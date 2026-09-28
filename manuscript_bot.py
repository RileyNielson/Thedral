import os
import re
import sys
import glob
import json
import time
import gzip
import shutil
import asyncio
import ollama
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from config import ACTIVE_CONTEXT, AUTH_FILE, WORKSPACE_DIR, STUDIO_MODEL, LLM_OPTIONS, DB_PATH, save_session
from db import (
    get_paragraphs_range, get_paragraph_with_scene_context, 
    save_paragraph_revision, get_last_revision, execute_rollback,
    insert_paragraph_and_reindex, delete_paragraph_and_reindex,
    add_style_rule, log_foreshadowing_promise, get_open_promises, get_db
)
from scanner import scan_bookshelf, get_file_metadata
from reader import ingest_manuscript, replace_entire_chapter, extract_raw_paragraphs
from editorial import (
    calculate_chapter_telemetry, export_local_mirror_files,
    sync_from_local_mirror, export_book_to_docx, check_downstream_ripples
)
from socratic import query_socratic, elevate_prose_diagnosis, generate_kdp_package
from disclosure import extract_chapter_disclosures, audit_reader_experience, get_reader_experience_dossier
from worldline import extract_chapter_worldlines, audit_continuity_paradoxes, render_3d_continuity_landscape

AUTHORIZED_USER_ID = None
if os.path.exists(AUTH_FILE):
    try:
        with open(AUTH_FILE, "r") as f: AUTHORIZED_USER_ID = int(f.read().strip())
    except Exception: pass

BOOKSHELF_CACHE = []
PENDING_CONFIRMATION = {}
PENDING_FILE_UPLOAD = {}

def is_authorized(user_id: int) -> bool:
    global AUTHORIZED_USER_ID
    if AUTHORIZED_USER_ID is None:
        AUTHORIZED_USER_ID = user_id
        with open(AUTH_FILE, "w") as f: f.write(str(user_id))
        return True
    return user_id == AUTHORIZED_USER_ID

def get_focus_hud() -> str:
    series = ACTIVE_CONTEXT.get("series", "Victorian Skies")
    book = ACTIVE_CONTEXT.get("book_title", "No Book Loaded")
    ch = ACTIVE_CONTEXT.get("active_chapter", 1)
    p = ACTIVE_CONTEXT.get("active_para")
    parts = [f"**{series}**"]
    if book and book != "None": parts.append(f"**{os.path.splitext(book)[0].replace('_', ' ')}**")
    if ch: parts.append(f"**Ch {ch:02d}**")
    if p: parts.append(f"**P{p:03d}**")
    return " ❯ ".join(parts)

async def safe_send(update: Update, text: str):
    if not text: return
    chunks = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 > 3800:
            if current: chunks.append(current.strip())
            current = paragraph + "\n\n"
        else: current += paragraph + "\n\n"
    if current.strip(): chunks.append(current.strip())
    for chunk in chunks:
        try: await update.message.reply_text(chunk, parse_mode="Markdown")
        except BadRequest:
            clean = re.sub(r"[\*_`\[\]]", "", chunk)
            await update.message.reply_text(clean)

def fast_regex_router(text: str) -> dict:
    t = text.strip()
    low = t.lower()
    ch = ACTIVE_CONTEXT.get("active_chapter", 1)
    if low in ["where", "where am i", "here", "focus", "hud"]: return {"action": "SHOW_HUD"}
    rw = re.match(r"^(?:rewrite|replace)\s+(?:ch(?:apter)?\s*(\d+)\s*)?p(?:ara)?\s*(\d+)[:\s]+(.+)", t, re.I | re.S)
    if rw: return {"action": "REWRITE", "chapter_num": int(rw.group(1)) if rw.group(1) else ch, "paragraph_num": int(rw.group(2)), "text_payload": rw.group(3).strip()}
    rev = re.match(r"^(?:review|critique|check)\s+(?:ch(?:apter)?\s*(\d+)\s*)?p(?:ara)?\s*(\d+)$", low)
    if rev: return {"action": "REVIEW_PARAGRAPH", "chapter_num": int(rev.group(1)) if rev.group(1) else ch, "paragraph_num": int(rev.group(2))}
    rev_ch = re.match(r"^(?:review|critique|diagnose)\s+(?:ch(?:apter)?\s*(\d+)|chapter)$", low)
    if rev_ch: return {"action": "REVIEW_CHAPTER", "chapter_num": int(rev_ch.group(1)) if rev_ch.group(1) else ch}
    rd = re.match(r"^(?:read|show|view)\s+(?:ch(?:apter)?\s*(\d+)\s*)?p(?:ara)?\s*(\d+)$", low)
    if rd: return {"action": "READ_PARAGRAPHS", "chapter_num": int(rd.group(1)) if rd.group(1) else ch, "paragraph_num": int(rd.group(2))}
    ch_jump = re.match(r"^(?:chapter|ch)\s*(\d+)$", low)
    if ch_jump: return {"action": "SET_CHAPTER", "chapter_num": int(ch_jump.group(1))}
    rb = re.match(r"^(?:undo|rollback|restore)\s+(?:ch(?:apter)?\s*(\d+)\s*)?p(?:ara)?\s*(\d+)$", low)
    if rb: return {"action": "ROLLBACK", "chapter_num": int(rb.group(1)) if rb.group(1) else ch, "paragraph_num": int(rb.group(2))}
    if low in ["telemetry", "stats", "cadence", "slopes"]: return {"action": "TELEMETRY", "chapter_num": ch}
    if low in ["drafts", "bookshelf", "show drafts"]: return {"action": "BROWSE_FILES"}
    op = re.match(r"^open\s+(\d+)$", low)
    if op: return {"action": "SELECT_FILE", "file_number": int(op.group(1))}
    if low in ["export", "export word", "export docx"]: return {"action": "EXPORT_WORD"}
    if low in ["sync", "sync mirror"]: return {"action": "SYNC_MIRROR"}
    if low in ["trajectory", "3d", "plot 3d"]: return {"action": "PLOT_3D"}
    if low in ["audit", "continuity"]: return {"action": "AUDIT_CONTINUITY"}
    if low in ["scan worldlines", "extract worldlines"]: return {"action": "EXTRACT_WORLDLINES", "chapter_num": ch}
    if low in ["reader", "track reader"]: return {"action": "TRACK_READER", "chapter_num": ch}
    if low in ["reader audit", "subtext audit"]: return {"action": "AUDIT_READER", "chapter_num": ch}
    if low in ["reader report", "reader dossier"]: return {"action": "VIEW_READER_DOSSIER", "chapter_num": ch}
    if low in ["promises", "foreshadowing"]: return {"action": "VIEW_PROMISES"}
    if low in ["kdp", "keywords"]: return {"action": "KDP_METADATA"}
    return None

SEMANTIC_ROUTER_SYSTEM = """Classify author input into JSON:
{"action": "ROLLBACK | INSERT_BEAT | DELETE_BEAT | UPDATE_STYLE | LOG_PROMISE | VIEW_PROMISES | EXPORT_WORD | KDP_METADATA | TELEMETRY | BROWSE_FILES | SELECT_FILE | READ_PARAGRAPHS | REVIEW_PARAGRAPH | REVIEW_CHAPTER | REWRITE | SET_CHAPTER | SYNC_MIRROR | SWITCH_PROJECT | CHAT", "chapter_num": int or null, "paragraph_num": int or null, "file_number": int or null, "text_payload": "str or null", "style_term": "str or null", "style_rule": "str or null", "promise_desc": "str or null", "target_volume": int or null}"""

def classify_semantic_intent(user_text: str) -> dict:
    quick = fast_regex_router(user_text)
    if quick: return quick
    ctx = f"Book: {ACTIVE_CONTEXT['book_title']} | Ch: {ACTIVE_CONTEXT.get('active_chapter', 1)}"
    try:
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "system", "content": SEMANTIC_ROUTER_SYSTEM}, {"role": "user", "content": f"{ctx}\nAuthor: '{user_text}'"}], format="json", options=LLM_OPTIONS)
        return json.loads(resp['message']['content'])
    except Exception: return {"action": "CHAT"}

async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PENDING_FILE_UPLOAD, ACTIVE_CONTEXT
    if not is_authorized(update.effective_user.id): return
    user_id = update.effective_user.id
    doc = update.message.document
    file_name = doc.file_name or "uploaded_chapter"
    ch_match = re.search(r"(?:chapter|ch|chap)[_\s\-]*(\d+)", f"{update.message.caption or ''} {file_name}", re.I)
    temp_path = os.path.join(WORKSPACE_DIR, f"temp_{user_id}_{file_name}")
    doc_file = await doc.get_file()
    await doc_file.download_to_drive(temp_path)
    if ch_match:
        ch = int(ch_match.group(1))
        raw_tuples = extract_raw_paragraphs(temp_path)
        full_text = "\n\n".join([t[0] for t in raw_tuples])
        status = await update.message.reply_text(f"📖 Chapter {ch} detected! Replacing in Vault...")
        p_cnt, w_cnt = await asyncio.to_thread(replace_entire_chapter, ACTIVE_CONTEXT["book_id"], ch, full_text)
        if os.path.exists(temp_path): os.remove(temp_path)
        await status.delete()
        await safe_send(update, f"✅ **CHAPTER {ch} REPLACED!**\n• `{w_cnt:,}` words ({p_cnt} paragraphs)\n• Synced to Mac mirror.")
    else:
        PENDING_FILE_UPLOAD[user_id] = {"path": temp_path, "filename": file_name}
        await safe_send(update, f"📥 Received `{file_name}`! Which chapter should this replace? (e.g. 'Chapter 3').")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_CONTEXT, BOOKSHELF_CACHE, PENDING_CONFIRMATION, PENDING_FILE_UPLOAD
    if not is_authorized(update.effective_user.id): return
    user_id = update.effective_user.id
    user_text = update.message.text.strip()
    u_lower = user_text.lower()

    if user_id in PENDING_FILE_UPLOAD:
        ch_match = re.search(r"\b(\d{1,3})\b", user_text)
        if ch_match:
            ch = int(ch_match.group(1))
            pending = PENDING_FILE_UPLOAD.pop(user_id)
            temp_path, fname = pending["path"], pending["filename"]
            raw_tuples = extract_raw_paragraphs(temp_path)
            full_text = "\n\n".join([t[0] for t in raw_tuples])
            status = await update.message.reply_text(f"📖 Replacing Chapter {ch} with `{fname}`...")
            p_cnt, w_cnt = await asyncio.to_thread(replace_entire_chapter, ACTIVE_CONTEXT["book_id"], ch, full_text)
            if os.path.exists(temp_path): os.remove(temp_path)
            await status.delete()
            await safe_send(update, f"✅ **CHAPTER {ch} REPLACED!**\n• `{w_cnt:,}` words ({p_cnt} paragraphs)\n• Synced to mirror.")
            return
        elif "cancel" in u_lower:
            p = PENDING_FILE_UPLOAD.pop(user_id)
            if os.path.exists(p["path"]): os.remove(p["path"])
            await safe_send(update, "🚫 Upload cancelled.")
            return

    if user_id in PENDING_CONFIRMATION:
        pending = PENDING_CONFIRMATION.pop(user_id)
        if any(w in u_lower for w in ["yes", "confirm", "sure", "yep"]):
            if pending["action"] == "ROLLBACK":
                execute_rollback(pending["pid"], pending["target_ver"], pending["text"])
                export_local_mirror_files(ACTIVE_CONTEXT["book_id"])
                await safe_send(update, f"✅ **Restored!** `{pending['pid']}` reverted to v{pending['target_ver']}.")
                return
        else:
            await safe_send(update, "🚫 Rollback cancelled.")
            return

    triage = await asyncio.to_thread(classify_semantic_intent, user_text)
    action = triage.get("action", "CHAT")
    ch = triage.get("chapter_num") or ACTIVE_CONTEXT.get("active_chapter", 1)
    ACTIVE_CONTEXT["active_chapter"] = ch
    save_session(ACTIVE_CONTEXT)

    if action == "SHOW_HUD":
        p = ACTIVE_CONTEXT.get("active_para")
        await safe_send(update, f"🧭 **NARRATIVE COORDINATE:**\n{get_focus_hud()}\n\n• **Active Focus:** {f'Paragraph {p:03d}' if p else 'Chapter overview'}\n• **Words:** `{ACTIVE_CONTEXT['total_words']:,}` across `{ACTIVE_CONTEXT['total_paras']}` paragraphs.")
        return

    elif action == "SET_CHAPTER":
        ACTIVE_CONTEXT["active_para"] = None
        save_session(ACTIVE_CONTEXT)
        await safe_send(update, f"📍 **Focused on:**\n{get_focus_hud()}")
        return

    elif action == "ROLLBACK":
        p = triage.get("paragraph_num", 1) or 1
        pid = f"CH{ch:02d}_P{p:03d}"
        last_rev = get_last_revision(pid)
        if not last_rev:
            await safe_send(update, f"No previous versions found for `{pid}`.")
            return
        PENDING_CONFIRMATION[user_id] = {"action": "ROLLBACK", "pid": pid, "target_ver": last_rev["version_num"], "text": last_rev["text"]}
        await safe_send(update, f"📜 *Previous Revision of `{pid}` (v{last_rev['version_num']}):*\n\n\"{last_rev['text']}\"\n\n👉 Restore this revision? (Reply *'Yes'* or *'No'*).")
        return

    elif action == "INSERT_BEAT":
        p = triage.get("paragraph_num", 1) or 1
        text_p = triage.get("text_payload", "")
        if not text_p:
            await safe_send(update, "What text would you like to insert?")
            return
        new_pid = insert_paragraph_and_reindex(ACTIVE_CONTEXT["book_id"], ch, p, text_p)
        export_local_mirror_files(ACTIVE_CONTEXT["book_id"])
        await safe_send(update, f"✅ *Inserted as `{new_pid}`!* Synced to Mac mirror.")
        return

    elif action == "DELETE_BEAT":
        p = triage.get("paragraph_num", 1) or 1
        delete_paragraph_and_reindex(ACTIVE_CONTEXT["book_id"], ch, p)
        export_local_mirror_files(ACTIVE_CONTEXT["book_id"])
        await safe_send(update, f"✅ *Deleted CH{ch:02d}_P{p:03d}.* Synced to Mac mirror.")
        return

    elif action == "UPDATE_STYLE":
        term, rule = triage.get("style_term"), triage.get("style_rule", "Author rule")
        if term:
            add_style_rule(term, rule)
            await safe_send(update, f"✅ *Style Rule Logged:* `{term}` → {rule}.")
        return

    elif action == "LOG_PROMISE":
        desc, vol, p = triage.get("promise_desc", user_text), triage.get("target_volume", 2), triage.get("paragraph_num", 1) or 1
        pid = f"CH{ch:02d}_P{p:03d}"
        log_foreshadowing_promise("Victorian_Skies", ACTIVE_CONTEXT["book_id"], pid, vol, desc)
        await safe_send(update, f"⚓ *Chekhov Gravity Well Logged:* `{desc}` planted in `{pid}` for Book {vol}!")
        return

    elif action == "VIEW_PROMISES":
        pr = get_open_promises()
        if not pr:
            await safe_send(update, "No open foreshadowing promises.")
            return
        msg = "⚓ **OPEN FORESHADOWING WELLS:**\n\n" + "\n".join([f"• **Book {r['target_volume']}:** {r['promise_desc']} (`{r['planted_para_id']}`)" for r in pr])
        await safe_send(update, msg)
        return

    elif action == "SYNC_MIRROR":
        status = await update.message.reply_text("🔄 Syncing from Mac mirror...")
        up = await asyncio.to_thread(sync_from_local_mirror, ACTIVE_CONTEXT["book_id"])
        await status.delete()
        await safe_send(update, f"✅ **Synced!** Updated `{up}` paragraphs." if up else "✨ Database already matches your mirror.")
        return

    elif action == "TELEMETRY":
        t = calculate_chapter_telemetry(ACTIVE_CONTEXT["book_id"], ch)
        if t:
            f_str = ", ".join([f"{k} ({v})" for k, v in list(t["top_filters"].items())[:4]]) or "None"
            c_str = ", ".join([f"{k} ({v})" for k, v in list(t["top_crutches"].items())[:4]]) or "None"
            await safe_send(update, f"📊 **Chapter {ch} Telemetry:**\n\n• Words: `{t['total_words']:,}` ({t['total_paras']} paras)\n• Dialogue: `{t['dialogue_ratio']}%`\n• Cadence Variance: `{t['cadence_variance']}` (Avg: `{t['avg_sentence_len']}` words)\n\n🌌 **Law 1 Physics:**\n• Tension (Y): `{t['tension_elevation']}`\n• Slope (dY/dX): `{t['pacing_slope']}` → **{t['slope_diagnosis']}**\n\n🔍 Filter Verbs: {f_str}\n⚡ Crutch Words: {c_str}")
        return

    elif action == "EXPORT_WORD":
        status = await update.message.reply_text("📄 Compiling .docx...")
        dp = await asyncio.to_thread(export_book_to_docx, ACTIVE_CONTEXT["book_id"])
        await status.delete()
        if dp and os.path.exists(dp):
            with open(dp, "rb") as f: await update.message.reply_document(document=f, filename=os.path.basename(dp), caption=f"📖 {ACTIVE_CONTEXT['book_title']}")
        else: await safe_send(update, "❌ No text to export.")
        return

    elif action == "BROWSE_FILES":
        BOOKSHELF_CACHE = scan_bookshelf()
        if not BOOKSHELF_CACHE:
            await safe_send(update, "No manuscripts found in your series directory.")
            return
        reply = f"📚 **MANUSCRIPTS FOUND ({len(BOOKSHELF_CACHE)}):**\n\n"
        for idx, (btype, rel_p, abs_p) in enumerate(BOOKSHELF_CACHE[:25], 1):
            meta = get_file_metadata(abs_p)
            size_tag = f" ({meta.get('size', '')})" if meta else ""
            reply += f"**{idx}.** {btype}: `{rel_p}`{size_tag}\n"
        reply += "\n👉 Text *'Open 1'* to load!"
        await safe_send(update, reply)
        return

    elif action == "SELECT_FILE":
        if not BOOKSHELF_CACHE: BOOKSHELF_CACHE = scan_bookshelf()
        fnum = triage.get("file_number", 1) or 1
        idx = fnum - 1
        if 0 <= idx < len(BOOKSHELF_CACHE):
            btype, rel_p, abs_p = BOOKSHELF_CACHE[idx]
            status = await update.message.reply_text(f"📖 Ingesting `{os.path.basename(abs_p)}`...")
            p_cnt, w_cnt, ch_cnt = await asyncio.to_thread(ingest_manuscript, abs_p, "ACTIVE_BOOK")
            ACTIVE_CONTEXT.update({"is_locked": True, "book_title": os.path.basename(abs_p), "book_id": "ACTIVE_BOOK", "mode": "EDITING", "active_chapter": 1, "active_para": None, "file": abs_p, "total_words": w_cnt, "total_paras": p_cnt})
            save_session(ACTIVE_CONTEXT)
            await status.delete()
            await safe_send(update, f"🔒 **LOADED: {ACTIVE_CONTEXT['book_title']}**\n\n• Words: `{w_cnt:,}` across `{ch_cnt}` chapters\n• Paragraphs: `{p_cnt:,}`\n• Mirror: Ready in `_Studio_Workspace/Manuscript_Mirror/`")
        return

    elif action == "READ_PARAGRAPHS":
        p = triage.get("paragraph_num", 1) or 1
        rows = get_paragraphs_range(ACTIVE_CONTEXT["book_id"], ch, p, 5)
        if not rows:
            await safe_send(update, f"No paragraphs found in Ch {ch} starting at P{p}.")
            return
        msg = f"📖 **{ACTIVE_CONTEXT['book_title']} — Ch {ch}:**\n\n" + "\n\n".join([f"**[P{r['para_num']}]:** {r['text']}" for r in rows])
        await safe_send(update, msg)
        return

    elif action == "ELEVATE_PARAGRAPH":
        p = triage.get("paragraph_num", 1) or 1
        ACTIVE_CONTEXT["active_para"] = p
        save_session(ACTIVE_CONTEXT)
        target, scene_ctx = get_paragraph_with_scene_context(ACTIVE_CONTEXT["book_id"], ch, p)
        if not target:
            await safe_send(update, f"Could not find Paragraph {p} in Chapter {ch}.")
            return
        status = await update.message.reply_text(f"🔬 Running Level 2–4 Craft Dissection on P{p}...")
        resp = await asyncio.to_thread(elevate_prose_diagnosis, target["text"], scene_ctx)
        await status.delete()
        hud = f"🧭 `{get_focus_hud()}`\n\n"
        await safe_send(update, f"{hud}🏛️ **HIGH-TIER PROSE ELEVATION (P{p:03d}):**\n\n{resp}\n\n👉 When ready, submit your elevated prose:\n*Rewrite P{p}: [Your replacement text]*")
        return

    elif action == "REVIEW_PARAGRAPH":
        p = triage.get("paragraph_num", 1) or 1
        ACTIVE_CONTEXT["active_para"] = p
        save_session(ACTIVE_CONTEXT)
        target, scene_ctx = get_paragraph_with_scene_context(ACTIVE_CONTEXT["book_id"], ch, p)
        if not target:
            await safe_send(update, f"Could not find Paragraph {p} in Chapter {ch}.")
            return
        t_data = calculate_chapter_telemetry(ACTIVE_CONTEXT["book_id"], ch)
        status = await update.message.reply_text("✍️ Diagnosing beat...")
        resp = await asyncio.to_thread(query_socratic, user_text, scene_ctx, t_data)
        await status.delete()
        hud = f"🧭 `{get_focus_hud()}`\n\n"
        await safe_send(update, f"{hud}✍️ **LINE CRITIQUE:**\n\n{resp}\n\n👉 To revise:\n*Rewrite P{p}: [Your replacement text]*")
        return

    elif action == "REVIEW_CHAPTER":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT total_paras, total_words, opening_beat, closing_beat, dialogue_ratio FROM chapter_digests WHERE book_id = ? AND chapter_num = ?", (ACTIVE_CONTEXT["book_id"], ch))
        digest = c.fetchone()
        conn.close()
        if not digest:
            await safe_send(update, f"No digest for Chapter {ch}.")
            return
        t_data = calculate_chapter_telemetry(ACTIVE_CONTEXT["book_id"], ch)
        macro_ctx = f"CHAPTER {ch}: {digest['total_words']} words across {digest['total_paras']} paras. Dialogue: {int(digest['dialogue_ratio']*100)}%.\nOpening: \"{digest['opening_beat']}\"\nClosing: \"{digest['closing_beat']}\""
        status = await update.message.reply_text(f"✍️ Diagnosing Chapter {ch} macro arc...")
        resp = await asyncio.to_thread(query_socratic, f"Analyze Chapter {ch} macro dramatic structure.", macro_ctx, t_data)
        await status.delete()
        await safe_send(update, f"🧭 `{get_focus_hud()}`\n\n✍️ **MACRO CHAPTER DIAGNOSIS:**\n\n{resp}")
        return

    elif action == "REWRITE":
        p = triage.get("paragraph_num", 1) or 1
        ACTIVE_CONTEXT["active_para"] = p
        save_session(ACTIVE_CONTEXT)
        new_text = triage.get("text_payload", "")
        if not new_text:
            await safe_send(update, "What is your replacement text?")
            return
        pid = f"CH{ch:02d}_P{p:03d}"
        new_ver = save_paragraph_revision(pid, new_text)
        export_local_mirror_files(ACTIVE_CONTEXT["book_id"])
        keywords = [w.strip('.,;:"!?') for w in new_text.split() if len(w) > 4][:5]
        ripples = check_downstream_ripples(ACTIVE_CONTEXT["book_id"], ch, p, keywords)
        rip_msg = "\n\n⚠️ **Downstream Continuity Warnings:**\n" + "\n".join([f"• [Ch {r['chapter']}, P{r['para']}]: Mentions *{', '.join(r['matched'])}* → _{r['snippet']}_" for r in ripples]) if ripples else ""
        hud = f"🧭 `{get_focus_hud()}`\n\n"
        await safe_send(update, f"{hud}✅ **Saved `{pid}` (v{new_ver})!** Synced to Mac mirror.{rip_msg}")
        return

    elif action == "TRACK_READER":
        status = await update.message.reply_text(f"🧠 Mapping Reader Epistemic Horizon for Ch {ch}...")
        cnts = await asyncio.to_thread(extract_chapter_disclosures, ACTIVE_CONTEXT["book_id"], ch)
        await status.delete()
        await safe_send(update, f"✅ **Reader Horizon Mapped (Ch {ch}):**\n• Direct Facts: `{cnts.get('direct', 0)}`\n• Inferred Clues: `{cnts.get('inferred', 0)}`\n• Delayed Mysteries: `{cnts.get('delayed', 0)}`\n\n👉 Text *'reader report'* to view!")
        return

    elif action == "AUDIT_READER":
        status = await update.message.reply_text("🔍 Auditing subtext & mysteries...")
        alerts = await asyncio.to_thread(audit_reader_experience, ACTIVE_CONTEXT["book_id"], ch)
        await status.delete()
        await safe_send(update, "✨ **Reader Experience Balanced!**" if not alerts else "🎭 **Reader Experience Alerts:**\n\n" + "\n\n".join(alerts))
        return

    elif action == "VIEW_READER_DOSSIER":
        dossier = await asyncio.to_thread(get_reader_experience_dossier, ACTIVE_CONTEXT["book_id"], ch)
        await safe_send(update, dossier)
        return

    elif action == "EXTRACT_WORLDLINES":
        status = await update.message.reply_text(f"🛰️ Extracting state vectors for Ch {ch}...")
        c_cnt = await asyncio.to_thread(extract_chapter_worldlines, ACTIVE_CONTEXT["book_id"], ch)
        await status.delete()
        await safe_send(update, f"✅ **State-Space Updated:** `{c_cnt}` state vectors logged.")
        return

    elif action == "AUDIT_CONTINUITY":
        status = await update.message.reply_text("🔍 Auditing 3D phase-space...")
        paradoxes = await asyncio.to_thread(audit_continuity_paradoxes, ACTIVE_CONTEXT["book_id"])
        await status.delete()
        await safe_send(update, "✨ **Continuity Pristine!** No teleportation or inversions." if not paradoxes else "⚠️ **Continuity Anomalies:**\n\n" + "\n\n".join(paradoxes))
        return

    elif action == "PLOT_3D":
        status = await update.message.reply_text("🌐 Rendering 3D trajectory landscape...")
        hp = await asyncio.to_thread(render_3d_continuity_landscape, ACTIVE_CONTEXT["book_id"])
        await status.delete()
        if hp and os.path.exists(hp):
            with open(hp, "rb") as f: await update.message.reply_document(document=f, filename=os.path.basename(hp), caption=f"🌐 3D Narrative Trajectory: {ACTIVE_CONTEXT['book_title']}")
        else: await safe_send(update, "❌ No trajectory vectors found. Run *'scan worldlines'* first.")
        return

    elif action == "KDP_METADATA":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT text FROM paragraphs WHERE book_id = ? ORDER BY seq_order ASC LIMIT 25", (ACTIVE_CONTEXT["book_id"],))
        sample = "\n".join([r[0] for r in c.fetchall()])
        conn.close()
        status = await update.message.reply_text("📦 Analyzing story for KDP keywords...")
        pkg = await asyncio.to_thread(generate_kdp_package, sample)
        await status.delete()
        await safe_send(update, f"📦 **AMAZON KDP LAUNCH PACKAGE:**\n\n{pkg}")
        return

    elif action == "SWITCH_PROJECT":
        ACTIVE_CONTEXT["is_locked"] = False
        save_session(ACTIVE_CONTEXT)
        await safe_send(update, f"🔓 Stepped out of `{ACTIVE_CONTEXT['book_title']}`. Text *'Drafts'* to choose another.")
        return

    # Default: Socratic Creative Consultation
    status = await update.message.reply_text("🤔 Reflecting on craft...")
    resp = await asyncio.to_thread(query_socratic, user_text)
    await status.delete()
    await safe_send(update, resp)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id): return
    await safe_send(update, "📚 **Socratic Manuscript Studio Online**\nZero AI prose — 100% your voice.\n\n🧭 **HUD & Navigation:**\n• *'where'* — Real-time narrative coordinates\n• *'drafts'* — Browse manuscripts\n• *'chapter 3'* — Set focus\n• *'read p1'* — Read 5 paragraphs\n\n✍️ **Editing:**\n• *'review p4'* — Line critique\n• *'review chapter'* — Macro arc diagnosis\n• *'rewrite p4: [text]'* — Instant revision\n• *'undo p4'* — Restore prior draft\n• *'sync'* — Pull changes from Mac mirror\n\n🌌 **Physics & Reader Tracking:**\n• *'stats'* — Telemetry & pacing slope\n• *'track reader'* — Map direct/inferred/delayed data\n• *'reader audit'* — Catch subtext murder\n• *'audit'* — Catch teleportation paradoxes\n• *'plot 3d'* — Send interactive 3D graph\n• `/backup` — Direct vault backup to your phone")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id): return
    await safe_send(update, f"🧭 **COORDINATE:** {get_focus_hud()}\n\n• **Words:** `{ACTIVE_CONTEXT['total_words']:,}` ({ACTIVE_CONTEXT['total_paras']} paras)\n• **Mirror:** `_Studio_Workspace/Manuscript_Mirror/`\n• **Model:** `{STUDIO_MODEL}` (Local Ollama)")

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id): return
    if not os.path.exists(DB_PATH):
        await safe_send(update, "❌ No database found.")
        return
    status = await update.message.reply_text("📦 Archiving SQLite Data Vault...")
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_gz = os.path.join(WORKSPACE_DIR, f"manuscript_backup_{ts}.db.gz")
    with open(DB_PATH, 'rb') as f_in:
        with gzip.open(backup_gz, 'wb') as f_out: shutil.copyfileobj(f_in, f_out)
    await status.delete()
    with open(backup_gz, 'rb') as f:
        await update.message.reply_document(document=f, filename=f"manuscript_vault_{ts}.db.gz", caption=f"🛡️ **Vault Backup ({ts})**")
    if os.path.exists(backup_gz): os.remove(backup_gz)

if __name__ == "__main__":
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_token.txt")
    if not TOKEN and os.path.exists(token_file):
        with open(token_file, "r") as f: TOKEN = f.read().strip()
    if not TOKEN and sys.stdin.isatty():
        TOKEN = input("Enter your Telegram Bot Token: ").strip()
    if not TOKEN:
        print("❌ FATAL: No Telegram Bot Token found.")
        sys.exit(1)
    t_request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = ApplicationBuilder().token(TOKEN).request(t_request).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("📚 Socratic Manuscript Studio is LIVE on your Mac Mini.")
    app.run_polling()
