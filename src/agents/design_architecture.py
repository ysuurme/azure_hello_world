from __future__ import annotations

from dataclasses import dataclass, field

import src.utils.m_ai_client as m_ai_client
from src.utils.m_diagram_engine import DiagramEngine
from src.utils.m_log import f_log
from src.utils.m_orchestrator import AgenticOrchestrator
from src.utils.m_persist_design import ArchitecturePersister


@dataclass
class ModuleResponse:
    response_text: str
    updated_state: dict
    artifacts: dict = field(default_factory=dict)
    status: str = "completed"


class DesignArchitectureModule:
    """Wraps AgenticOrchestrator as a registered WorkflowModule under /design."""

    name = "Design Architecture"
    slash_command = "/design"
    description = "Design a multi-tier Azure architecture from requirements (intake → composer)."

    def __init__(self, client_manager: m_ai_client.ClientManager) -> None:
        self._client_manager = client_manager

    def handle(self, user_input: str, module_state: dict) -> ModuleResponse:
        parts = user_input.split(maxsplit=1)
        prompt = parts[1] if len(parts) > 1 and user_input.startswith("/") else user_input

        orchestrator = AgenticOrchestrator(client_manager=self._client_manager)
        updated_state, output_text = orchestrator.orchestrate_cycle(prompt, dict(module_state))

        phase = updated_state.get("phase")
        if phase == "CLARIFYING":
            return ModuleResponse(
                response_text=output_text,
                updated_state=updated_state,
                status="in_refinement",
            )

        artifacts: dict = {}
        if phase == "GENERATION":
            f_log("DesignArchitectureModule: architecture finalised, building diagram.", level="process")
            d2_syntax = orchestrator.get_d2_syntax(output_text)
            if d2_syntax:
                svg_bytes = DiagramEngine().generate_svg(d2_syntax)
                if svg_bytes:
                    artifacts["svg"] = svg_bytes
                else:
                    f_log("D2 compilation returned no bytes.", level="warning")
                artifacts["d2"] = d2_syntax
            else:
                f_log("No D2 syntax block found in LLM output.", level="warning")

            svg_to_persist = artifacts.get("svg")
            ArchitecturePersister().archive_solution("Lean-MVP-Design", output_text, svg_to_persist)

        return ModuleResponse(
            response_text=output_text,
            updated_state=updated_state,
            artifacts=artifacts,
            status="completed",
        )
