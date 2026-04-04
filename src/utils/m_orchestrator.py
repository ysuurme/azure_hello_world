from typing import Any

import src.utils.m_ai_client as m_ai_client
from src.agents.architecture_composer import ArchitectureComposerAgent
from src.agents.intake_reviewer import IntakeReviewerAgent
from src.utils.m_log import f_log


class AgenticOrchestrator:
    """
    State Management Framework utilizing Microsoft Agent Framework (MAF)
    to route between the Intake Reviewer and Architecture Composer effortlessly.
    """
    def __init__(self, client_manager: m_ai_client.ClientManager) -> None:
        # Require a shared ClientManager instance created at app bootstrap.
        if client_manager is None:
            raise ValueError("client_manager is required for AgenticOrchestrator")
        self.reviewer = IntakeReviewerAgent(client_manager=client_manager)
        self.composer = ArchitectureComposerAgent(client_manager=client_manager)
        
    def orchestrate_cycle(self, user_prompt: str, session_state: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """
        Manages the transition state without blocking the Streamlit UI.
        Returns a tuple: (State Update Dict, Output Text/Markdown).
        """
        f_log("Orchestrator initiating MAF lifecycle.", c_type="process")
        
        # Step 1: Route to Intake Reviewer
        intake_response = self.reviewer.review_input(user_prompt)
        
        if intake_response.get("status") == "needs_clarification":
            f_log("MAF halted at Intake phase: Clarification needed.", c_type="warning")
            # Update State machine to wait for input
            session_state["phase"] = "CLARIFYING"
            questions = "\n".join([f"- {q}" for q in intake_response.get("questions", [])])
            return session_state, f"To help me design this architecture perfectly, please clarify:\n{questions}"
            
        elif intake_response.get("status") == "ready":
            f_log("MAF progressing to Composer phase.", c_type="success")
            session_state["phase"] = "GENERATION"
            requirements = intake_response.get("requirements", {})
            
            # Step 2: Route to Composer
            markdown_output = self.composer.generate_architecture(requirements)
            return session_state, markdown_output
            
        f_log("Unhandled MAF State.", c_type="error")
        return session_state, "Unknown state occurred in Orchestrator."

    def get_d2_syntax(self, markdown: str) -> str | None:
        """
        Delegates D2 extraction to the composer agent.
        """
        return self.composer.generate_d2_syntax(markdown)
