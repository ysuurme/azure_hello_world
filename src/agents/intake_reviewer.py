import os
import json
from src.utils.m_log import f_log
import src.utils.m_ai_client as m_ai_client
from src.config import AGENT_MODELS, TEMPLATE_PATH
from typing import Dict, Any

from azure.ai.inference.models import SystemMessage, UserMessage

class IntakeReviewerAgent:
    """
    Validates user input against the architecture template natively via Live LLM integration.
    """
    def __init__(self, client_manager: m_ai_client.ClientManager) -> None:
        # Require a shared ClientManager instance to be injected at bootstrap.
        if client_manager is None:
            raise ValueError("client_manager is required — create a single shared ClientManager at app bootstrap")
        self.client_manager = client_manager
        self.template_path = TEMPLATE_PATH
        self._load_template()
        
        self.system_prompt = (
            "You are the Intake Reviewer for an Architecture Sentinel. "
            f"Your job is to review the user's software description against this template: \n{self.template}\n"
            "If the user has not provided enough information, return a JSON object exactly like this: "
            '{"status": "needs_clarification", "questions": ["Question 1", "Question 2"]} '
            "If the information is sufficient, return exactly: "
            '{"status": "ready", "requirements": {"objective": "...", "workload": "...", "data": "...", "integration": "...", "constraints": "..."}}'
        )

    def _load_template(self) -> None:
        if os.path.exists(self.template_path):
            with open(self.template_path, "r", encoding="utf-8") as f:
                self.template = f.read()
        else:
            self.template = "Standard 5-pillar architecture template."

    def review_input(self, user_prompt: str) -> Dict[str, Any]:
        """
        Executes the intake review process, invoking live Azure OpenAI if client exists.
        """
        f_log(f"IntakeReviewer reviewing prompt: {user_prompt[:50]}...", c_type="process")

        try:
            f_log("Calling AI Foundry Inference...", c_type="process")
            chat = self.client_manager.get_chat_completions_client()
            response = chat.complete(
                model=AGENT_MODELS["intake_reviewer"],
                messages=[SystemMessage(content=self.system_prompt), UserMessage(content=user_prompt)]
            )

            raw_output = response.choices[0].message.content
            # To handle markdown json wrappers securely:
            clean_json = raw_output.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)

        except Exception as e:
            f_log(f"Azure Inference Failure: {str(e)}", c_type="error")
            return {"status": "needs_clarification", "questions": [f"I encountered a service fault analyzing your request: {e}"]}
