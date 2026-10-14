"""Read-only access to the locally installed English Wiktionary SQLite dataset."""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import re
import sqlite3
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Iterable

from backend.config import WIKTIONARY_DB_PATH

DATASET_URL = (
    "https://huggingface.co/datasets/cstr/en-wiktionary-sqlite-full/resolve/"
    "main/en_wiktionary_normalized_full.db.gz?download=true"
)
DATASET_CARD_URL = "https://huggingface.co/datasets/cstr/en-wiktionary-sqlite-full"
LICENSE = "CC BY-SA 4.0"

_WORD_COLUMNS = (
    "word", "lemma", "form", "word_form", "form_text", "synonym", "synonym_word",
    "synonym_text", "related_word", "related_text", "target_word", "link_text",
)
_FORM_TABLE_NAMES = {"forms", "word_forms", "wordforms", "inflections"}
_SYNONYM_TABLE_NAMES = {"synonyms", "synonym"}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1].lower() for row in conn.execute(f"PRAGMA table_info({_quote(table)})")}


def _tables(conn: sqlite3.Connection) -> dict[str, str]:
    return {
        row[0].lower(): row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def _english_filter(alias: str, columns: set[str]) -> str:
    if "lang" in columns:
        return f" AND lower({_quote(alias)}.{_quote('lang')}) IN ('english', 'en')"
    if "language" in columns:
        return f" AND lower({_quote(alias)}.{_quote('language')}) IN ('english', 'en')"
    return ""


def _lookup_words(words: Iterable[str]) -> list[str]:
    # The dataset indexes lower(word); querying lowercase terms keeps lookups fast.
    return sorted({word.strip().lower() for word in words if word and word.strip()})


def _validate_database(path: str | Path) -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
        try:
            tables = _tables(conn)
            if "entries" not in tables:
                return False, "Missing required entries table"
            entry_columns = _table_columns(conn, tables["entries"])
            if not {"word", "id"} <= entry_columns:
                return False, "The entries table must contain id and word columns"
            if not ({"lang", "language"} & entry_columns):
                return False, "The entries table must identify entry languages"
            if "senses" not in tables or "glosses" not in tables:
                return False, "Missing required senses or glosses table"
            if not {"id", "entry_id"} <= _table_columns(conn, tables["senses"]):
                return False, "The senses table must contain id and entry_id columns"
            if not {"sense_id", "gloss_text"} <= _table_columns(conn, tables["glosses"]):
                return False, "The glosses table must contain sense_id and gloss_text columns"
            return True, "English Wiktionary SQLite database is ready"
        finally:
            conn.close()
    except (OSError, sqlite3.Error) as exc:
        return False, f"Could not read Wiktionary database: {exc}"


def _connect_readonly(database_path: str | Path | None = None) -> sqlite3.Connection | None:
    path = Path(database_path or WIKTIONARY_DB_PATH)
    if not path.is_file():
        return None
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_lexicon_status(database_path: str | Path | None = None) -> dict:
    path = Path(database_path or WIKTIONARY_DB_PATH)
    if not path.is_file():
        return {
            "available": False,
            "path": str(path),
            "source": DATASET_CARD_URL,
            "license": LICENSE,
            "message": "Wiktionary is not installed. The reader works without it.",
        }
    valid, message = _validate_database(path)
    return {
        "available": valid,
        "path": str(path),
        "source": DATASET_CARD_URL,
        "license": LICENSE,
        "message": message,
        "size_bytes": path.stat().st_size,
    }


def download_wiktionary_database() -> dict:
    """Stream the public compressed dataset, validate it, then atomically install it."""
    target = Path(WIKTIONARY_DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    compressed_path = None
    unpacked_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="wiktionary-", suffix=".db.gz", dir=target.parent, delete=False) as temp:
            compressed_path = Path(temp.name)
            request = urllib.request.Request(
                DATASET_URL,
                headers={"User-Agent": "Thedral/1.0 (local Wiktionary dataset installer)"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                total_bytes = int(response.headers.get("Content-Length", "0") or 0)
                downloaded = 0
                next_report = 16 * 1024 * 1024
                while chunk := response.read(1024 * 1024):
                    temp.write(chunk)
                    downloaded += len(chunk)
                    if downloaded >= next_report:
                        if total_bytes:
                            progress = f"{downloaded / 1024**2:.0f} / {total_bytes / 1024**2:.0f} MB"
                        else:
                            progress = f"{downloaded / 1024**2:.0f} MB"
                        print(f"Downloading English Wiktionary: {progress}", file=sys.stderr, flush=True)
                        next_report = downloaded + 16 * 1024 * 1024

        fd, unpacked_name = tempfile.mkstemp(prefix="wiktionary-", suffix=".db", dir=target.parent)
        os.close(fd)
        unpacked_path = Path(unpacked_name)
        with gzip.open(compressed_path, "rb") as source, unpacked_path.open("wb") as dest:
            shutil.copyfileobj(source, dest, length=1024 * 1024)
        valid, message = _validate_database(unpacked_path)
        if not valid:
            raise ValueError(f"Downloaded file is not a supported Wiktionary database: {message}")
        os.replace(unpacked_path, target)
        return get_lexicon_status()
    finally:
        for temporary in (compressed_path, unpacked_path):
            if temporary and temporary.exists():
                temporary.unlink()


def install_wiktionary_database(source_path: str | Path) -> dict:
    """Install a previously downloaded dataset without changing its SQLite contents."""
    source = Path(source_path)
    valid, message = _validate_database(source)
    if not valid:
        raise ValueError(f"Unsupported Wiktionary database: {message}")
    target = Path(WIKTIONARY_DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix="wiktionary-", suffix=".db", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return get_lexicon_status()


def _related_terms(conn: sqlite3.Connection, words: Iterable[str]) -> set[str]:
    names = _tables(conn)
    entries = names.get("entries")
    senses = names.get("senses")
    if not entries or not senses:
        return set()
    entry_columns = _table_columns(conn, entries)
    sense_columns = _table_columns(conn, senses)
    if not {"id", "word"} <= entry_columns or not {"id", "entry_id"} <= sense_columns:
        return set()
    words = _lookup_words(words)
    if not words:
        return set()
    placeholders = ",".join("?" for _ in words)
    found: set[str] = set()
    for table_key, table in names.items():
        if (
            table_key not in _SYNONYM_TABLE_NAMES
            and "synonym" not in table_key
            and table_key not in {"sense_links", "semantic_relations"}
        ):
            continue
        columns = _table_columns(conn, table)
        target_column = next((column for column in _WORD_COLUMNS if column in columns and column not in {"word", "lemma"}), None)
        if target_column is None:
            continue
        if "sense_id" in columns:
            join = f"JOIN {_quote(senses)} s ON r.{_quote('sense_id')} = s.{_quote('id')}"
            source = f"JOIN {_quote(entries)} e ON s.{_quote('entry_id')} = e.{_quote('id')}"
        elif "entry_id" in columns:
            join = ""
            source = f"JOIN {_quote(entries)} e ON r.{_quote('entry_id')} = e.{_quote('id')}"
        else:
            continue
        relation_column = next(
            (column for column in ("relation_type", "link_type", "type") if column in columns),
            None,
        )
        relation_filter = ""
        if relation_column:
            relation_filter = (
                f" AND lower(r.{_quote(relation_column)}) IN "
                "('synonym', 'synonyms', 'syn')"
            )
        query = (
            f"SELECT DISTINCT r.{_quote(target_column)} FROM {_quote(table)} r "
            f"{join} {source} WHERE lower(e.{_quote('word')}) IN ({placeholders})"
            + _english_filter("e", entry_columns)
            + relation_filter
            + f" AND r.{_quote(target_column)} IS NOT NULL LIMIT 500"
        )
        found.update(str(row[0]).strip() for row in conn.execute(query, words) if str(row[0]).strip())
    return found


def _word_forms(conn: sqlite3.Connection, words: Iterable[str]) -> set[str]:
    names = _tables(conn)
    entries = names.get("entries")
    if not entries:
        return set()
    entry_columns = _table_columns(conn, entries)
    if not {"id", "word"} <= entry_columns:
        return set()
    words = _lookup_words(words)
    if not words:
        return set()
    placeholders = ",".join("?" for _ in words)
    found: set[str] = set()
    for table_key, table in names.items():
        if table_key not in _FORM_TABLE_NAMES and not ("form" in table_key and table_key not in {"head_templates"}):
            continue
        columns = _table_columns(conn, table)
        surface_column = next((column for column in ("form", "word_form", "form_text", "surface", "word") if column in columns), None)
        if not surface_column:
            continue
        if "entry_id" in columns:
            relation = f"f.{_quote('entry_id')} = e.{_quote('id')}"
        elif "lemma" in columns:
            relation = f"lower(f.{_quote('lemma')}) = lower(e.{_quote('word')})"
        else:
            continue
        query = (
            f"SELECT DISTINCT f.{_quote(surface_column)} FROM {_quote(table)} f "
            f"JOIN {_quote(entries)} e ON {relation} "
            f"WHERE lower(e.{_quote('word')}) IN ({placeholders})"
            + _english_filter("e", entry_columns)
            + f" AND f.{_quote(surface_column)} IS NOT NULL LIMIT 500"
        )
        found.update(str(row[0]).strip() for row in conn.execute(query, words) if str(row[0]).strip())
    return found


def _plain_word(word: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z'-]+", word))


def _regular_forms(word: str) -> set[str]:
    if len(word) < 3:
        return set()
    stem = word[:-1] if word.endswith("e") else word
    plural = word[:-1] + "ies" if re.search(r"[^aeiou]y$", word) else word + ("es" if word.endswith(("s", "x", "z", "ch", "sh")) else "s")
    past = word[:-1] + "ied" if re.search(r"[^aeiou]y$", word) else stem + "ed"
    return {plural, past, stem + "ing"}


def is_english_word(word: str, database_path: str | Path | None = None) -> bool:
    return word.casefold() in english_words([word], database_path)


def english_words(words: Iterable[str], database_path: str | Path | None = None) -> set[str]:
    conn = _connect_readonly(database_path)
    if conn is None:
        return set()
    try:
        names = _tables(conn)
        entries = names.get("entries")
        if not entries:
            return set()
        columns = _table_columns(conn, entries)
        normalized = _lookup_words(words)
        if not normalized:
            return set()
        placeholders = ",".join("?" for _ in normalized)
        query = (
            f"SELECT DISTINCT lower({_quote('word')}) FROM {_quote(entries)} "
            f"WHERE lower({_quote('word')}) IN ({placeholders})"
            + _english_filter(entries, columns)
        )
        return {row[0] for row in conn.execute(query, normalized)}
    finally:
        conn.close()


def expand_lexical_terms(
    seeds: Iterable[str],
    database_path: str | Path | None = None,
    limit: int = 120,
) -> set[str]:
    """Add bounded English synonyms and inflections for a small cue vocabulary."""
    original = {word.strip() for word in seeds if word and word.strip()}
    conn = _connect_readonly(database_path)
    if conn is None or not original:
        if conn:
            conn.close()
        return set()
    try:
        related = {word for word in _related_terms(conn, original) if _plain_word(word)}
        forms = {word for word in _word_forms(conn, original | related) if _plain_word(word)}
        covered = {word.lower() for word in forms}
        # The dataset omits some everyday words, so regular inflections fill the gaps.
        fallback = set()
        for seed in original:
            if _plain_word(seed) and not any(form.startswith(seed.lower()[:max(3, len(seed) - 2)]) for form in covered):
                fallback |= _regular_forms(seed.lower())
        expanded = {word.lower() for word in related | forms | fallback if 1 < len(word) <= 40}
        return set(sorted(expanded - {seed.lower() for seed in original})[:max(0, limit)])
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the local English Wiktionary SQLite database.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--download", action="store_true", help="Download and install the public Hugging Face dataset.")
    source.add_argument("--install", metavar="DB", help="Validate and install an existing SQLite database.")
    parser.add_argument("--status", action="store_true", help="Print local installation status.")
    args = parser.parse_args()
    if args.install:
        print(install_wiktionary_database(args.install))
    elif args.download:
        print(download_wiktionary_database())
    else:
        print(get_lexicon_status())


if __name__ == "__main__":
    main()
