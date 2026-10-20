import json
import re
import sqlite3
from typing import Dict, Iterator, List, Optional, Tuple


class WiktionaryFullIngestor:
    """
    Extracts multi-table linguistic intelligence from a Wiktionary SQLite DB:
    - Senses & Glosses
    - Nyms (Synonyms, Antonyms, Hypernyms, Meronyms) -> concept_edges
    - Forms (Irregular inflections) -> inflected_forms
    - Qualifiers/Tags (figurative, sarcastic, formal, vulgar, archaic)
    - IPA / Phonetics -> plosive vs sonorant prosody scores
    """

    def __init__(self, wiktionary_db_path: str) -> None:
        self.conn = sqlite3.connect(wiktionary_db_path)
        self.conn.row_factory = sqlite3.Row
        self.tables = self._discover_tables()

    def _discover_tables(self) -> Dict[str, List[str]]:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")
        schema: Dict[str, List[str]] = {}
        for (t_name,) in cur.fetchall():
            if t_name.startswith("sqlite_"):
                continue
            cur.execute(f'PRAGMA table_info("{t_name}")')
            schema[t_name] = [r[1] for r in cur.fetchall()]
        return schema

    def iter_rich_entries(self) -> Iterator[Dict[str, object]]:
        cur = self.conn.cursor()

        # Case 1: Wiktextract / Kaikki JSON column
        for t_name, cols in self.tables.items():
            low_map = {c.lower(): c for c in cols}
            if "word" in low_map and ("data" in low_map or "json" in low_map):
                json_col = low_map.get("data") or low_map["json"]
                word_col = low_map["word"]
                cur.execute(f'SELECT "{word_col}", "{json_col}" FROM "{t_name}"')
                for word, raw_json in cur:
                    if not word or not raw_json:
                        continue
                    try:
                        doc = json.loads(raw_json)
                    except Exception:
                        continue
                    if doc.get("lang_code", "en") != "en":
                        continue
                    yield self._parse_wiktextract_json(str(word), doc)
                return

        # Case 2: Normalized Relational Wiktionary SQLite Tables
        sense_table = self._find_table_with({"word", "gloss"}) or self._find_table_with({"lemma", "definition"})
        if sense_table:
            cols = {c.lower(): c for c in self.tables[sense_table]}
            w_col = cols.get("word") or cols.get("lemma")
            p_col = cols.get("pos") or cols.get("part_of_speech")
            g_col = cols.get("gloss") or cols.get("definition")
            t_col = cols.get("tags") or cols.get("qualifiers")

            select_cols = [f'"{w_col}" AS word', f'"{g_col}" AS gloss']
            select_cols.append(f'"{p_col}" AS pos' if p_col else "'noun' AS pos")
            select_cols.append(f'"{t_col}" AS tags' if t_col else "'' AS tags")

            cur.execute(f"SELECT {', '.join(select_cols)} FROM \"{sense_table}\"")
            for row in cur:
                yield {
                    "lemma": str(row["word"]).lower().strip(),
                    "pos": str(row["pos"] or "noun").lower().strip(),
                    "gloss": str(row["gloss"] or ""),
                    "tags": str(row["tags"] or "").lower().split(","),
                    "nyms": [],
                    "forms": [],
                    "ipa": "",
                }

    def iter_nym_edges(self) -> Iterator[Tuple[str, str, str, float]]:
        nym_table = self._find_table_with({"word", "nym", "type"}) or self._find_table_with({"source", "target", "relation"})
        if not nym_table:
            return
        cols = {c.lower(): c for c in self.tables[nym_table]}
        s_col = cols.get("word") or cols.get("source")
        t_col = cols.get("nym") or cols.get("target")
        r_col = cols.get("type") or cols.get("relation")

        cur = self.conn.cursor()
        cur.execute(f'SELECT "{s_col}", "{r_col}", "{t_col}" FROM "{nym_table}"')
        for src, rel, tgt in cur:
            if src and tgt and rel:
                yield (str(src).lower(), str(rel).upper(), str(tgt).lower(), 0.95)

    def _find_table_with(self, required_cols: set) -> Optional[str]:
        for t_name, cols in self.tables.items():
            if required_cols.issubset({c.lower() for c in cols}):
                return t_name
        return None

    def _parse_wiktextract_json(self, word: str, doc: dict) -> Dict[str, object]:
        pos = str(doc.get("pos", "noun")).lower()
        forms = [
            f.get("form", "").lower()
            for f in doc.get("forms", [])
            if isinstance(f, dict) and f.get("form")
        ]
        ipas = [
            s.get("ipa", "")
            for s in doc.get("sounds", [])
            if isinstance(s, dict) and s.get("ipa")
        ]
        nyms: List[Tuple[str, str]] = []
        for rel_key in ("synonyms", "antonyms", "hypernyms", "hyponyms", "holonyms", "meronyms"):
            for item in doc.get(rel_key, []):
                if isinstance(item, dict) and item.get("word"):
                    nyms.append((rel_key.upper(), str(item["word"]).lower()))

        senses = doc.get("senses", [])
        glosses = []
        tags = []
        for s in senses:
            if not isinstance(s, dict):
                continue
            glosses.extend(s.get("glosses", []))
            tags.extend(s.get("tags", []))
            tags.extend(s.get("qualifiers", []))
            for rel_key in ("synonyms", "antonyms", "hypernyms", "meronyms"):
                for item in s.get(rel_key, []):
                    if isinstance(item, dict) and item.get("word"):
                        nyms.append((rel_key.upper(), str(item["word"]).lower()))

        return {
            "lemma": word.lower().strip(),
            "pos": pos,
            "gloss": " ; ".join(str(g) for g in glosses if g),
            "tags": [str(t).lower() for t in tags],
            "nyms": nyms,
            "forms": forms,
            "ipa": ipas[0] if ipas else "",
        }


def compute_phonetic_texture(ipa_or_word: str) -> Dict[str, float]:
    clean = re.sub(r"[^a-zʃʒθðŋ]", "", ipa_or_word.lower())
    if not clean:
        return {"plosive_impact": 0.0, "sonorant_flow": 0.0}
    plosives = sum(1 for ch in clean if ch in "ktpbdg")
    sonorants = sum(1 for ch in clean if ch in "lrmnsʃ")
    length = max(1, len(clean))
    return {
        "plosive_impact": round(min(1.0, (plosives / length) * 2.5), 3),
        "sonorant_flow": round(min(1.0, (sonorants / length) * 2.2), 3),
    }