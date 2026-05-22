from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import src.utils.m_ai_client as m_ai_client
from src.agents.architecture_composer import ArchitectureComposerAgent
from src.agents.intake_reviewer import IntakeReviewerAgent
from src.utils.m_diagram_engine import DiagramEngine
from src.utils.m_log import f_log
from src.utils.m_persist_design import ArchitecturePersister


@dataclass
class ModuleResponse:
    response_text: str
    updated_state: dict
    artifacts: dict = field(default_factory=dict)
    status: str = "completed"


class DesignArchitectureModule:
    """`/design` capability: owns intake → composer → SVG render → archive lifecycle."""

    name = "Design Architecture"
    slash_command = "/design"
    description = "Design a multi-tier Azure architecture from requirements (intake → composer)."

    def __init__(self, client_manager: m_ai_client.ClientManager) -> None:
        self._reviewer = IntakeReviewerAgent(client_manager=client_manager)
        self._composer = ArchitectureComposerAgent(client_manager=client_manager)

    def handle(self, user_input: str, module_state: dict) -> ModuleResponse:
        prompt = self._strip_slash(user_input)
        state = dict(module_state)

        f_log("DesignArchitectureModule: initiating intake review.", level="process")
        intake = self._reviewer.review_input(prompt)
        status = intake.get("status")

        if status == "needs_clarification":
            return self._build_clarification(intake, state)
        if status == "ready":
            return self._build_generation(intake, state)

        f_log("Unhandled intake state.", level="error")
        return ModuleResponse(
            response_text="Unknown state occurred in DesignArchitectureModule.",
            updated_state=state,
            status="error",
        )

    @staticmethod
    def _strip_slash(user_input: str) -> str:
        parts = user_input.split(maxsplit=1)
        if len(parts) > 1 and user_input.startswith("/"):
            return parts[1]
        return user_input

    @staticmethod
    def _build_clarification(intake: dict, state: dict) -> ModuleResponse:
        f_log("Intake clarification needed; remaining in refinement.", level="warning")
        state["phase"] = "CLARIFYING"
        questions = "\n".join(f"- {q}" for q in intake.get("questions", []))
        return ModuleResponse(
            response_text=f"To help me design this architecture perfectly, please clarify:\n{questions}",
            updated_state=state,
            status="in_refinement",
        )

    def _build_generation(self, intake: dict, state: dict) -> ModuleResponse:
        f_log("Intake ready; composing architecture.", level="success")
        state["phase"] = "GENERATION"
        requirements = intake.get("requirements", {})
        markdown = self._composer.generate_architecture(requirements)
        artifacts = self._build_artifacts(markdown)
        ArchitecturePersister().archive_solution("Lean-MVP-Design", markdown, artifacts.get("svg"))
        return ModuleResponse(
            response_text=markdown,
            updated_state=state,
            artifacts=artifacts,
            status="completed",
        )

    def _build_artifacts(self, markdown: str) -> dict[str, Any]:
        artifacts: dict[str, Any] = {}
        d2_syntax = self._composer.generate_d2_syntax(markdown)
        if not d2_syntax:
            f_log("No D2 syntax block found in LLM output.", level="warning")
            return artifacts
        artifacts["d2"] = d2_syntax
        svg_bytes = DiagramEngine().generate_svg(d2_syntax)
        if svg_bytes:
            artifacts["svg"] = svg_bytes
        else:
            f_log("D2 compilation returned no bytes.", level="warning")
        return artifacts
