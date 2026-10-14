import re
from functools import lru_cache
from pathlib import Path

from backend.config import WIKTIONARY_DB_PATH
from backend.reader_feel import analyze_reader_feel
from backend.text_utils import html_to_text
from backend.wiktionary_lexicon import expand_lexical_terms, get_lexicon_status


_STOP_WORDS = {
    "about", "after", "again", "against", "among", "because", "before", "being",
    "between", "could", "does", "doing", "down", "each", "from", "have", "having",
    "into", "just", "more", "most", "other", "over", "same", "should", "some",
    "such", "than", "that", "their", "them", "then", "there", "these", "they",
    "this", "those", "through", "under", "until", "very", "were", "what", "when",
    "where", "which", "while", "whom", "with", "would", "your", "also", "been",
    "will", "shall", "must", "need", "needs", "want", "wants", "make", "made",
    "someone", "somebody", "anyone", "anybody", "thing", "things", "someone's",
}
_PROMISE_CUES = re.compile(
    r"\b(?:promise[sd]?|swore|sworn|vowed|owe[sd]?|have to|has to|"
    r"must|won['’]t stop|won['’]t rest|one day|"
    r"was going to|set out to|need to|needs to)\b",
    re.IGNORECASE,
)
_POSITIVE_CUES = re.compile(
    r"\b(?:found|saved|won|escaped|survived|succeeded|success|worked|"
    r"agreed|accepted|opened|arrived|managed|rescued|reached|kept|"
    r"answered|returned|remembered|learned|discovered|revealed|admitted)\b",
    re.IGNORECASE,
)
_NEGATIVE_CUES = re.compile(
    r"\b(?:failed|lost|refused|denied|rejected|broke|missed|couldn['’]t|"
    r"wouldn['’]t|cannot|can['’]t|dead|died|death|killed|stopped|"
    r"betrayed|lied|wounded|injured|wrong)\b",
    re.IGNORECASE,
)
_RESOLUTION_CUES = re.compile(
    r"\b(?:finally|at last|found|saved|opened|answered|returned|"
    r"remembered|learned|discovered|revealed|admitted|chose|decided|"
    r"understood|kept the promise|fulfilled)\b",
    re.IGNORECASE,
)
_LOSS_CUES = re.compile(
    r"\b(?:died|dies|funeral|grief|mourn(?:ed|ing)?|goodbye|killed|murdered|"
    r"butchered|passed away|death of|never came back|(?:was|is) gone forever)\b",
    re.IGNORECASE,
)
_CARE_CUES = re.compile(
    r"\b(?:loved(?! to\b)|trusted|protected|comforted|waited for|slept beside|"
    r"loyal|best friend|cared for|raised me|taught me|tucked me|"
    r"held (?:(?:the )?\w+['’]s|his|her|their|my|our) (?:hand|paw|face|head|body)s?)\b",
    re.IGNORECASE,
)
_VULNERABILITY_CUES = re.compile(
    r"\b(?:afraid|alone|ashamed|terrified|cried|wept|sobbed|"
    r"begged|confessed|admitted|couldn['’]t stop crying)\b",
    re.IGNORECASE,
)
_REVERSAL_CUES = re.compile(
    r"\b(?:instead|turned out|all along|suddenly|actually|after all|"
    r"until|not .{1,50} but|yet)\b",
    re.IGNORECASE,
)
_REASSURANCE_CUES = re.compile(
    r"\b(?:perfectly safe|nothing could go wrong|exactly as planned|"
    r"completely harmless|trust me|all under control|couldn['’]t fail)\b",
    re.IGNORECASE,
)
_CONTRAST_CUES = re.compile(r"\b(?:but|yet|however|although|though|instead)\b", re.IGNORECASE)
_AND_CUES = re.compile(r"\b(?:and then|and|then)\b", re.IGNORECASE)
_LEXICAL_SEEDS = {
    "promise": {"promise", "vow", "pledge"},
    "positive": {"success", "win", "rescue", "discovery", "answer"},
    "negative": {"failure", "loss", "death", "rejection", "betrayal", "injury"},
    "resolution": {"resolve", "answer", "discovery", "revelation", "decision"},
    "loss": {"death", "grief", "mourning", "bereavement"},
    "care": {"care", "love", "trust", "protection", "comfort", "loyalty"},
    "vulnerability": {"fear", "loneliness", "shame", "terror", "crying", "confession"},
}


@lru_cache(maxsize=16)
def _cached_reader_cues(
    lexicon_path: str, modification_time: int, file_size: int
) -> dict[str, re.Pattern]:
    del modification_time, file_size
    fallbacks = {
        "promise": _PROMISE_CUES,
        "positive": _POSITIVE_CUES,
        "negative": _NEGATIVE_CUES,
        "resolution": _RESOLUTION_CUES,
        "loss": _LOSS_CUES,
        "care": _CARE_CUES,
        "vulnerability": _VULNERABILITY_CUES,
    }
    cues = {}
    for category, seeds in _LEXICAL_SEEDS.items():
        terms = expand_lexical_terms(seeds, lexicon_path)
        lexical_pattern = (
            r"\b(?:" + "|".join(re.escape(term) for term in sorted(terms)) + r")\b"
            if terms else r"(?!)"
        )
        cues[category] = re.compile(
            f"(?:{fallbacks[category].pattern})|(?:{lexical_pattern})",
            re.IGNORECASE,
        )
    cues["reversal"] = _REVERSAL_CUES
    cues["reassurance"] = _REASSURANCE_CUES
    return cues


def _reader_cues(lexicon_path: str | Path | None = None) -> dict[str, re.Pattern]:
    target = Path(lexicon_path) if lexicon_path else WIKTIONARY_DB_PATH
    if target.is_file():
        stat = target.stat()
        return _cached_reader_cues(str(target), stat.st_mtime_ns, stat.st_size)
    return _cached_reader_cues(str(target), 0, 0)


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", html_to_text(text)) if part.strip()]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _key_terms(text: str) -> set[str]:
    return {
        token.lower().strip("'’")
        for token in re.findall(r"[A-Za-z][A-Za-z'’_-]{2,}", text)
        if token.lower().strip("'’") not in _STOP_WORDS
    }


def _named_terms(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\b[A-Z][a-z]{2,}\b", text)
        if token.lower() not in {"the", "then", "this", "that", "when", "what"}
    }


_IDIOMS = re.compile(
    r"\b(?:dead (?:center|centre|sprint|silent|still|end|air|weight|quiet|ahead|"
    r"asleep|tired|serious|calm|on)|stopped dead|stopped short|"
    r"(?:held|hold|holding) (?:together|on|tight|steady|up|back|still|out)|"
    r"(?:dead|stopped) in (?:his|her|their|my) tracks|wrong (?:way|turn|side|door)|"
    r"dead (?:rodents?|leaves|wood|weeds?))\b",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    return _IDIOMS.sub(" ", text)


def _search(pattern: re.Pattern, text: str):
    return pattern.search(_clean(text))


def _in_dialogue(sentence: str) -> bool:
    return any(mark in sentence for mark in '"“”')


_KIN = {
    "father", "mother", "brother", "sister", "son", "daughter", "wife", "husband",
    "mentor", "friend", "dad", "mom", "grandmother", "grandfather", "uncle", "aunt",
}


_GENERIC = {
    "his", "her", "him", "she", "its", "our", "who", "how", "why", "all", "one",
    "was", "had", "for", "and", "but", "not", "the", "you", "own", "way", "day",
    "night", "time", "life", "eyes", "hand", "hands", "heart", "back", "like",
}


def _anchors(text: str) -> set[str]:
    terms = {re.sub(r"['’]s$", "", term) for term in _key_terms(text)}
    return {term for term in terms if len(term) > 2 and term not in _GENERIC}


def _windows(text: str):
    """Yield (sentence, sentence plus its predecessor), newest first, so a pronoun
    subject can lean on the sentence that names who it is."""
    sentences = _sentences(text)
    for index in range(len(sentences) - 1, -1, -1):
        previous = sentences[index - 1] if index else ""
        yield sentences[index], f"{previous} {sentences[index]}"


def _first_matching_sentence(text: str, pattern: re.Pattern) -> str:
    return next(
        (sentence for sentence in _sentences(text) if _search(pattern, sentence)),
        "",
    )


def _last_matching_sentence(text: str, pattern: re.Pattern) -> str:
    return next(
        (sentence for sentence in reversed(_sentences(text)) if _search(pattern, sentence)),
        "",
    )


def _scene_text(scene: dict) -> str:
    return html_to_text(scene.get("content") or "").strip()


def _state(text: str, cues: dict[str, re.Pattern]) -> str | None:
    positive = bool(_search(cues["positive"], text))
    negative = bool(_search(cues["negative"], text))
    if positive == negative:
        return None
    return "yes" if positive else "no"


def _turns(
    paragraphs: list[str], cues: dict[str, re.Pattern] | None = None
) -> list[dict]:
    cues = cues or _reader_cues()
    turns = []
    for index, paragraph in enumerate(paragraphs, 1):
        contrast = _CONTRAST_CUES.search(paragraph)
        kind = None
        if contrast:
            first_state = _state(paragraph[:contrast.start()], cues)
            second_state = _state(paragraph[contrast.end():], cues)
            if first_state == "yes" and second_state == "no":
                kind = "yes_but"
            elif first_state == "no" and second_state == "yes":
                kind = "no_but"
        else:
            for connector in _AND_CUES.finditer(paragraph):
                first_state = _state(paragraph[:connector.start()], cues)
                second_state = _state(paragraph[connector.end():], cues)
                if first_state == second_state == "yes":
                    kind = "yes_and"
                    break
                if first_state == second_state == "no":
                    kind = "no_and"
                    break
        copy = {
            "yes_but": ("The win comes with a sting", "That 'but' turns the success into a costly, uneasy win."),
            "no_but": ("The setback opens a door", "The refusal or failure gives the reader a new reason to hope."),
            "yes_and": ("One win builds into another", "The first success carries us straight into a second possibility."),
            "no_and": ("The trouble keeps piling up", "The next setback compounds the first, so the pressure keeps climbing."),
        }
        if not kind:
            continue
        headline, reaction = copy[kind]
        turns.append({
            "kind": kind,
            "headline": headline,
            "reaction": reaction,
            "paragraph": index,
            "evidence": paragraph[:700],
            "confidence": "Strong textual turn",
        })
    return turns


def _promise_candidates(scenes: list[dict], cues: dict[str, re.Pattern]) -> list[dict]:
    candidates = []
    for scene_index, scene in enumerate(scenes):
        for paragraph_index, paragraph in enumerate(_paragraphs(_scene_text(scene)), 1):
            for sentence in _sentences(paragraph):
                is_question = (
                    "?" in sentence and not _in_dialogue(sentence)
                    and len(sentence.split()) >= 6
                )
                is_promise = bool(_search(cues["promise"], sentence))
                if not (is_question or is_promise):
                    continue
                terms = _key_terms(sentence)
                if not terms:
                    continue
                candidates.append({
                    "scene_id": scene["scene_id"],
                    "scene_title": scene["title"],
                    "scene_index": scene_index,
                    "paragraph": paragraph_index,
                    "evidence": sentence[:400],
                    "terms": terms,
                    "kind": "question" if is_question else "commitment",
                })
    return candidates


def _find_reader_threads(
    scenes: list[dict], selected_index: int, current_text: str, cues: dict[str, re.Pattern]
) -> list[dict]:
    reading_scenes = [
        *scenes[:selected_index],
        {**scenes[selected_index], "content": current_text},
    ]
    candidates = _promise_candidates(reading_scenes, cues)
    for candidate in candidates:
        rest = current_text.replace(candidate["evidence"], " ")
        rest_words = re.findall(r"[a-z][a-z'’-]{2,}", rest.lower())
        candidate["recurrence"] = sum(
            1 for term in candidate["terms"] if 1 <= rest_words.count(term) <= 8
        )
        if candidate["kind"] == "commitment":
            candidate["recurrence"] += 2
    current_paragraphs = _paragraphs(current_text)
    events = []
    for promise in candidates:
        same_scene = promise["scene_index"] == selected_index
        if same_scene:
            events.append({
                "kind": "setup",
                "headline": "You’ve given the reader something to carry forward",
                "reaction": (
                    "This question stays alive on the page; readers will keep looking "
                    "for the answer."
                    if promise["kind"] == "question"
                    else "That promise gives readers a clear reason to watch what happens next."
                ),
                "setup_title": "",
                "setup_evidence": "",
                "payoff_evidence": promise["evidence"],
                "setup_scene_id": reading_scenes[selected_index]["scene_id"],
                "payoff_scene_id": reading_scenes[selected_index]["scene_id"],
                "confidence": "Clear setup",
                "paragraph": promise["paragraph"],
                "recurrence": promise["recurrence"],
            })
            continue

        overlap = promise["terms"] & _key_terms(current_text)
        if not overlap:
            continue
        matching_paragraph = next(
            (
                paragraph for paragraph in current_paragraphs
                if len(promise["terms"] & _key_terms(paragraph)) >= min(2, len(promise["terms"]))
                or (
                    len(promise["terms"]) == 1
                    and bool(promise["terms"] & _key_terms(paragraph))
                    and bool(cues["resolution"].search(paragraph))
                )
            ),
            "",
        )
        if not matching_paragraph:
            continue
        is_payoff = bool(cues["resolution"].search(matching_paragraph))
        is_surprise = (
            bool(cues["reversal"].search(matching_paragraph))
            and bool(cues["negative"].search(matching_paragraph))
        )
        event_kind = "surprise" if is_surprise else "payoff" if is_payoff else "return"
        events.append({
            "kind": event_kind,
            "headline": (
                "The answer takes a sharp turn" if is_surprise
                else "A promise finds its payoff" if is_payoff
                else "An earlier question comes back"
            ),
            "reaction": (
                "We were watching for the earlier promise to come true; this turn changes what that promise means. The setup gives the surprise something solid to overturn."
                if is_surprise
                else "This feels like an answer the story has been earning. The earlier setup gives this moment its satisfying click."
                if is_payoff
                else "We remember the earlier setup, and this return makes the question feel live again."
            ),
            "setup_title": promise["scene_title"],
            "setup_evidence": promise["evidence"],
            "payoff_evidence": matching_paragraph[:700],
            "setup_scene_id": promise["scene_id"],
            "payoff_scene_id": scenes[selected_index]["scene_id"],
            "confidence": (
                "Two or more story details connect setup to payoff"
                if len(overlap) >= 2
                else "Shared story term plus a resolution cue"
            ),
            "paragraph": next(
                (index for index, paragraph in enumerate(current_paragraphs, 1) if paragraph == matching_paragraph),
                None,
            ),
        })
    setups = [event for event in events if event["kind"] == "setup"]
    others = [event for event in events if event["kind"] != "setup"]
    setups = sorted(setups, key=lambda event: -event.pop("recurrence"))[:3]
    setups.sort(key=lambda event: event["paragraph"])
    return (others + setups)[-8:]


def _loss_and_care(
    scenes: list[dict], selected_index: int, current_text: str, cues: dict[str, re.Pattern]
) -> list[dict]:
    insights = []
    for index, paragraph in enumerate(_paragraphs(current_text), 1):
        loss_evidence = _first_matching_sentence(paragraph, cues["loss"])
        prior_text = "\n\n".join(
            _scene_text(scene) for scene in scenes[:selected_index]
        ) + "\n\n" + "\n\n".join(_paragraphs(current_text)[:index - 1])
        loss_match = cues["loss"].search(paragraph)
        if loss_match:
            prior_text += "\n\n" + paragraph[:loss_match.start()]
        loss_anchors = _anchors(loss_evidence)
        care_evidence = next(
            (
                sentence for sentence, window in _windows(prior_text)
                if _search(cues["care"], sentence) and loss_anchors & _anchors(window)
            ),
            "",
        )
        if loss_evidence and care_evidence:
            care_scene = next(
                (
                    scene for scene in reversed(scenes[:selected_index])
                    if care_evidence in _scene_text(scene)
                ),
                None,
            )
            if care_scene is None:
                care_scene = scenes[selected_index]
            insights.append({
                "kind": "loss",
                "headline": "This one is going to hurt",
                "reaction": (
                    f"We’ve already seen the bond in “{care_evidence[:220]}”. "
                    f"Now “{loss_evidence[:220]}” takes that familiar comfort away. "
                    "That loss will land as grief: the story gave us "
                    "someone to miss before it took them away."
                ),
                "setup_evidence": care_evidence,
                "payoff_evidence": loss_evidence[:700],
                "setup_title": care_scene["title"],
                "setup_scene_id": care_scene["scene_id"],
                "payoff_scene_id": scenes[selected_index]["scene_id"],
                "confidence": "Strong emotional setup",
                "paragraph": index,
            })
    return insights


def _empathy_moments(
    scenes: list[dict], selected_index: int, current_text: str, cues: dict[str, re.Pattern]
) -> list[dict]:
    insights = []
    paragraphs = _paragraphs(current_text)
    for index, paragraph in enumerate(paragraphs, 1):
        vulnerability_evidence = _first_matching_sentence(paragraph, cues["vulnerability"])
        prior_text = "\n\n".join(
            _scene_text(scene) for scene in scenes[:selected_index]
        ) + "\n\n" + "\n\n".join(paragraphs[:index - 1])
        vulnerability_match = cues["vulnerability"].search(paragraph)
        if vulnerability_match:
            prior_text += "\n\n" + paragraph[:vulnerability_match.start()]
        vulnerability_anchors = _anchors(vulnerability_evidence)
        care_evidence = next(
            (
                sentence for sentence, window in _windows(prior_text)
                if _search(cues["care"], sentence) and vulnerability_anchors & _anchors(window)
            ),
            "",
        )
        if vulnerability_evidence and care_evidence:
            care_scene = next(
                (
                    scene for scene in reversed(scenes[:selected_index])
                    if care_evidence in _scene_text(scene)
                ),
                None,
            )
            if care_scene is None:
                care_scene = scenes[selected_index]
            insights.append({
                "kind": "empathy",
                "headline": "This is where we get closer to them",
                "reaction": (
                    f"We’ve seen the care in “{care_evidence[:180]}”. Now this character’s "
                    f"guard drops in “{vulnerability_evidence[:220]}”. That contrast gives readers "
                    "something personal to hold onto."
                ),
                "setup_evidence": care_evidence,
                "payoff_evidence": vulnerability_evidence[:700],
                "setup_title": care_scene["title"],
                "setup_scene_id": care_scene["scene_id"],
                "payoff_scene_id": scenes[selected_index]["scene_id"],
                "confidence": "Care and vulnerability build across scenes",
                "paragraph": index,
            })
    return insights


def _subtext_moments(current_text: str) -> list[dict]:
    insights = []
    evasion = re.compile(
        r"\b(?:didn['’]t answer|did not answer|said nothing|looked away|"
        r"changed the subject|ignored (?:the question|her question|his question))\b",
        re.IGNORECASE,
    )
    for index, paragraph in enumerate(_paragraphs(current_text), 1):
        if "?" in paragraph and evasion.search(paragraph):
            insights.append({
                "kind": "subtext",
                "headline": "The silence answers more than the words do",
                "reaction": (
                    "The reader hears the question, then sees it dodged. That gap makes "
                    "the unspoken answer feel important—and gives us a reason to watch "
                    "what this character is protecting."
                ),
                "setup_evidence": "",
                "payoff_evidence": paragraph[:700],
                "setup_scene_id": "",
                "payoff_scene_id": "",
                "setup_title": "",
                "confidence": "Question followed by a clear evasion",
                "paragraph": index,
            })
    return insights


def _irony_moments(current_text: str, cues: dict[str, re.Pattern]) -> list[dict]:
    insights = []
    for index, paragraph in enumerate(_paragraphs(current_text), 1):
        reassurance = cues["reassurance"].search(paragraph)
        consequence = (
            next(
                (match for match in cues["negative"].finditer(paragraph)
                 if match.start() > reassurance.end()),
                None,
            )
            if reassurance else None
        )
        if reassurance and consequence:
            reassurance_text = reassurance.group(0)
            consequence_text = paragraph[consequence.start():].strip()
            insights.append({
                "kind": "irony",
                "headline": "The reassurance makes the trouble funnier—or sharper",
                "reaction": (
                    f"We hear “{reassurance_text}” and then watch “{consequence_text[:180]}” "
                    "prove the opposite. That gap lets the reader see the trouble coming "
                    "before the character catches up."
                ),
                "setup_evidence": reassurance_text,
                "payoff_evidence": consequence_text[:700],
                "setup_title": "",
                "setup_scene_id": "",
                "payoff_scene_id": "",
                "confidence": "Reassurance directly contradicted by the outcome",
                "paragraph": index,
            })
    return insights


def _trust_shifts(
    scenes: list[dict], selected_index: int, current_text: str, cues: dict[str, re.Pattern]
) -> list[dict]:
    promises = [
        (scene["scene_id"], sentence)
        for scene in scenes[:selected_index]
        for paragraph in _paragraphs(_scene_text(scene))
        for sentence in _sentences(paragraph)
        if cues["promise"].search(sentence)
    ]
    if not promises:
        return []
    for index, paragraph in enumerate(_paragraphs(current_text), 1):
        broken_promise = re.search(
            r"\b(?:lied|betrayed|broke (?:his|her|their) promise|went back on)\b",
            paragraph,
            re.I,
        )
        if broken_promise and (_key_terms(promises[-1][1]) & _key_terms(paragraph)):
            broken_action = paragraph[broken_promise.start():].strip()
            promise_scene_id, promise_text = promises[-1]
            return [{
                "kind": "trust_shift",
                "headline": "The reader’s trust takes a hit",
                "reaction": (
                    f"Earlier, we heard “{promise_text[:180]}”. Now “{broken_action[:220]}” "
                    "shows that promise breaking. That gap between word and action changes how we read this character."
                ),
                "setup_evidence": promise_text[:400],
                "payoff_evidence": broken_action[:700],
                "setup_title": next(
                    scene["title"] for scene in scenes if scene["scene_id"] == promise_scene_id
                ),
                "setup_scene_id": promise_scene_id,
                "payoff_scene_id": scenes[selected_index]["scene_id"],
                "confidence": "Direct promise-and-action contrast",
                "paragraph": index,
            }]
    return []


def analyze_reader_story(
    scenes: list[dict],
    selected_scene_id: str,
    current_content: str,
    lexicon_path: str | Path | None = None,
) -> dict:
    selected_index = next(
        (index for index, scene in enumerate(scenes) if scene["scene_id"] == selected_scene_id),
        None,
    )
    if selected_index is None:
        return {
            "scene_id": selected_scene_id,
            "turns": [],
            "threads": [],
            "emotional_payoffs": [],
            "trust_shifts": [],
            "summary": "This scene is not in the manuscript’s active reading order.",
        }

    text = html_to_text(current_content or "")
    paragraphs = _paragraphs(text)
    cues = _reader_cues(lexicon_path)
    lexicon = get_lexicon_status(lexicon_path)
    threads = _find_reader_threads(scenes, selected_index, text, cues)
    turns = _turns(paragraphs, cues)
    emotional_payoffs = _loss_and_care(scenes, selected_index, text, cues)
    empathy_moments = _empathy_moments(scenes, selected_index, text, cues)
    subtext_moments = _subtext_moments(text)
    irony_moments = _irony_moments(text, cues)
    trust_shifts = _trust_shifts(scenes, selected_index, text, cues)
    experience_moments = analyze_reader_feel(current_content)
    for moment in experience_moments:
        moment["setup_scene_id"] = selected_scene_id
        moment["payoff_scene_id"] = selected_scene_id
    insights = (
        len(experience_moments) + len(threads) + len(turns) + len(emotional_payoffs)
        + len(empathy_moments) + len(subtext_moments)
        + len(irony_moments) + len(trust_shifts)
    )
    summary = (
        "There’s a story turn here worth noticing."
        if insights
        else "No clear promise, payoff, or story turn surfaced here yet."
    )
    return {
        "scene_id": selected_scene_id,
        "scene_index": selected_index,
        "summary": summary,
        "experience_moments": experience_moments,
        "threads": threads,
        "turns": turns,
        "emotional_payoffs": emotional_payoffs,
        "empathy_moments": empathy_moments,
        "subtext_moments": subtext_moments,
        "irony_moments": irony_moments,
        "trust_shifts": trust_shifts,
        "disclaimer": (
            "These are confident predictions of a typical reader’s experience, "
            "grounded in the manuscript—not a guarantee that every reader will react the same way."
        ),
        "method": (
            "Transparent text-pattern rules expanded with local English Wiktionary word forms and synonyms; no generative AI is used."
            if lexicon["available"]
            else "Transparent text-pattern rules; no generative AI is used. A local Wiktionary index can expand word forms and synonyms."
        ),
        "lexicon": {
            "available": lexicon["available"],
            "source": lexicon.get("source"),
            "license": lexicon.get("license"),
            "attribution": lexicon.get("attribution"),
        },
    }
