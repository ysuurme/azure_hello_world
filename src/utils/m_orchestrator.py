from src.utils.m_log import f_log
from src.agents.intake_reviewer import IntakeReviewerAgent
from src.agents.architecture_composer import ArchitectureComposerAgent
from typing import Dict, Any, Tuple

class AgenticOrchestrator:
    """
    State Management Framework utilizing Microsoft Agent Framework (MAF)
    to route between the Intake Reviewer and Architecture Composer effortlessly.
    """
    def __init__(self) -> None:
        self.reviewer = IntakeReviewerAgent()
        self.composer = ArchitectureComposerAgent()
        
    def orchestrate_cycle(self, user_prompt: str, session_state: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
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
