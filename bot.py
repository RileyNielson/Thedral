import os
import re
import asyncio
import traceback
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from config import ACTIVE_CONTEXT, AUTH_FILE, WORKSPACE_DIR
from db import get_paragraphs_range, get_paragraph_with_scene_context, save_paragraph_revision, get_db
from scanner import scan_bookshelf
from reader import ingest_manuscript
from editorial import (
    calculate_chapter_telemetry, export_local_mirror_files,
    sync_from_local_mirror, export_book_to_docx, check_downstream_ripples
)
from socratic import query_socratic

AUTHORIZED_USER_ID = None
if os.path.exists(AUTH_FILE):
    try:
        with open(AUTH_FILE, "r") as f: AUTHORIZED_USER_ID = int(f.read().strip())
    except Exception: pass

BOOKSHELF_CACHE = []
WORD_NUMS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

def is_authorized(user_id: int) -> bool:
    global AUTHORIZED_USER_ID
    if AUTHORIZED_USER_ID is None:
        AUTHORIZED_USER_ID = user_id
        with open(AUTH_FILE, "w") as f: f.write(str(user_id))
        return True
    return user_id == AUTHORIZED_USER_ID

async def send_split(update: Update, text: str):
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i + 4000])

async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seamless upload: send a .docx and it slots right in."""
    if not is_authorized(update.effective_user.id): return
    doc = update.message.document
    fname = doc.file_name or "uploaded.docx"
    temp_path = os.path.join(WORKSPACE_DIR, f"upload_{fname}")
    
    dfile = await doc.get_file()
    await dfile.download_to_drive(temp_path)

    status = await update.message.reply_text(f"📖 Slicing `{fname}` into paragraphs and building Mac mirror...")
    p_cnt, w_cnt, ch_cnt = await asyncio.to_thread(ingest_manuscript, temp_path, "ACTIVE_BOOK")
    
    ACTIVE_CONTEXT["is_locked"] = True
    ACTIVE_CONTEXT["book_title"] = fname
    ACTIVE_CONTEXT["total_words"] = w_cnt
    ACTIVE_CONTEXT["total_paras"] = p_cnt

    await status.edit_text(
        f"✅ *{fname} LOADED SUCCESSFULLY!*\n\n"
        f"• Words: `{w_cnt:,}` across `{ch_cnt}` chapters\n"
        f"• Paragraphs: `{p_cnt:,}`\n"
        f"• Mac Mirror: Ready in `_Studio_Workspace/Manuscript_Mirror/`\n\n"
        f"Ready to work! Try asking:\n"
        f"• *'What are the first 5 paragraphs of chapter 1?'*\n"
        f"• *'Review chapter 1'* (Stage 1 Macro Audit)\n"
        f"• *'Telemetry chapter 1'* (Crutch words & rhythm math)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_CONTEXT, BOOKSHELF_CACHE
    if not is_authorized(update.effective_user.id): return
    text = update.message.text.strip()
    u = text.lower()

    # 1. Project Navigation (Browse & Search)
    if any(k in u for k in ["bookshelf", "browse", "show drafts", "list projects", "my projects", "find project", "search"]):
        query = re.sub(r"(?:find|search|show|list|my|projects|drafts|bookshelf|open)", "", u).strip()
        BOOKSHELF_CACHE = scan_bookshelf(query)
        if not BOOKSHELF_CACHE:
            await update.message.reply_text(f"❌ No manuscripts found matching '{query}'.")
            return
        reply = f"📚 *MANUSCRIPTS FOUND ({len(BOOKSHELF_CACHE)}):*\n\n"
        for idx, (btype, rel_p, _) in enumerate(BOOKSHELF_CACHE[:25], 1):
            reply += f"*{idx}.* {btype}: `{rel_p}`\n"
        reply += "\n👉 Text *'Open number 4'* (or the book name) to load it!"
        await send_split(update, reply)
        return

    # 2. Unlock / Switch
    if any(k in u for k in ["switch project", "change project", "close book", "exit project", "unlock"]):
        ACTIVE_CONTEXT["is_locked"] = False
        await update.message.reply_text(f"🔓 Stepped out of `{ACTIVE_CONTEXT['book_title']}`. Text *'Show my bookshelf'* to browse.")
        return

    # 3. Select / Open Book
    if not ACTIVE_CONTEXT["is_locked"] or any(k in u for k in ["open", "load"]):
        if not BOOKSHELF_CACHE: BOOKSHELF_CACHE = scan_bookshelf()
        selected_idx = None

        num_m = re.search(r"\b(?:number\s*)?(\d{1,2})\b", u)
        if num_m and any(v in u for v in ["open", "load", "select", "number"]):
            val = int(num_m.group(1)) - 1
            if 0 <= val < len(BOOKSHELF_CACHE): selected_idx = val

        if selected_idx is None:
            for idx, (_, rel_p, _) in enumerate(BOOKSHELF_CACHE):
                clean = os.path.basename(rel_p).lower().replace('.docx','').replace('.scriv','')
                if clean in u or any(w in u for w in clean.split() if len(w) > 4):
                    selected_idx = idx
                    break

        if selected_idx is not None:
            btype, rel_p, abs_p = BOOKSHELF_CACHE[selected_idx]
            status = await update.message.reply_text(f"📖 Opening `{os.path.basename(abs_p)}` and building Mac Mirror...")
            p_cnt, w_cnt, ch_cnt = await asyncio.to_thread(ingest_manuscript, abs_p, "ACTIVE_BOOK")
            ACTIVE_CONTEXT = {
                "is_locked": True,
                "book_title": os.path.basename(abs_p),
                "book_id": "ACTIVE_BOOK",
                "mode": "EDITING",
                "file": abs_p,
                "total_words": w_cnt,
                "total_paras": p_cnt
            }
            await status.edit_text(
                f"🔒 *{ACTIVE_CONTEXT['book_title']} LOADED!*\n\n"
                f"• Words: `{w_cnt:,}` across `{ch_cnt}` real chapters\n"
                f"• Paragraphs: `{p_cnt:,}`\n"
                f"• Mac Mirror: `_Studio_Workspace/Manuscript_Mirror/`\n\n"
                f"What would you like to explore? We can review Chapter 1, read paragraphs, check telemetry, or export to Word."
            )
            return

    # 4. Gap 1: In-Place Rewrite Write-Back Loop
    rewrite_m = re.search(r"(?:rewrite|update)\s+(?:CH\d+_)?P(\d+)\s*[:\-]\s*(.+)", text, re.I | re.DOTALL)
    if rewrite_m:
        p_num = int(rewrite_m.group(1))
        new_text = rewrite_m.group(2).strip()
        pid = f"CH01_P{p_num:03d}" # default Ch 1 or parsed
        new_ver = save_paragraph_revision(pid, new_text)
        export_local_mirror_files(ACTIVE_CONTEXT["book_id"])
        
        # Check downstream ripples
        keywords = [w for w in new_text.split() if len(w) > 5][:4]
        ripples = check_downstream_ripples(ACTIVE_CONTEXT["book_id"], 1, p_num, keywords)
        rip_msg = ""
        if ripples:
            rip_msg = "\n\n⚠️ *Downstream Change Matrix Warnings:*\n"
            for r in ripples: rip_msg += f"• [CH{r['chapter']:02d}_P{r['para']:03d}]: Mentions *{', '.join(r['matched'])}* -> _{r['snippet']}_\n"

        await update.message.reply_text(f"✅ *PARAGRAPH UPDATED: `{pid}` (v{new_ver})*\n• Archived previous draft to Revision Vault\n• Synced to Mac Mirror{rip_msg}")
        return

    # 5. Gap 2: Two-Way Local Mac Mirror Sync
    if "sync" in u:
        status = await update.message.reply_text("🔄 Syncing edits from your Mac Mirror into SQLite...")
        updated = sync_from_local_mirror(ACTIVE_CONTEXT["book_id"])
        await status.edit_text(f"✅ Sync Complete!\nUpdated `{updated}` paragraphs modified on your Mac keyboard.")
        return

    # 6. Gap 5: Non-AI Prose Telemetry
    if any(k in u for k in ["telemetry", "crutch words", "filter verbs", "metrics"]):
        ch_m = re.search(r"chapter\s*(\d+)", u)
        ch = int(ch_m.group(1)) if ch_m else 1
        t = calculate_chapter_telemetry(ACTIVE_CONTEXT["book_id"], ch)
        if t:
            filters = ", ".join([f"{k} ({v})" for k, v in list(t["top_filters"].items())[:5]]) or "None"
            crutches = ", ".join([f"{k} ({v})" for k, v in list(t["top_crutches"].items())[:5]]) or "None"
            await update.message.reply_text(
                f"📊 *Chapter {ch} Prose Telemetry:*\n\n"
                f"• **Words:** `{t['total_words']:,}` across `{t['total_paras']}` paragraphs\n"
                f"• **Dialogue Ratio:** `{t['dialogue_ratio']}%`\n"
                f"• **Sentence Variety (Cadence):** `{t['cadence_variance']}` (Avg: `{t['avg_sentence_len']}` words)\n\n"
                f"🔍 **Top Filter Verbs:** {filters}\n"
                f"⚡ **Top Crutch Words:** {crutches}"
            )
        else:
            await update.message.reply_text(f"Couldn't calculate telemetry for Chapter {ch}.")
        return

    # 7. Export to Word (.docx)
    if "export" in u and ("word" in u or "docx" in u):
        status = await update.message.reply_text("📄 Compiling your book into Word (.docx)...")
        docx_p = export_book_to_docx(ACTIVE_CONTEXT["book_id"])
        if docx_p and os.path.exists(docx_p):
            await status.delete()
            with open(docx_p, "rb") as f:
                await update.message.reply_document(document=f, filename=os.path.basename(docx_p), caption="📖 Formatted manuscript ready for publication or beta readers.")
        else:
            await status.edit_text("❌ No paragraphs found to export. Open a book first!")
        return

    # 8. Instant Paragraph Display (SQLite Direct Read)
    if any(k in u for k in ["what are", "show me", "read", "display", "print"]) and "paragraph" in u:
        ch_m = re.search(r"chapter\s*(\d+)", u)
        ch = int(ch_m.group(1)) if ch_m else 1
        
        count_m = re.search(r"(?:first\s*)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*paragraphs?", u)
        count = 5
        if count_m:
            c_val = count_m.group(1).lower()
            count = WORD_NUMS.get(c_val, int(c_val) if c_val.isdigit() else 5)

        start_m = re.search(r"paragraph\s*(\d+)", u)
        start_p = int(start_m.group(1)) if (start_m and "first" not in u) else 1
        
        rows = get_paragraphs_range(ACTIVE_CONTEXT["book_id"], ch, start_p, count)
        if not rows:
            await update.message.reply_text(f"❌ No paragraphs found for Chapter {ch} (P{start_p}+).")
            return
        msg = f"📖 *{ACTIVE_CONTEXT['book_title']} — Chapter {ch} (P{start_p} to P{start_p + len(rows) - 1}):*\n\n"
        for r in rows: msg += f"*[P{r['para_num']}]:* {r['text']}\n\n"
        await send_split(update, msg)
        return

    # 9. Review Paragraph (Stage 2 Line Critique with Scene Context)
    ch_m = re.search(r"chapter\s*(\d+)", u)
    p_m = re.search(r"(?:paragraph|p)\s*(\d+)", u)
    if ch_m and p_m and any(v in u for v in ["review", "critique", "diagnose", "how is", "how does"]):
        ch, p = int(ch_m.group(1)), int(p_m.group(1))
        target, scene_ctx = get_paragraph_with_scene_context(ACTIVE_CONTEXT["book_id"], ch, p)
        if not target:
            await update.message.reply_text(f"Could not find Paragraph {p} in Chapter {ch}.")
            return
        status = await update.message.reply_text(f"✍️ Analyzing Chapter {ch}, Paragraph {p}...")
        resp = await asyncio.to_thread(query_socratic, text, scene_ctx)
        await status.delete()
        await send_split(update, f"✍️ *LINE CRITIQUE (CH{ch}, P{p}):*\n\n{resp}\n\n👉 To submit a rewrite, text:\n*Rewrite P{p}: [Your new words]*")
        return

    # 10. Review Chapter (Stage 1 Developmental Macro Audit)
    if ch_m and not p_m and any(v in u for v in ["review", "analyze", "audit", "structure"]):
        ch = int(ch_m.group(1))
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM chapter_digests WHERE book_id = ? AND chapter_num = ?", (ACTIVE_CONTEXT["book_id"], ch))
        digest = c.fetchone()
        conn.close()
        
        if not digest:
            await update.message.reply_text(f"Could not find Chapter {ch}.")
            return
            
        status = await update.message.reply_text(f"🏛️ Reviewing Chapter {ch} structure...")
        ch_ctx = f"CHAPTER {ch} STATS: {digest['total_words']} words across {digest['total_paras']} paragraphs ({int(digest['dialogue_ratio']*100)}% dialogue)\nOPENING: \"{digest['opening_beat']}\"\nCLOSING: \"{digest['closing_beat']}\""
        resp = await asyncio.to_thread(query_socratic, text, ch_ctx)
        await status.delete()
        await send_split(update, f"🏛️ *STAGE 1 DEV AUDIT (Chapter {ch}):*\n\n{resp}")
        return

    # 11. Conversational Partner
    status = await update.message.reply_text("🤔 Reflecting...")
    resp = await asyncio.to_thread(query_socratic, text)
    await status.delete()
    await send_split(update, resp)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id): return
    await update.message.reply_text(
        "📚 *Socratic Manuscript Studio*\n"
        "Your private AI literary partner on your Mac Mini.\n"
        "Zero AI prose — 100% your voice.\n\n"
        "📖 *Finding & Opening Books:*\n"
        "• *'Show my bookshelf'* — List all manuscripts\n"
        "• *'Find [name]'* — Search for a draft\n"
        "• *'Open number 4'* — Load and lock into a book\n\n"
        "✍️ *Reading & Editing:*\n"
        "• *'What are the first 5 paragraphs of chapter 1?'* — Instant text read\n"
        "• *'Review chapter 1'* — Stage 1 Developmental Macro Audit\n"
        "• *'Review chapter 1 paragraph 3'* — Stage 2 Line Critique\n"
        "• *'Rewrite P3: [text]'* — Save revision & sync to Mac\n"
        "• *'Telemetry chapter 1'* — Crutch words & rhythm math\n\n"
        "🔄 *Sync & Publish:*\n"
        "• *'Sync'* — Pull edits made on your Mac into the database\n"
        "• *'Export to Word'* — Download formatted .docx file\n"
        "• *'Let's switch projects'* — Return to bookshelf"
    )

if __name__ == "__main__":
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN: TOKEN = input("Enter your Telegram Bot Token: ").strip()

    t_request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = ApplicationBuilder().token(TOKEN).request(t_request).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("📚 Complete Socratic Studio with All Features Restored is live!")
    app.run_polling()
