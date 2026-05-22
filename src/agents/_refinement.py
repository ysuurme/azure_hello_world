from __future__ import annotations

import json
from dataclasses import dataclass, field

_GRILL_SYSTEM_PROMPT = (
    "You are a diagram requirements analyst using the grill-me refinement pattern.\n\n"
    "Given a diagram description and a partial DiagramBrief, do two things:\n"
    "1. Extract as much structured information as possible from the description.\n"
    "2. Identify remaining gaps and emit clarifying questions — each with a recommended answer.\n\n"
    "A brief is COMPLETE when ALL of the following are satisfied:\n"
    "- subject: a clear, concise name for the diagram (not empty)\n"
    "- components: at least 2 named components, each with a shape\n"
    "- relationships: at least 1 relationship between components\n"
    "- layout_direction: one of right, down, left, up\n\n"
    "Output ONLY this JSON object — no prose, no markdown wrapper:\n"
    "{\n"
    '  "updated_brief": {\n'
    '    "subject": "<string>",\n'
    '    "components": [{"name": "<str>", "shape": "<str>", "group": "<str or null>"}],\n'
    '    "relationships": [{"from_component": "<str>", "to_component": "<str>", "label": "<str or null>"}],\n'
    '    "layout_direction": "<right|down|left|up>",\n'
    '    "complete": <true|false>\n'
    "  },\n"
    '  "questions": [\n'
    '    {"question": "<str>", "recommendation": "<str>"}\n'
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- If complete is true, questions must be an empty array [].\n"
    "- Every question must include a non-empty recommendation string.\n"
    "- Ask only about genuine gaps — if the description is fully specified, mark complete=true.\n"
    "- Default layout_direction to right when not specified.\n"
    "- Default shape to rectangle when not specified."
)


@dataclass
class GrillQuestion:
    question: str
    recommendation: str


@dataclass
class GrillRound:
    questions: list[GrillQuestion] = field(default_factory=list)
    updated_brief: dict = field(default_factory=dict)
    complete: bool = False


def _parse_grill_response(raw: str) -> GrillRound:
    try:
        start = raw.index("{")
        data, _ = json.JSONDecoder().raw_decode(raw, start)
    except (ValueError, json.JSONDecodeError):
        return GrillRound()

    brief = data.get("updated_brief", {})
    questions = [
        GrillQuestion(question=q["question"], recommendation=q["recommendation"])
        for q in data.get("questions", [])
        if "question" in q and "recommendation" in q
    ]
    return GrillRound(
        questions=questions,
        updated_brief=brief,
        complete=bool(brief.get("complete", False)),
    )


class RefinementMixin:
    """Thin mixin encoding the grill pattern: read known → identify gaps → emit questions."""

    brief_class = None  # schema slot — override in subclass with the module's Brief dataclass

    def grill_round(self, description: str, partial_brief: dict) -> GrillRound:
        prompt = (
            _GRILL_SYSTEM_PROMPT
            + f"\n\nDescription: {description}"
            + f"\n\nCurrent partial brief: {json.dumps(partial_brief, default=str)}"
        )
        raw = self._run_grill_llm(prompt)
        return _parse_grill_response(raw)

    def _run_grill_llm(self, prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError
