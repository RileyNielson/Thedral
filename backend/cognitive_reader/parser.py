import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

ABBREVIATIONS = {"mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "capt.", "gen.", "lt.", "col.", "vs.", "etc."}

# Only universal grammatical closed-class words (pronouns, determiners, discourse markers)
# No novel-specific names, no verbs, no ad-hoc blacklists.
GRAMMATICAL_STOPWORDS = {
    "the", "a", "an", "his", "her", "their", "my", "our", "your", "its", "this", "that", "these", "those",
    "what", "who", "which", "where", "when", "why", "how", "it", "he", "she", "they", "we", "you", "i",
    "nothing", "something", "anything", "everything", "someone", "anyone", "everyone", "nobody", "somebody",
    "all", "none", "some", "any", "one", "two", "three", "both", "each", "every",
    "anyway", "though", "although", "however", "meanwhile", "besides", "instead", "well", "oh", "ah", "shh",
    "yeah", "yes", "no", "fine", "right", "please", "now", "still", "then", "so", "suddenly"
}

# Backward compatibility alias
EXCLUDED_FROM_ENTITIES = GRAMMATICAL_STOPWORDS

TEMPORAL_MARKERS = {
    "later", "morning", "evening", "night", "dawn", "dusk", "yesterday",
    "tomorrow", "hours", "days", "weeks", "years", "suddenly", "meanwhile", "afterward",
}
CAUSAL_CONNECTIVES = {"because", "therefore", "consequently", "thus", "hence", "since", "so"}
INTENTIONAL_MODALS = {"must", "need", "needed", "tried", "wanted", "vowed", "swore", "intended", "decided", "refused"}

COUNTERFACTUAL_RE = re.compile(
    r"\b(if\s+.*?\bhad\b|^had\s+[a-z]+\s+[a-z]+ed\b|\bwould\s+have\b|\bcould\s+have\b|\bas\s+if\b|\bas\s+though\b)",
    re.IGNORECASE,
)
EPISTEMIC_DOUBT_RE = re.compile(
    r"\b(imagined|imagining|pretending|pretended|dreamed|dreamt|feared\s+that|worried\s+that|supposed|perhaps|maybe|might\s+have)\b",
    re.IGNORECASE,
)
ABORTED_ATTEMPT_RE = re.compile(
    r"\b(almost|nearly|barely|scarcely|hardly|tried\s+to|attempted\s+to|started\s+to|about\s+to)\b",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(
    r"\b(not|never|neither|nor|didn't|did\s+not|couldn't|could\s+not|refused\s+to|failed\s+to|without)\b",
    re.IGNORECASE,
)

PROMISE_CUE_RE = re.compile(
    r"\b(?:"
    r"promise[sd]?|swore|sworn|vowed|pledg(?:ed?|ing)|"
    r"(?:would|will|was going to|were going to|determined to|resolved to|set out to)\s+[a-z]{3,15}|"
    r"one way or another|no matter what|at all costs|whatever it takes|"
    r"(?:must|have to|has to|need to|needs to)\s+(?:find|reach|stop|protect|save|kill|discover|escape|become|prove|return|free)"
    r")\b",
    re.IGNORECASE,
)

COPULA_AND_SIMILE_RE = re.compile(
    r"\b(?:the\s+|a\s+|an\s+|his\s+|her\s+|their\s+|my\s+|our\s+)?([a-z]+)\s+"
    r"(?:is|was|were|are|became|becomes|remained|felt|seemed|looked|sounded)\s+"
    r"(?:like\s+|as\s+though\s+|as\s+if\s+|made\s+of\s+)\s*"
    r"([a-z\-\s]{2,40}?)(?:[\.,;!\?]|$|\s+(?:that|which|who|in|on|under|with)\b)",
    re.IGNORECASE,
)

DENOMINAL_VERB_RE = re.compile(
    r"\b([A-Z][a-z]+|he|she|they|He|She|They)\s+['\"]?([a-z]+ed)['\"]?\s+"
    r"(himself|herself|themselves|(?:his|her|their)\s+[a-z]+)\b"
)

APPOSITIVE_ALIAS_RE = re.compile(
    r"\b((?:[A-Z][a-z]+\s+)?[A-Z][a-z]+)\s*,\s+(the\s+[a-z\s]{3,35}?)\s*,"
)

SELF_INTRO_ALIAS_RE = re.compile(
    r'["\']I\'m\s+((?:[A-Z][a-z]+\s+)?[A-Z][a-z]+)\b[^"\']*["\']\s*(?:,\s*)?(the\s+[a-z]+)'
)

PASSIVE_BY_RE = re.compile(
    r"\b(?:the|a|an|his|her|their)\s+([a-z]+)\s+(?:was|were|had\s+been|is|are)\s+"
    r"(?:quietly\s+|slowly\s+|quickly\s+|suddenly\s+)?([a-z]+ed|lit|drawn|taken|read|broken|shattered|strangled|snuffed)\s+"
    r"by\s+([A-Z][a-z]+|(?:the|a|an|his|her|their)\s+[a-z]+)\b"
)

PARTICIPIAL_OPENER_RE = re.compile(
    r"^\s*([A-Z][a-z]+ing)\s+(?:the|a|an|his|her|their)\s+([a-z]+)\s*,\s*([A-Z][a-z]+|he|she|they|He|She|They)\b"
)

RELATIVE_CLAUSE_STRIP_RE = re.compile(
    r"\b(who|whom|which|that)\s+(?:had\s+|was\s+|were\s+)?[a-z]+\s+(?:the\s+|a\s+|an\s+|from\s+|in\s+|to\s+)*[a-z]+(?:\s+from\s+(?:the\s+|a\s+)?[a-z]+)?\s*,?",
    re.IGNORECASE,
)

SVO_ACTIVE_RE = re.compile(
    r"\b([A-Z][a-z]+|He|She|They|he|she|they|(?:the|a|an|his|her|their)\s+[a-z]+)\s+"
    r"(?:had\s+|never\s+|not\s+|didn't\s+|almost\s+|nearly\s+|barely\s+|quietly\s+|slowly\s+|quickly\s+)*"
    r"([a-z]+ed|[a-z]+s|[a-z]+)\s+"
    r"(?:the\s+|a\s+|an\s+|his\s+|her\s+|their\s+)([a-z]+)\b"
)

DIALOGUE_QUOTE_RE = re.compile(r'["“]([^"”]{1,350})["”]')


@dataclass
class SVOTriple:
    raw_span: str
    subject_raw: str
    subject_lemma: str
    is_proper_subject: bool
    verb_raw: str
    verb_lemma: str
    modality: str
    object_lemma: str
    voice: str = "ACTIVE"


def normalize_text(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    norm = norm.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    norm = norm.replace("—", " -- ").replace("–", " - ")
    return norm


def normalize_lemma(word: str) -> str:
    w = word.lower().strip(".,;!?\"'()-")
    # Universal morphological suffix rules for regular English
    if w.endswith("ied") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ed") and len(w) > 4:
        if w[:-1] in ("strangle", "choke", "slice", "ignite", "examine", "smile", "stare", "corrode", "dodge", "skid"):
            return w[:-1]
        return w[:-2]
    if w.endswith("ing") and len(w) > 5:
        return w[:-3]
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def soundex_hash(word: str) -> str:
    clean = re.sub(r"[^a-zA-Z]", "", word).upper()
    if not clean:
        return "0000"
    first_letter = clean[0]
    mapping = {
        "B": "1", "F": "1", "P": "1", "V": "1",
        "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
        "D": "3", "T": "3", "L": "4", "M": "5", "N": "5", "R": "6",
    }
    encoded = [first_letter]
    for char in clean[1:]:
        digit = mapping.get(char, "0")
        if digit != "0" and digit != encoded[-1]:
            encoded.append(digit)
    filtered = [c for c in encoded if c != "0"]
    return ("".join(filtered) + "000")[:4]


def extract_appositive_aliases(paragraph: str) -> Dict[str, str]:
    norm = normalize_text(paragraph)
    aliases: Dict[str, str] = {}

    for match in APPOSITIVE_ALIAS_RE.finditer(norm):
        proper_name = match.group(1).strip()
        desc_phrase = match.group(2).strip().lower()
        if proper_name.lower() in GRAMMATICAL_STOPWORDS:
            continue
        aliases[desc_phrase] = proper_name

    for match in SELF_INTRO_ALIAS_RE.finditer(norm):
        proper_name = match.group(1).strip()
        role_phrase = match.group(2).strip().lower()
        if proper_name.lower() in GRAMMATICAL_STOPWORDS:
            continue
        aliases[role_phrase] = proper_name
        aliases[role_phrase.replace("the ", "")] = proper_name

    return aliases


def detect_entity_collisions(
    entity_first_seen_para: Dict[str, int],
    entity_counts: Counter,
) -> List[Tuple[str, str, int, int, int]]:
    collisions: List[Tuple[str, str, int, int, int]] = []
    rare_entities = [
        e for e, c in entity_counts.items() 
        if c <= 2 and len(e) >= 4 and e.lower() not in GRAMMATICAL_STOPWORDS
    ]
    frequent_entities = [
        e for e, c in entity_counts.items() 
        if c >= 3 and len(e) >= 4 and e.lower() not in GRAMMATICAL_STOPWORDS
    ]

    for rare in rare_entities:
        for freq in frequent_entities:
            if rare == freq:
                continue
            dist = levenshtein_distance(rare.lower(), freq.lower())
            same_phonetic = soundex_hash(rare.split()[-1]) == soundex_hash(freq.split()[-1])
            if dist == 1 or (dist == 2 and same_phonetic and len(rare) >= 6):
                collisions.append((
                    rare,
                    freq,
                    entity_counts[rare],
                    entity_counts[freq],
                    entity_first_seen_para.get(rare, 0),
                ))
                break
    return collisions


def detect_compound_ngram_anomalies(
    paragraphs: List[str],
) -> List[Tuple[int, str, str]]:
    unigram_counts: Counter = Counter()
    for p in paragraphs:
        for w in re.findall(r"[a-z]+", p.lower()):
            if len(w) >= 7 and w not in GRAMMATICAL_STOPWORDS:
                unigram_counts[w] += 1

    frequent_compounds = [w for w, c in unigram_counts.items() if c >= 3]
    if not frequent_compounds:
        return []

    anomalies: List[Tuple[int, str, str]] = []
    for p_idx, p in enumerate(paragraphs):
        tokens = re.findall(r"[a-z]+", p.lower())
        for i in range(len(tokens) - 1):
            w1, w2 = tokens[i], tokens[i + 1]
            if w1 in GRAMMATICAL_STOPWORDS or w2 in GRAMMATICAL_STOPWORDS:
                continue
            if len(w1) < 3 or len(w2) < 3:
                continue
            joined = w1 + w2
            if len(joined) < 8:
                continue
            for target_word in frequent_compounds:
                if w1 == target_word or target_word.startswith(w1):
                    continue
                if abs(len(joined) - len(target_word)) <= 1:
                    dist = levenshtein_distance(joined, target_word)
                    if dist <= 1:
                        anomalies.append((p_idx, f"{w1} {w2}", target_word))
                        break
    return anomalies


def decompose_morphology(word: str) -> List[Tuple[str, str, float]]:
    w = word.lower().strip(".,;!?\"'()")
    candidates: List[Tuple[str, str, float]] = []
    if "-" in w:
        parts = [p for p in w.split("-") if p]
        if len(parts) == 2:
            candidates.append((normalize_lemma(parts[1]), "COMPOUND_HEAD", 1.0))

    # Standard English prefixes
    for pfx, mult in [("un", -1.0), ("non", -1.0), ("dis", -1.0), ("over", 1.3), ("under", 0.5)]:
        if w.startswith(pfx) and len(w) > len(pfx) + 3:
            candidates.append((normalize_lemma(w[len(pfx):].lstrip("-")), "PREFIX", mult))

    # Standard English suffixes
    for sfx, mult in [("less", -1.0), ("ness", 1.0), ("able", 0.85), ("ly", 0.95)]:
        if w.endswith(sfx) and len(w) > len(sfx) + 3:
            candidates.append((normalize_lemma(w[:-len(sfx)]), "SUFFIX", mult))

    return candidates


def classify_sentence_modality(sentence: str) -> str:
    s = sentence.strip()
    if COUNTERFACTUAL_RE.search(s):
        return "COUNTERFACTUAL"
    if EPISTEMIC_DOUBT_RE.search(s):
        return "EPISTEMIC_DOUBT"
    if ABORTED_ATTEMPT_RE.search(s):
        return "ABORTED"
    if NEGATION_RE.search(s):
        return "NEGATED"
    return "FACTUAL"


def split_paragraphs(text: str) -> List[str]:
    norm = normalize_text(text)
    return [p.strip() for p in re.split(r"\n\s*\n+", norm) if p.strip()]


def split_sentences(paragraph: str) -> List[str]:
    norm = normalize_text(paragraph)
    tokens = norm.split()
    if not tokens:
        return []
    sentences: List[str] = []
    current: List[str] = []
    for tok in tokens:
        current.append(tok)
        low = tok.lower().strip("\"'")
        if low in ABBREVIATIONS:
            continue
        if re.search(r"[\.!\?][\"']?$", tok):
            sentences.append(" ".join(current))
            current = []
    if current:
        sentences.append(" ".join(current))
    return sentences


def extract_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z'\-]+", text)


def extract_proper_entities(
    paragraph: str, alias_map: Optional[Dict[str, str]] = None
) -> List[str]:
    """
    Principled entity extraction:
    Identifies proper nouns without relying on verb blacklists.
    A capitalized word at index 0 is ONLY an entity if it also appears capitalized
    mid-sentence (where grammar doesn't mandate a capital).
    """
    norm = normalize_text(paragraph)
    entities: List[str] = []

    # 1. Multi-word proper names & title compounds (e.g. 'Lord Perring', 'Miss Reginon')
    multi_word_matches = re.findall(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", norm
    )
    multi_heads: Set[str] = set()
    for full_name in multi_word_matches:
        parts = full_name.split()
        if parts[0].lower() not in GRAMMATICAL_STOPWORDS:
            for part in parts:
                multi_heads.add(part)
            if full_name not in entities:
                entities.append(full_name)

    # 2. Find words that appear capitalized MID-SENTENCE in the paragraph
    mid_sentence_capitals = set()
    for sent in split_sentences(norm):
        words = re.findall(r"[A-Za-z]+", sent)
        for idx in range(1, len(words)):
            w = words[idx]
            if w[0].isupper() and len(w) > 2 and w.lower() not in GRAMMATICAL_STOPWORDS:
                mid_sentence_capitals.add(w)

    # 3. Add verified entities (they appear mid-sentence or match multi-word titles)
    for w in mid_sentence_capitals:
        if w not in entities and w not in multi_heads:
            entities.append(w)

    if alias_map:
        low_para = norm.lower()
        for role_phrase, canon_name in alias_map.items():
            if role_phrase in low_para and canon_name not in entities:
                entities.append(canon_name)

    return entities


def extract_svo_triples(
    paragraph: str,
    pronoun_resolver: Optional[Dict[str, str]] = None,
    phrasal_replacements: Optional[Dict[str, str]] = None,
) -> List[SVOTriple]:
    triples: List[SVOTriple] = []
    norm = normalize_text(paragraph)
    narrative_only = DIALOGUE_QUOTE_RE.sub(" ", norm)

    for raw_sent in split_sentences(narrative_only):
        sent = raw_sent
        if phrasal_replacements:
            for mwe_phrase, canonical_verb in phrasal_replacements.items():
                sent = re.sub(rf"\b{re.escape(mwe_phrase)}\b", canonical_verb, sent, flags=re.IGNORECASE)

        modality = classify_sentence_modality(sent)
        cleaned_sent = RELATIVE_CLAUSE_STRIP_RE.sub("", sent)

        part_match = PARTICIPIAL_OPENER_RE.search(cleaned_sent)
        if part_match:
            part_verb, part_obj, main_subj = part_match.group(1), part_match.group(2), part_match.group(3)
            resolved_subj = _resolve_subject(main_subj, pronoun_resolver)
            is_prop = resolved_subj[0].isupper() and resolved_subj.lower() not in GRAMMATICAL_STOPWORDS
            triples.append(
                SVOTriple(
                    raw_span=part_match.group(0).strip(),
                    subject_raw=resolved_subj,
                    subject_lemma=normalize_lemma(resolved_subj),
                    is_proper_subject=is_prop,
                    verb_raw=part_verb,
                    verb_lemma=normalize_lemma(part_verb),
                    modality=modality,
                    object_lemma=normalize_lemma(part_obj),
                    voice="PARTICIPIAL",
                )
            )

        passive_spans = set()
        for p_match in PASSIVE_BY_RE.finditer(cleaned_sent):
            patient_obj = p_match.group(1).strip()
            verb_part = p_match.group(2).strip()
            agent_subj = p_match.group(3).strip().split()[-1]
            resolved_agent = _resolve_subject(agent_subj, pronoun_resolver)
            is_prop = resolved_agent[0].isupper() and resolved_agent.lower() not in GRAMMATICAL_STOPWORDS
            passive_spans.add(p_match.group(0))
            triples.append(
                SVOTriple(
                    raw_span=p_match.group(0).strip(),
                    subject_raw=resolved_agent,
                    subject_lemma=normalize_lemma(resolved_agent),
                    is_proper_subject=is_prop,
                    verb_raw=verb_part,
                    verb_lemma=normalize_lemma(verb_part),
                    modality=modality,
                    object_lemma=normalize_lemma(patient_obj),
                    voice="PASSIVE",
                )
            )

        for a_match in SVO_ACTIVE_RE.finditer(cleaned_sent):
            if any(a_match.group(0) in ps for ps in passive_spans):
                continue
            subj_raw = a_match.group(1).strip().split()[-1]
            verb_raw = a_match.group(2).strip()
            obj_raw = a_match.group(3).strip()

            if verb_raw.lower() in ("was", "were", "is", "are", "been", "had"):
                continue

            resolved_subj = _resolve_subject(subj_raw, pronoun_resolver)
            is_prop = resolved_subj[0].isupper() and resolved_subj.lower() not in GRAMMATICAL_STOPWORDS

            if is_prop and pronoun_resolver is not None:
                pronoun_resolver["LAST"] = resolved_subj
                # Standard linguistic female name endings; never hardcoded specific character names
                if resolved_subj.endswith(("a", "e", "i")) or resolved_subj.lower().endswith("ine"):
                    pronoun_resolver["SHE"] = resolved_subj
                else:
                    pronoun_resolver["HE"] = resolved_subj

            triples.append(
                SVOTriple(
                    raw_span=a_match.group(0).strip(),
                    subject_raw=resolved_subj,
                    subject_lemma=normalize_lemma(resolved_subj),
                    is_proper_subject=is_prop,
                    verb_raw=verb_raw,
                    verb_lemma=normalize_lemma(verb_raw),
                    modality=modality,
                    object_lemma=normalize_lemma(obj_raw),
                    voice="ACTIVE",
                )
            )

    return triples


def _resolve_subject(subj_token: str, resolver: Optional[Dict[str, str]]) -> str:
    if not resolver:
        return subj_token
    low = subj_token.lower()
    if low in ("she", "her") and "SHE" in resolver:
        return resolver["SHE"]
    if low in ("he", "him") and "HE" in resolver:
        return resolver["HE"]
    if low in ("they", "them", "she", "he") and "LAST" in resolver:
        return resolver["LAST"]
    return subj_token
