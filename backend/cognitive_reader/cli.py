import argparse
import json
import sys
from pathlib import Path

from cognitive_reader.engine import CognitiveEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cognitive-reader",
        description="Deterministic, zero-LLM cognitive reading comprehension & telemetry CLI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_p = sub.add_parser("analyze", help="Analyze a manuscript or text file.")
    analyze_p.add_argument("filepath", type=Path, help="Path to .txt or .md file")
    analyze_p.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    analyze_p.add_argument("--notes-only", action="store_true", help="Print plain-English reader notes only")

    args = parser.parse_args()

    if args.command == "analyze":
        if not args.filepath.exists():
            print(f"Error: File '{args.filepath}' not found.", file=sys.stderr)
            sys.exit(1)
        text = args.filepath.read_text(encoding="utf-8")
        engine = CognitiveEngine()
        report = engine.analyze_document(text)
        if args.notes_only:
            for note in report.reader_notes:
                print(f"[Paragraph {note.paragraph_index}] {note.label}\n  > {note.body}\n")
        else:
            indent = 2 if args.pretty else None
            print(json.dumps(report.to_dict(), indent=indent))


if __name__ == "__main__":
    main()