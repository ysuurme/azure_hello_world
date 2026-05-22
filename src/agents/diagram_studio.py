from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.config import AGENT_MODELS
from src.utils.m_diagram_engine import DiagramEngine
from src.utils.m_log import f_log

_SYSTEM_PROMPT = (
    "You are a D2 diagram code generator. "
    "Convert the user's free-text architecture description into valid D2 syntax. "
    "Use shapes, labels, and connections to represent the described components accurately. "
    "Return ONLY a single ```d2 ... ``` code block — no prose before or after."
)

_D2_PATTERN = re.compile(r"```d2\n(.*?)```", re.DOTALL)


@dataclass
class ModuleResponse:
    response_text: str
    updated_state: dict
    artifacts: dict = field(default_factory=dict)
    status: str = "completed"


class DiagramStudioModule:
    """v0 tracer — single LLM call producing D2 code; no grill, no brief, no persistence."""

    name = "Diagram Studio"
    slash_command = "/diagram"
    description = "Generate a sketch-style architecture diagram from a free-text description."

    def __init__(self, client_manager) -> None:
        self._client_manager = client_manager

    def handle(self, user_input: str, module_state: dict) -> ModuleResponse:
        parts = user_input.split(maxsplit=1)
        description = parts[1] if len(parts) > 1 else user_input

        f_log("DiagramStudioModule: generating D2 from description.", level="process")
        d2_code = self._generate_d2(description)

        if not d2_code:
            return ModuleResponse(
                response_text="Could not generate D2 code from that description. Please rephrase.",
                updated_state=module_state,
                status="error",
            )

        svg_bytes = DiagramEngine().generate_svg(d2_code, sketch=True)

        artifacts: dict = {"d2": d2_code}
        if svg_bytes:
            artifacts["svg"] = svg_bytes

        return ModuleResponse(
            response_text=f"Here is the generated diagram:\n\n```d2\n{d2_code}\n```",
            updated_state=module_state,
            artifacts=artifacts,
            status="completed",
        )

    def _generate_d2(self, description: str) -> str | None:
        try:
            with self._client_manager.get_openai_client() as client:
                combined = f"{_SYSTEM_PROMPT}\n\n{description}"
                response = client.responses.create(
                    model=AGENT_MODELS["diagram_studio"],
                    input=combined,
                )
            raw = getattr(response, "output_text", None) or getattr(response, "text", None) or str(response)
            match = _D2_PATTERN.search(raw)
            if match:
                return match.group(1).strip()
            return raw.strip() or None
        except Exception as e:
            f_log(f"DiagramStudioModule LLM call failed: {e}", level="error")
            return None
