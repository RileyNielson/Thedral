from backend.database import get_db
from backend.config import STUDIO_MODEL, LLM_OPTIONS, ENABLE_AI
from backend.text_utils import html_to_text

def generate_query_synopsis(book_id: str | None = None) -> str:
    if not ENABLE_AI:
        return "Query Synopsis generation requires local AI. Running in Pure Math Mode."

    conn = get_db()
    c = conn.cursor()

    if not book_id:
        c.execute("""
            SELECT id, title FROM binder_nodes 
            WHERE node_type = 'BOOK' AND (is_archived IS NULL OR is_archived = 0) 
            ORDER BY sort_order ASC LIMIT 1
        """)
        book = c.fetchone()
        if not book:
            c.execute("SELECT id, title FROM binder_nodes WHERE node_type = 'BOOK' LIMIT 1")
            book = c.fetchone()
        book_id = book["id"] if book else None

    c.execute("""
        SELECT ch.title as ch_title, s.title as sc_title, s.synopsis, s.content
        FROM binder_nodes s
        JOIN binder_nodes ch ON s.parent_id = ch.id
        WHERE ch.parent_id = ? AND s.node_type = 'SCENE'
        ORDER BY ch.sort_order ASC, s.sort_order ASC
    """, (book_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return "Not enough scenes drafted to compile an industry query synopsis."

    spine_bullets = []
    for r in rows:
        plain_content = html_to_text(r["content"] or "")
        summary = r["synopsis"] or (plain_content[:140] + "..." if plain_content else "")
        if summary.strip():
            spine_bullets.append(f"- [{r['ch_title']} / {r['sc_title']}]: {summary}")

    causal_timeline = "\n".join(spine_bullets[:25])

    prompt = f"""You are a Veteran Literary Agent and Commercial Fiction Publishing Executive.
Analyze this book's causal plot spine and write a clean, compelling 1-Page Industry Query Synopsis (approx 450-500 words).

FORMAT STRICTLY INTO:
1. THE HOOK & PROTAGONIST'S DILEMMA (1 concise paragraph)
2. THE ESCALATING CONFLICT & MAJOR TURNING POINTS (2 narrative paragraphs)
3. THE CLIMAX & ULTIMATE RESOLUTION (1 paragraph - reveal the ending completely; literary agents require spoilers)

NO MARKETING FLUFF. FOCUS PURELY ON CHARACTER MOTIVE, CAUSE, AND EFFECT.

CAUSAL PLOT SPINE:
{causal_timeline}
"""

    try:
        import ollama
        resp = ollama.chat(
            model=STUDIO_MODEL, 
            messages=[{"role": "user", "content": prompt}], 
            options=LLM_OPTIONS
        )
        return resp['message']['content']
    except Exception as e:
        return f"Could not generate query synopsis: {e}"
