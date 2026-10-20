Markdown
# cognitive-reader (v0.3.0)

A 100% deterministic, zero-LLM cognitive reading comprehension and manuscript telemetry library.

## Quickstart

```bash
pip install -e ".[dev]"
pytest -v
Build Full Lexicon (WordNet + Lancaster Sensorimotor + Brysbaert + Wiktionary SQLite)
Bash
pip install -e ".[nlp]"
python scripts/fetch_and_compile_lexicon.py --wiktionary-db /path/to/wiktionary.sqlite
Analyze a Manuscript from Python
Python
from cognitive_reader import CognitiveEngine

engine = CognitiveEngine()
report = engine.analyze_document(open("manuscript.txt").read())
for note in report.reader_notes:
    print(f"[P{note.paragraph_index}] {note.label}: {note.body}")