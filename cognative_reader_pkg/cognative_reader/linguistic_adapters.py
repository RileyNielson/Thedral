from typing import List, Optional, Set, Tuple
from cognitive_reader.parser import SVOTriple, extract_svo_triples, normalize_lemma

try:
    import spacy
    _NLP = spacy.load("en_core_web_sm", disable=["ner"])
except Exception:
    _NLP = None

try:
    from nltk.corpus import wordnet as wn
    wn.synsets("anchor")
    _WN_AVAILABLE = True
except Exception:
    _WN_AVAILABLE = False

WORDNET_LEXNAME_TO_DOMAIN = {
    "noun.feeling": ("ABSTRACT_STATE", 0.12),
    "noun.cognition": ("ABSTRACT_STATE", 0.15),
    "noun.attribute": ("ABSTRACT_STATE", 0.20),
    "noun.state": ("ABSTRACT_STATE", 0.18),
    "noun.communication": ("SOCIAL_CONSTRUCT", 0.25),
    "noun.group": ("SOCIAL_CONSTRUCT", 0.25),
    "noun.artifact": ("ARTIFACT_SOLID", 0.94),
    "noun.object": ("ARTIFACT_SOLID", 0.92),
    "noun.substance": ("SUBSTANCE_LIQUID", 0.88),
    "noun.person": ("ANIMATE_BEING", 0.95),
    "noun.animal": ("ANIMATE_BEING", 0.95),
    "noun.body": ("ANIMATE_BEING", 0.96),
    "noun.location": ("SPACE_CONTAINER", 0.92),
}


def resolve_wordnet_ontology(
    lemma: str, context_lemmas: Optional[Set[str]] = None
) -> Optional[Tuple[str, float, List[str]]]:
    if not _WN_AVAILABLE:
        return None
    synsets = wn.synsets(lemma)
    if not synsets:
        return None
    best_syn = synsets[0]
    if len(synsets) > 1 and context_lemmas:
        best_score = -1
        for syn in synsets:
            def_tokens = set(syn.definition().lower().split())
            overlap = len(def_tokens & context_lemmas)
            if overlap > best_score:
                best_score = overlap
                best_syn = syn

    domain, conc = WORDNET_LEXNAME_TO_DOMAIN.get(best_syn.lexname(), ("ARTIFACT_SOLID", 0.55))
    related: List[str] = []
    for hyper in best_syn.hypernyms():
        for l in hyper.lemmas():
            related.append(l.name().lower())
    return domain, conc, related


def extract_ast_svo_triples(
    paragraph: str,
    pronoun_resolver: Optional[dict] = None,
    phrasal_replacements: Optional[dict] = None,
) -> List[SVOTriple]:
    # Always use the deterministic regex/chunking parser to guarantee consistent cross-platform behavior
    return extract_svo_triples(
        paragraph,
        pronoun_resolver=pronoun_resolver,
        phrasal_replacements=phrasal_replacements,
    )