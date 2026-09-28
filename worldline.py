import json
import os
import ollama
import plotly.graph_objects as go
from config import STUDIO_MODEL, LLM_OPTIONS, EXPORTS_DIR, ACTIVE_CONTEXT
from db import get_db

WORLDLINE_PROMPT = """Analyze scene paragraphs and extract character states into strict JSON:
[{"entity_name": "Name", "timeline_day": float, "location_name": "Location", "physical_state": "State", "epistemic_knowledge": "Known secrets"}]
"""

def extract_chapter_worldlines(book_id: str, chapter_num: int) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT para_num, text FROM paragraphs WHERE book_id = ? AND chapter_num = ? ORDER BY seq_order ASC", (book_id, chapter_num))
    rows = c.fetchall()
    if not rows:
        conn.close()
        return 0
    records = 0
    for i in range(0, len(rows), 6):
        chunk = rows[i:i + 6]
        first_p = chunk[0]["para_num"]
        combined = "\n".join([f"[P{r['para_num']}]: {r['text']}" for r in chunk])
        try:
            resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "system", "content": WORLDLINE_PROMPT}, {"role": "user", "content": combined}], format="json", options=LLM_OPTIONS)
            data = json.loads(resp['message']['content'])
            if isinstance(data, dict): data = data.get("entities", [data])
            with conn:
                for entry in data:
                    if not entry.get("entity_name"): continue
                    c.execute("INSERT INTO story_worldlines VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)",
                              (book_id, chapter_num, first_p, entry.get("entity_name", "Unknown").title(), entry.get("location_name", "Unknown").title(), entry.get("physical_state", "Normal"), entry.get("epistemic_knowledge", "None"), float(entry.get("timeline_day", chapter_num * 1.0))))
                    records += 1
        except Exception as e: print(f"⚠️ Worldline extraction error: {e}")
    conn.close()
    return records

def audit_continuity_paradoxes(book_id: str) -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT entity_name FROM story_worldlines WHERE book_id = ? ORDER BY entity_name ASC", (book_id,))
    entities = [r[0] for r in c.fetchall()]
    anomalies = []
    for ent in entities:
        c.execute("SELECT chapter_num, para_num, geographic_location, timeline_day FROM story_worldlines WHERE book_id = ? AND entity_name = ? ORDER BY timeline_day ASC, chapter_num ASC, para_num ASC", (book_id, ent))
        traj = c.fetchall()
        for i in range(1, len(traj)):
            p, cur = traj[i-1], traj[i]
            if p["geographic_location"] != cur["geographic_location"] and cur["timeline_day"] - p["timeline_day"] <= 0:
                anomalies.append(f"⚡ **Spatial Teleportation** [{ent}]: At `{p['geographic_location']}` (Ch {p['chapter_num']}) and `{cur['geographic_location']}` (Ch {cur['chapter_num']}) simultaneously on Day {cur['timeline_day']}.")
    conn.close()
    return anomalies

def render_3d_continuity_landscape(book_id: str) -> str:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT chapter_num, para_num, entity_name, geographic_location, physical_state, epistemic_knowledge, timeline_day FROM story_worldlines WHERE book_id = ? ORDER BY timeline_day ASC, chapter_num ASC, para_num ASC", (book_id,))
    rows = c.fetchall()
    conn.close()
    if not rows: return ""
    locations = sorted(list(set([r["geographic_location"] for r in rows if r["geographic_location"]])))
    loc_to_y = {loc: idx for idx, loc in enumerate(locations)}
    entity_data = {}
    for r in rows:
        ent = r["entity_name"]
        if ent not in entity_data: entity_data[ent] = {"x": [], "y": [], "z": [], "text": []}
        entity_data[ent]["x"].append(r["timeline_day"])
        entity_data[ent]["y"].append(loc_to_y.get(r["geographic_location"], 0))
        entity_data[ent]["z"].append(round(3.0 + ((r["chapter_num"] * 0.7) % 6.5), 1))
        entity_data[ent]["text"].append(f"<b>{ent}</b><br>{r['geographic_location']}<br>Day {r['timeline_day']} (Ch {r['chapter_num']}:P{r['para_num']})")
    fig = go.Figure()
    for ent, d in entity_data.items():
        if d["x"]: fig.add_trace(go.Scatter3d(x=d["x"], y=d["y"], z=d["z"], mode='lines+markers', name=ent, text=d["text"], hoverinfo="text", marker=dict(size=5), line=dict(width=4)))
    fig.update_layout(title=f"3D State-Space Trajectory — {ACTIVE_CONTEXT['book_title']}", scene=dict(xaxis_title='Timeline Days', yaxis=dict(title='Location', tickvals=list(loc_to_y.values()), ticktext=list(loc_to_y.keys())), zaxis_title='Tension & Stakes (1-10)'), template="plotly_dark", margin=dict(l=0, r=0, b=0, t=40))
    out_file = os.path.join(EXPORTS_DIR, f"{ACTIVE_CONTEXT['book_id']}_3D_Trajectory.html")
    fig.write_html(out_file, include_plotlyjs="cdn")
    return out_file
