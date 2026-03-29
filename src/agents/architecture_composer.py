import os
import json
from src.utils.m_log import f_log
import src.utils.m_ai_client as m_ai_client
from typing import Dict, Any, List
from src.config import AGENT_MODELS

# Use Foundry/OpenAI-style responses client via AIProjectClient.get_openai_client()
from src.utils.m_tools import calculate_cost

class ArchitectureComposerAgent:
    """
    Core "Maker" Agent using MAF concepts. 
    Queries AI search for capabilities and generates the 5-point architecture markdown.
    """
    def __init__(self, client_manager: m_ai_client.ClientManager) -> None:
        # Require a shared ClientManager instance to be injected at bootstrap.
        if client_manager is None:
            raise ValueError("client_manager is required — create a single shared ClientManager at app bootstrap")
        self.client_manager = client_manager
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
        
        # Use the chat completions client for LLM drafting.
        # Do not fallback to mocked output — raise on any missing/incompatible surfaces.
            
        f_log("Drafting 5-point architecture via Azure Foundry...", c_type="process")

        # Checker Synergy: Price evaluation dynamically added
        tech_names = [tech.get("technology") for tech in selected_tech]
        cost_evaluation = calculate_cost(tech_names)
        
        user_query = f"User Intake Requirements Constraints:\n{json.dumps(requirements, indent=2)}\n\n"
        user_query += f"Maker Output (Initial RAG Selection):\n{json.dumps(selected_tech, indent=2)}\n\n"
        user_query += f"Checker Constraint Evaluation (Azure Retail Price Live Sync):\n{json.dumps(cost_evaluation, indent=2)}\n\n"
        user_query += "INSTRUCTION: You must critique the Maker Output against the Checker Costs. If the Monthly Cost exceeds the User Constraint budget, you MUST select an alternative 'Value' technology inside your rationale and adjust the architecture diagram output accordingly. Draft the markdown strictly according to the format."
        
        # Call AI Foundry Responses via OpenAI surface exclusively.
        try:
            f_log("Calling AI Foundry Responses via OpenAI surface...", c_type="process")
            with self.client_manager.get_openai_client() as openai_client:
                combined_input = f"{self.system_prompt}\n\n{user_query}"
                response = openai_client.responses.create(
                    model=AGENT_MODELS["architecture_composer"],
                    input=combined_input,
                )

            return getattr(response, "output_text", None) or getattr(response, "text", None) or str(response)
        except Exception as e:
            f_log(f"LLM Generation Failed: {e}", c_type="error")
            return f"Error Generating Architecture: {e}"
