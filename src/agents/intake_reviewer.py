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
    def __init__(self) -> None:
        # Obtain authenticated client via ClientManager API
        self.client = m_ai_client.ClientManager().get_aiproject_client()
        # If the returned client doesn't expose an `inference` surface, fall back to mocked logic.
        if self.client and not hasattr(self.client, "inference"):
            f_log("Foundry client has no 'inference' attribute; falling back to mock mode.", c_type="warning")
            self.client = None
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

        # Treat missing or incomplete clients (no inference surface) as no-client fallback
        if not self.client or not hasattr(self.client, "inference"):
            f_log("No live client found or client lacks inference; Falling back to mocked logic.", c_type="warning")
            if len(user_prompt.split()) < 5:
                return {"status": "needs_clarification", "questions": ["Please provide more details on workload."]}
            return {"status": "ready", "requirements": {"objective": user_prompt}}
        # MVP LLM Integration via Inference Client 
        try:
            f_log("Calling AI Foundry Inference...", c_type="process")

            inference = getattr(self.client, "inference", None)
            if inference is None:
                raise AttributeError("Client has no inference attribute")

            # Prefer legacy test-friendly API when available
            get_completions = getattr(inference, "get_chat_completions", None)
            if callable(get_completions):
                response = get_completions(model=AGENT_MODELS["intake_reviewer"], messages=[SystemMessage(content=self.system_prompt), UserMessage(content=user_prompt)])
            else:
                # Fall back to the new factory method if present
                get_client = getattr(inference, "get_chat_completions_client", None)
                if not callable(get_client):
                    raise AttributeError("No compatible inference method found on client.inference")
                chat_client = get_client()
                response = chat_client.complete(
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
