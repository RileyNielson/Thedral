from collections import Counter
import re

from backend.reader_cues import _AND_CUES, _CONTRAST_CUES, _key_terms, _paragraphs, _reader_cues, _sentences
from backend.reader_text import _in_dialogue, _scene_text, _search, _state

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
    word_pattern = re.compile(r"[a-z][a-z'’-]{2,}")
    lowered_text = current_text.lower()
    total_counts = Counter(word_pattern.findall(lowered_text))
    evidence_cache: dict[str, tuple[int, Counter]] = {}
    for candidate in candidates:
        evidence = candidate["evidence"]
        if evidence not in evidence_cache:
            evidence_cache[evidence] = (
                lowered_text.count(evidence.lower()),
                Counter(word_pattern.findall(evidence.lower())),
            )
        occurrences, evidence_counts = evidence_cache[evidence]
        candidate["recurrence"] = sum(
            1 for term in candidate["terms"]
            if 1 <= total_counts[term] - occurrences * evidence_counts[term] <= 8
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


