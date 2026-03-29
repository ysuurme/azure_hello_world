import os
import json
from src.utils.m_log import f_log
import src.utils.m_ai_client as m_ai_client
from typing import Dict, Any, List
from src.config import AGENT_MODELS

from azure.ai.inference.models import SystemMessage, UserMessage
from src.utils.m_tools import calculate_cost

class ArchitectureComposerAgent:
    """
    Core "Maker" Agent using MAF concepts. 
    Queries AI search for capabilities and generates the 5-point architecture markdown.
    """
    def __init__(self) -> None:
        # Use the ClientManager API for obtaining an authenticated client.
        self.client = m_ai_client.ClientManager().get_aiproject_client()
        # If the returned client doesn't expose an `inference` surface (older/partial clients),
        # treat it as if no client was provided so the local/mock path is used.
        if self.client and not hasattr(self.client, "inference"):
            f_log("Foundry client has no 'inference' attribute; falling back to mock mode.", c_type="warning")
            self.client = None
        self.system_prompt = (
            "You are the Solution Architecture Generator. "
            "Based on the chosen capabilities from the RAG search, produce a highly structured Markdown document exactly matching this standard:\n"
            "a. Purpose of the solution architecture\n"
            "b. Decisions that lead to the solution architecture\n"
            "c. Scenario's considered with pro's/con's for the solution architecture\n"
            "d. Rationale for selecting the solution architecture in b.\n"
            "e. Implementation guidelines containing any relevant details"
        )

    def _retrieve_capabilities(self, requirements: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Mock Hybrid/Semantic Search over the capabilities Markdown files in Azure AI Search.
        """
        f_log(f"Retrieving capabilities for constraints: {requirements.get('constraints')}", c_type="process")
        # In reality, this queries `src.utils.m_search.knowledge_base_retrieve`
        return [
            {"technology": "Azure Container Apps", "reason": "Serverless scale-down matches Cost Constraint"},
            {"technology": "Prometheus", "reason": "Open-source requirement met"}
        ]

    def generate_architecture(self, requirements: Dict[str, Any]) -> str:
        """
        Executes the Composer step. Returns the final Markdown string natively via LLM.
        """
        f_log("Composer received ready-requirements. Searching capabilities repo.", c_type="process")
        selected_tech = self._retrieve_capabilities(requirements)
        
        # If client is absent or lacks inference surface, use mocked architecture
        if not self.client or not hasattr(self.client, "inference"):
            f_log("No live Foundry Client. Returning mocked Architecture.", c_type="warning")
            doc = f"# Proposed Solution Architecture\n\n## a. Purpose\nTo fulfill the business objective: {requirements.get('objective', 'Custom App.')}\n\n"
            doc += f"## b. Decisions\n- We selected **{selected_tech[0]['technology']}** for Compute.\n"
            doc += "## c. Scenarios Considered with Pros/Cons\n"
            doc += f"- *Scenario 1 (PaaS)*: {selected_tech[0]['technology']} (Pros: Serverless. Cons: Cold Starts).\n"
            doc += "## d. Rationale\nThis matches the strict constraints provided during intake.\n\n"
            doc += f"## e. Implementation Guidelines\nFollow the specific RAG guidelines attached."
            return doc
            
        f_log("Drafting 5-point architecture via Azure Foundry...", c_type="process")

        # Checker Synergy: Price evaluation dynamically added
        tech_names = [tech.get("technology") for tech in selected_tech]
        cost_evaluation = calculate_cost(tech_names)
        
        user_query = f"User Intake Requirements Constraints:\n{json.dumps(requirements, indent=2)}\n\n"
        user_query += f"Maker Output (Initial RAG Selection):\n{json.dumps(selected_tech, indent=2)}\n\n"
        user_query += f"Checker Constraint Evaluation (Azure Retail Price Live Sync):\n{json.dumps(cost_evaluation, indent=2)}\n\n"
        user_query += "INSTRUCTION: You must critique the Maker Output against the Checker Costs. If the Monthly Cost exceeds the User Constraint budget, you MUST select an alternative 'Value' technology inside your rationale and adjust the architecture diagram output accordingly. Draft the markdown strictly according to the format."
        
        try:
            f_log("Calling AI Foundry Inference...", c_type="process")

            # Support both the 2026 SDK (get_chat_completions_client().complete)
            # and legacy mocks that expose inference.get_chat_completions(...)
            inference = getattr(self.client, "inference", None)
            if inference is None:
                raise AttributeError("Client has no inference attribute")

            # Prefer legacy test-friendly API when available (many tests/mocks expose this)
            get_completions = getattr(inference, "get_chat_completions", None)
            if callable(get_completions):
                response = get_completions(model=AGENT_MODELS["architecture_composer"], messages=[SystemMessage(content=self.system_prompt), UserMessage(content=user_query)])
            else:
                # Fall back to the new factory method if present
                get_client = getattr(inference, "get_chat_completions_client", None)
                if not callable(get_client):
                    raise AttributeError("No compatible inference method found on client.inference")
                chat_client = get_client()
                response = chat_client.complete(
                    model=AGENT_MODELS["architecture_composer"],
                    messages=[SystemMessage(content=self.system_prompt), UserMessage(content=user_query)]
                )

            return response.choices[0].message.content
        except Exception as e:
            f_log(f"LLM Generation Failed: {e}", c_type="error")
            return f"Error Generating Architecture: {e}"
