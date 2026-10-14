import re

from backend.reader_cues import _key_terms, _paragraphs, _sentences
from backend.reader_text import _anchors, _first_matching_sentence, _scene_text, _search, _windows

def _loss_and_care(
    scenes: list[dict], selected_index: int, current_text: str, cues: dict[str, re.Pattern]
) -> list[dict]:
    insights = []
    for index, paragraph in enumerate(_paragraphs(current_text), 1):
        loss_evidence = _first_matching_sentence(paragraph, cues["loss"])
        if not loss_evidence:
            continue
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
        if not vulnerability_evidence:
            continue
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


