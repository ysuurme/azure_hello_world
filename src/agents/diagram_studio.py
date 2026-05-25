from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import src.config as config
from src.agents._refinement import RefinementMixin
from src.config import AGENT_MODELS
from src.utils.m_diagram_engine import DiagramEngine
from src.utils.m_diagram_store import get_diagram_store, slugify
from src.utils.m_log import f_log
from src.utils.m_persist_design import _brief_to_markdown

_D2_SYSTEM_PROMPT = (
    "You are an expert D2 diagram author. Convert the DiagramBrief JSON into clean, valid, visually "
    "polished D2. Return ONLY a single ```d2 ... ``` code block — no prose.\n\n"
    "Author it like a real architecture diagram, not a row of identical boxes:\n"
    "- Start with `direction: <layout_direction>`.\n"
    "- GROUPING: when components share a `group`, nest them in a D2 container so you get blocks-in-blocks, "
    'e.g.\n  ingress: "Ingress" {\n    gateway: "API Gateway"\n    auth: "Auth"\n  }\n'
    "- PALETTE (not monochrome): define classes and tag each shape by role. Example:\n"
    "  classes: {\n"
    '    service: { style: { fill: "#e8f0fe"; stroke: "#1a73e8"; border-radius: 8 } }\n'
    '    datastore: { shape: cylinder; style: { fill: "#fce8e6"; stroke: "#c5221f" } }\n'
    '    queue: { shape: hexagon; style: { fill: "#fef7e0"; stroke: "#f9ab00" } }\n'
    '    external: { style: { fill: "#f1f3f4"; stroke: "#5f6368"; stroke-dash: 3 } }\n'
    "  }\n"
    "  then `order_svc.class: service`, `db.class: datastore`, etc. Map the brief's `shape` and pick the "
    "class that fits each component's role.\n"
    "- RELATIONSHIPS: label every edge with what flows. Solid arrow for synchronous calls; dashed for "
    'async/events, e.g. `services.order_svc -> bus.queue: emits { style.stroke-dash: 4 }`. ALWAYS '
    "reference nested shapes by their FULL container path so edges connect the real nodes instead of "
    "spawning new empty top-level ones.\n"
    "- Stay faithful to the brief — do NOT invent components that are not in it.\n"
    "- The output MUST compile as valid D2."
)

_D2_PATTERN = re.compile(r"```d2\n(.*?)```", re.DOTALL)

_APPROVAL_PHRASES = frozenset({"yes", "approved", "looks good", "lgtm", "ship it"})
_RENDER_PHRASES = frozenset({"render", "draw", "draw it", "show me", "generate", "generate now", "good enough"})


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
    lines.append("_Answer to refine further, or reply `render` to draw the current draft now._")
    return "\n".join(lines)


def _is_approved(user_input: str) -> bool:
    return user_input.strip().lower() in _APPROVAL_PHRASES


def _wants_render(user_input: str) -> bool:
    return user_input.strip().lower() in _RENDER_PHRASES


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
        self._store = None

    def _get_store(self):
        if self._store is None:
            cred = self._client_manager.get_credential() if config.DIAGRAM_STORAGE_ACCOUNT else None
            self._store = get_diagram_store(cred)
        return self._store

    def handle(self, user_input: str, module_state: dict) -> ModuleResponse:
        if user_input.strip().lower().startswith(self.slash_command):
            return self._handle_command(user_input.strip(), module_state)
        phase = module_state.get("phase")
        if phase == "grilling":
            return self._grill_turn(user_input, module_state)
        if phase == "awaiting_approval":
            return self._approval_turn(user_input, module_state)
        return self._first_turn(user_input, module_state)

    def _handle_command(self, text: str, module_state: dict) -> ModuleResponse:
        parts = text.split(maxsplit=2)
        sub = parts[1].lower() if len(parts) > 1 else ""
        arg = parts[2] if len(parts) > 2 else ""
        if sub == "list":
            return self._list_diagrams(module_state)
        if sub == "open":
            return self._open_diagram(arg, module_state)
        if sub == "delete":
            return self._delete_diagram(arg, module_state)
        return self._first_turn(text, module_state)

    def _list_diagrams(self, module_state: dict) -> ModuleResponse:
        summaries = self._get_store().list()
        if not summaries:
            text = "No saved diagrams yet. Create one with `/diagram <description>`."
        else:
            rows = ["| Name | Subject |", "|------|---------|"]
            rows += [f"| `{s.slug}` | {s.subject} |" for s in summaries]
            text = "Saved diagrams — open with `/diagram open <name>`:\n\n" + "\n".join(rows)
        return ModuleResponse(response_text=text, updated_state=module_state, status="completed")

    def _open_diagram(self, name: str, module_state: dict) -> ModuleResponse:
        slug = slugify(name)
        record = self._get_store().load(slug)
        if record is None:
            return ModuleResponse(
                response_text=f"No diagram named `{slug}` found. Use `/diagram list` to see saved diagrams.",
                updated_state=module_state,
                status="completed",
            )
        subject = record.brief.get("subject", slug)
        md = _brief_to_markdown(_brief_dict_to_dataclass(record.brief))
        artifacts: dict = {"d2": record.d2}
        if record.svg:
            artifacts["svg"] = record.svg
        return ModuleResponse(
            response_text=(
                f"Opened **{subject}** (`{slug}`). Describe changes to build forward, "
                f"or reply `yes` to re-render as-is.\n\n" + md
            ),
            updated_state={
                "phase": "awaiting_approval",
                "description": subject,
                "brief": record.brief,
                "slug": slug,
                "d2": record.d2,
            },
            artifacts=artifacts,
            status="awaiting_approval",
        )

    def _delete_diagram(self, name: str, module_state: dict) -> ModuleResponse:
        slug = slugify(name)
        ok = self._get_store().delete(slug)
        text = f"Deleted diagram `{slug}`." if ok else f"No diagram named `{slug}` found."
        return ModuleResponse(response_text=text, updated_state=module_state, status="completed")

    def _first_turn(self, user_input: str, module_state: dict) -> ModuleResponse:
        parts = user_input.split(maxsplit=1)
        description = parts[1] if len(parts) > 1 else user_input
        f_log("DiagramStudioModule: starting grill round.", level="process")
        grill = self.grill_round(f"[Refinement round 1]\n{description}", {})
        new_state = {"phase": "grilling", "description": description, "brief": grill.updated_brief, "round": 1}
        if grill.complete:
            return self._present_for_approval(grill.updated_brief, new_state)
        return ModuleResponse(
            response_text=_format_grill_questions(grill.questions),
            updated_state=new_state,
            status="in_refinement",
        )

    def _grill_turn(self, user_input: str, module_state: dict) -> ModuleResponse:
        if _wants_render(user_input):
            f_log("DiagramStudioModule: user requested intermediate render.", level="process")
            return self._generate_diagram(module_state.get("brief", {}), module_state)
        description = module_state.get("description", "")
        current_brief = module_state.get("brief", {})
        round_num = module_state.get("round", 1) + 1
        context = f"[Refinement round {round_num}]\n{description}\n\nUser answers to previous questions: {user_input}"
        f_log("DiagramStudioModule: folding grill answers.", level="process")
        grill = self.grill_round(context, current_brief)
        new_state = {**module_state, "brief": grill.updated_brief, "round": round_num}
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
        d2_code = self._generate_d2_from_brief(brief, prior_d2=module_state.get("d2"))
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
        slug = self._get_store().save(brief, d2_code, svg_bytes)
        artifacts["slug"] = slug
        # Stay in awaiting_approval (not "completed") so the user can keep refining this
        # same diagram by describing further changes; each pass re-generates and re-saves.
        return ModuleResponse(
            response_text=(
                f"Here is the diagram (saved as `{slug}`). Describe further changes to keep "
                f"iterating, or `/diagram open <name>` to switch diagrams:\n\n```d2\n{d2_code}\n```"
            ),
            updated_state={**module_state, "phase": "awaiting_approval", "slug": slug, "d2": d2_code, "brief": brief},
            status="completed",
            artifacts=artifacts,
        )

    def _generate_d2_from_brief(self, brief: dict, prior_d2: str | None = None) -> str | None:
        prompt = f"{_D2_SYSTEM_PROMPT}\n\nBrief: {json.dumps(brief, default=str)}"
        if prior_d2:
            prompt += (
                "\n\nThis diagram already exists. Update the following D2 to reflect the brief, "
                f"preserving existing structure and styling where still valid:\n```d2\n{prior_d2}\n```"
            )
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
                response = client.responses.create(model=AGENT_MODELS["diagram_grill"], input=prompt)
            return getattr(response, "output_text", None) or getattr(response, "text", None) or str(response)
        except Exception as e:
            f_log(f"DiagramStudioModule grill LLM call failed: {e}", level="error")
            return ""
