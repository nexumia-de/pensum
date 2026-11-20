"""The user's own journeys (#80): `journey:<id>` records as QuestArc's
engine keeps them (QuestArc docs/data-model.md), the quick form's
journey and its proposed steps. Everything is the engine's: what the
form writes, the journey checker and the record; nothing is decided
here. No GTK."""
import json
from functools import lru_cache

from pensum.game import content

KEY = "journey:"
MEASURES = ("minutes", "pages", "times", "same")
LIMITS = {"name": 40, "action": 80, "anchor": 40}
MAX_STEPS = 6


def journeys(found):
    """The journeys among loaded records (pensum.game.records.load)."""
    return [value for key, value in sorted(found.items())
            if key.startswith(KEY) and isinstance(value, dict)]


@lru_cache(maxsize=1)
def available():
    """Whether the installed engine has the quick form and keeps journey
    files. QuestArc 4.3.1, the release pinned now, answers "unknown
    request"; the form and import stay hidden until a release has them."""
    from pensum.game import engine
    try:
        answer = engine.run({"quickSteps": {"first": 1, "last": 2}})
    except (engine.EngineError, ValueError):
        return False
    return isinstance(answer, list)


def is_own(journey_id):
    return any(j.get("id") == journey_id for j in content.own())


def propose(first, last):
    """The steps the engine suggests between two amounts."""
    from pensum.game import engine
    answer = engine.run({"quickSteps": {"first": first, "last": last}})
    return [n for n in answer if isinstance(n, int)] if isinstance(answer, list) else []


def quick(answers):
    """{journey, problems, hints} for the form's answers. The language
    is the one QuestArc's texts are shown in, so the built sentences and
    the user's words match."""
    from pensum.game import engine
    texts = content.ui_texts()
    answer = engine.run({"quick": {
        "answers": {**answers, "language": content.language(),
                    "taken": [j.get("id") for j in content.journeys()]},
        "texts": {k: v for k, v in texts.items() if k.startswith("ui.quick.")}}})
    if not isinstance(answer, dict) or "journey" not in answer:
        raise engine.EngineError("this QuestArc engine has no quick journey")
    return answer


def keep(journey):
    """(record changes, problems) for a journey file, after the engine's
    journey checker; no changes when it has an error."""
    from pensum.game import engine
    answer = engine.run({"keepJourney": {"journey": journey,
                                         "builtIn": [j.get("id") for j in content.builtin()]}})
    if not isinstance(answer, dict) or "changes" not in answer:
        raise engine.EngineError("this QuestArc engine keeps no journeys")
    return answer["changes"], answer.get("problems") or []


def errors(problems):
    return [p for p in problems if isinstance(p, dict) and p.get("level") == "error"]


def read_file(text):
    """A journey file's content, or None when it is not a JSON object."""
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def file_text(journey):
    return json.dumps(journey, ensure_ascii=False, indent=2) + "\n"


def plan_sentences(journey):
    """Every step of a journey that is not kept yet as its plan sentence,
    from the journey's own texts."""
    blocks = journey.get("texts") or {}
    texts = {**(blocks.get("en") or {}), **(blocks.get(content.language()) or {})}
    return [content.t("ui.plan.sentence", anchor=texts.get(stage["plan"]["anchor"], ""),
                      action=texts.get(stage["plan"]["action"] + ".plan")
                      or texts.get(stage["plan"]["action"], ""))
            for stage in journey.get("stages", ())]
