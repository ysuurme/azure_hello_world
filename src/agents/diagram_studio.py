from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from src.agents._refinement import RefinementMixin
from src.config import AGENT_MODELS
from src.utils.m_diagram_engine import DiagramEngine
from src.utils.m_log import f_log
from src.utils.m_persist_design import ArchitecturePersister, _brief_to_markdown

_D2_SYSTEM_PROMPT = (
    "You are a D2 diagram code generator. "
    "Convert the DiagramBrief JSON into valid D2 syntax. "
    "Use shapes, connections, and labels to represent the components and relationships accurately. "
    "Apply the layout_direction from the brief. "
    "Return ONLY a single ```d2 ... ``` code block — no prose before or after."
)

_D2_PATTERN = re.compile(r"```d2\n(.*?)```", re.DOTALL)

_APPROVAL_PHRASES = frozenset({"yes", "approved", "looks good", "lgtm", "ship it"})


@dataclass
class ComponentSpec:
    name: str
    shape: str = "rectangle"
    group: str | None = None


@dataclass
class RelationshipSpec:
    from_component: str
    to_component: str
    label: str | None = None


@dataclass
class DiagramStyle:
    sketch: bool = True


@dataclass
class DiagramBrief:
    subject: str = ""
    components: list[ComponentSpec] = field(default_factory=list)
    relationships: list[RelationshipSpec] = field(default_factory=list)
    layout_direction: str = "right"
    style: DiagramStyle = field(default_factory=DiagramStyle)


@dataclass
class ModuleResponse:
    response_text: str
    updated_state: dict
    artifacts: dict = field(default_factory=dict)
    status: str = "completed"


def _format_grill_questions(questions: list) -> str:
    if not questions:
        return "I need a few more details about the diagram."
    lines = ["I need a few more details to create your diagram:\n"]
    for i, q in enumerate(questions, 1):
        lines.append(f"**Q{i}:** {q.question}")
        lines.append(f"**Recommended:** {q.recommendation}\n")
    return "\n".join(lines)


def _is_approved(user_input: str) -> bool:
    return user_input.strip().lower() in _APPROVAL_PHRASES


def _derive_diagram_name(brief: dict) -> str:
    subject = brief.get("subject", "").strip()
    if not subject:
        return f"diagram_{int(time.time())}"
    safe = re.sub(r"[^a-zA-Z0-9 ]", "", subject).strip()
    name = safe[:30].replace(" ", "_")
    return name if name else f"diagram_{int(time.time())}"


def _brief_dict_to_dataclass(brief: dict) -> DiagramBrief:
    components = [
        ComponentSpec(
            name=c.get("name", ""),
            shape=c.get("shape", "rectangle"),
            group=c.get("group"),
        )
        for c in brief.get("components", [])
    ]
    relationships = [
        RelationshipSpec(
            from_component=r.get("from_component", ""),
            to_component=r.get("to_component", ""),
            label=r.get("label"),
        )
        for r in brief.get("relationships", [])
    ]
    return DiagramBrief(
        subject=brief.get("subject", ""),
        components=components,
        relationships=relationships,
        layout_direction=brief.get("layout_direction", "right"),
    )


class DiagramStudioModule(RefinementMixin):
    """Diagram capability module: grill loop → DiagramBrief → approval gate → D2 → sketch-rendered SVG."""

    name = "Diagram Studio"
    slash_command = "/diagram"
    description = "Generate a sketch-style architecture diagram from a free-text description."
    brief_class = DiagramBrief

    def __init__(self, client_manager) -> None:
        self._client_manager = client_manager

    def handle(self, user_input: str, module_state: dict) -> ModuleResponse:
        phase = module_state.get("phase")
        if phase == "grilling":
            return self._grill_turn(user_input, module_state)
        if phase == "awaiting_approval":
            return self._approval_turn(user_input, module_state)
        return self._first_turn(user_input, module_state)

    def _first_turn(self, user_input: str, module_state: dict) -> ModuleResponse:
        parts = user_input.split(maxsplit=1)
        description = parts[1] if len(parts) > 1 else user_input
        f_log("DiagramStudioModule: starting grill round.", level="process")
        grill = self.grill_round(description, {})
        new_state = {"phase": "grilling", "description": description, "brief": grill.updated_brief}
        if grill.complete:
            return self._present_for_approval(grill.updated_brief, new_state)
        return ModuleResponse(
            response_text=_format_grill_questions(grill.questions),
            updated_state=new_state,
            status="in_refinement",
        )

    def _grill_turn(self, user_input: str, module_state: dict) -> ModuleResponse:
        description = module_state.get("description", "")
        current_brief = module_state.get("brief", {})
        context = f"{description}\n\nUser answers to previous questions: {user_input}"
        f_log("DiagramStudioModule: folding grill answers.", level="process")
        grill = self.grill_round(context, current_brief)
        new_state = {**module_state, "brief": grill.updated_brief}
        if grill.complete:
            return self._present_for_approval(grill.updated_brief, new_state)
        return ModuleResponse(
            response_text=_format_grill_questions(grill.questions),
            updated_state={**new_state, "phase": "grilling"},
            status="in_refinement",
        )

    def _present_for_approval(self, brief: dict, module_state: dict) -> ModuleResponse:
        brief_obj = _brief_dict_to_dataclass(brief)
        md = _brief_to_markdown(brief_obj)
        response = (
            "I've built up the following diagram brief:\n\n"
            + md
            + "\n\nReply `yes`, `approved`, `lgtm`, `looks good`, or `ship it` to generate the diagram, "
            "or describe any changes."
        )
        return ModuleResponse(
            response_text=response,
            updated_state={**module_state, "phase": "awaiting_approval", "brief": brief},
            status="awaiting_approval",
        )

    def _approval_turn(self, user_input: str, module_state: dict) -> ModuleResponse:
        if _is_approved(user_input):
            brief = module_state.get("brief", {})
            return self._generate_diagram(brief, module_state)
        return self._grill_turn(user_input, {**module_state, "phase": "grilling"})

    def _generate_diagram(self, brief: dict, module_state: dict) -> ModuleResponse:
        f_log("DiagramStudioModule: generating D2 from approved brief.", level="process")
        d2_code = self._generate_d2_from_brief(brief)
        if not d2_code:
            return ModuleResponse(
                response_text="Could not generate D2 code from the brief. Please try again.",
                updated_state=module_state,
                status="error",
            )
        svg_bytes = DiagramEngine().generate_svg(d2_code, sketch=True)
        artifacts: dict = {"d2": d2_code, "brief": brief}
        if svg_bytes:
            artifacts["svg"] = svg_bytes
        brief_obj = _brief_dict_to_dataclass(brief)
        name = _derive_diagram_name(brief)
        persisted_path = ArchitecturePersister().persist_diagram(name, brief_obj, d2_code, svg_bytes or b"")
        artifacts["persisted_path"] = str(persisted_path)
        return ModuleResponse(
            response_text=f"Here is the generated diagram:\n\n```d2\n{d2_code}\n```",
            updated_state={**module_state, "phase": "completed"},
            artifacts=artifacts,
            status="completed",
        )

    def _generate_d2_from_brief(self, brief: dict) -> str | None:
        prompt = f"{_D2_SYSTEM_PROMPT}\n\nBrief: {json.dumps(brief, default=str)}"
        try:
            with self._client_manager.get_openai_client() as client:
                response = client.responses.create(model=AGENT_MODELS["diagram_studio"], input=prompt)
            raw = getattr(response, "output_text", None) or getattr(response, "text", None) or str(response)
            match = _D2_PATTERN.search(raw)
            if match:
                return match.group(1).strip()
            return raw.strip() or None
        except Exception as e:
            f_log(f"DiagramStudioModule D2 generation failed: {e}", level="error")
            return None

    def _run_grill_llm(self, prompt: str) -> str:
        try:
            with self._client_manager.get_openai_client() as client:
                response = client.responses.create(model=AGENT_MODELS["diagram_studio"], input=prompt)
            return getattr(response, "output_text", None) or getattr(response, "text", None) or str(response)
        except Exception as e:
            f_log(f"DiagramStudioModule grill LLM call failed: {e}", level="error")
            return ""
