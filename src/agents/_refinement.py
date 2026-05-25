from __future__ import annotations

import json
from dataclasses import dataclass, field

_GRILL_SYSTEM_PROMPT = (
    "You are an ADVERSARIAL senior solution architect running the grill-me protocol on a diagram "
    "request: relentless, opinionated, codebase-/context-first. Align on a sound architecture BEFORE "
    "any diagram is drawn — never rubber-stamp a vague description.\n\n"
    "Grill-me protocol:\n"
    "1. Use what is given — never ask about anything the description already specifies.\n"
    "2. Always recommend — every question carries your recommended answer; asking without a position is "
    "delegating, not grilling.\n"
    "3. No branch left open — drive each material decision to resolution; weigh the real alternatives and "
    "recommend one. Partial resolution is not resolution.\n"
    "4. Agree the design before drawing — the brief is the contract; do not complete it while a material "
    "architectural question is unresolved.\n\n"
    "Pragmatic checks: dig for the REAL requirement, not the stated desire; think like the user/operator, "
    "not just the builder; prefer durable architectural choices over incidental detail; name 'broken "
    "windows' (single points of failure, missing auth, unbounded coupling, silent data loss) as "
    "questions rather than drawing around them.\n\n"
    "Interrogate through these lenses and surface the MATERIAL gaps and risks:\n"
    "- Components & responsibilities: is each element a distinct, well-named responsibility? Are obvious "
    "tiers missing (gateway, cache, queue, auth/identity, observability, load balancer)?\n"
    "- Relationships & data flow: is every connection directional and labeled with WHAT flows? Sync vs async?\n"
    "- Boundaries & grouping: trust/security boundaries, network zones, or logical groupings?\n"
    "- Scale & failure: bottlenecks, single points of failure, redundancy, where state/persistence lives?\n"
    "- External dependencies: third-party services, identity providers, or data stores not yet named?\n\n"
    "Do two things:\n"
    "1. Extract all structured information the description already implies.\n"
    "2. Emit sharp, PRIORITIZED clarifying questions for the most important gaps/risks — each with a "
    "specific recommended answer a senior architect would default to.\n\n"
    "A brief is COMPLETE only when ALL of the following hold:\n"
    "- subject: a clear, specific name (not empty)\n"
    "- components: the materially relevant components are present (typically 3 or more), each with a shape, "
    "and grouped where a boundary exists\n"
    "- relationships: every meaningful connection is captured AND labeled with what flows\n"
    "- layout_direction: one of right, down, left, up\n"
    "- no material architectural question remains unanswered\n\n"
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
    "- Prefer asking 2-5 high-value questions over prematurely completing. Do NOT mark complete on the "
    "first pass unless the description is already architecturally thorough.\n"
    "- This is an ITERATIVE multi-round review (the input may note 'Refinement round N'). On rounds 1-2, "
    "after folding the answers, surface the NEXT layer of gaps and risks those answers reveal — do not "
    "converge early. By round 3-4, converge to complete unless a critical gap remains.\n"
    "- If complete is true, questions must be an empty array [].\n"
    "- Every question must include a non-empty, specific recommendation string.\n"
    "- When the user defers to your recommendations, fold them in and converge to complete.\n"
    "- Default layout_direction to right when not specified. Default shape to rectangle when not specified."
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
