import os
import json
from src.utils.m_log import f_log
from src.utils.m_agentfactory import get_foundry_agent_client
from src.config import AGENT_MODELS, TEMPLATE_PATH
from typing import Dict, Any

from azure.ai.inference.models import SystemMessage, UserMessage

class IntakeReviewerAgent:
    """
    Validates user input against the architecture template natively via Live LLM integration.
    """
    def __init__(self) -> None:
        self.client = get_foundry_agent_client()
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
        
        if not self.client:
             f_log("No live client found. Falling back to mocked logic.", c_type="warning")
             if len(user_prompt.split()) < 5:
                  return {"status": "needs_clarification", "questions": ["Please provide more details on workload."]}
             return {"status": "ready", "requirements": {"objective": user_prompt}}
             
        # MVP LLM Integration via Inference Client 
        try:
            f_log("Calling AI Foundry Inference...", c_type="process")
            response = self.client.inference.get_chat_completions(
                # Pull dynamically from active environmental singleton config
                model=AGENT_MODELS["intake_reviewer"], 
                messages=[
                    SystemMessage(content=self.system_prompt),
                    UserMessage(content=user_prompt)
                ]
            )
            raw_output = response.choices[0].message.content
            # To handle markdown json wrappers securely:
            clean_json = raw_output.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
            
        except Exception as e:
            f_log(f"Azure Inference Failure: {str(e)}", c_type="error")
            return {"status": "needs_clarification", "questions": [f"I encountered a service fault analyzing your request: {e}"]}
