import json
import re
from typing import Any

import src.utils.m_ai_client as m_ai_client
from src.config import AGENT_MODELS
from src.utils.m_log import f_log

# Use Foundry/OpenAI-style responses client via AIProjectClient.get_openai_client()
from src.utils.m_search import knowledge_base_retrieve
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
            "Based on the chosen capabilities from the RAG search, "
            "produce a highly structured Markdown document exactly "
            "matching this standard:\n"
            "a. Purpose of the solution architecture\n"
            "b. Decisions that lead to the solution architecture\n"
            "c. Scenario's considered with pro's/con's for the solution architecture\n"
            "d. Rationale for selecting the solution architecture in b.\n"
            "e. Implementation guidelines containing any relevant details\n\n"
            "After the markdown, you MUST include a D2 diagram syntax block wrapped in ```d2 ... ``` "
            "that visualizes the architecture components and their relationships.\n\n"
            "### STRICT D2 SCHEMA RULES\n"
            "To prevent compilation errors and adhere to Hexagonal/Clean Architecture, follow these syntactical rules:\n"
            "1. Define components strictly with `shape` attributes (e.g., `component: {shape: cylinder}`). Do NOT use unsupported HTML tags.\n"
            "2. Ensure all components are grouped logically into Bounded Contexts or Hexagonal layers (e.g., `Core Domain`, `Adapters`, `Infrastructure`).\n"
            "3. Use `direction: right` or `direction: down` at the top of the diagram for consistent flow.\n"
            "4. Enforce Hexagonal Architecture flow: External Triggers -> Application Adapters -> Domain Core. Dependency arrows (`->`) MUST point inwards.\n"
            "5. Apply standard colors/classes to indicate Azure components vs Core Logic where appropriate.\n"
            "6. Always include `classes: { ... }` or `theme: sketch` to style the diagram safely without raw CSS.\n"
            "If you fail to follow valid D2 syntax, the UI will crash. Use simple, robust node declarations."
        )

    def _retrieve_capabilities(self, requirements: dict[str, Any]) -> list[dict[str, str]]:
        """
        Context-Aware Search over the capabilities Markdown files.
        """
        query = str(requirements.get('constraints', 'azure architecture'))
        f_log(f"Retrieving capabilities for query: {query}", c_type="process")
        
        # Use the local RAG search implementation
        search_results = knowledge_base_retrieve(query)
        
        # Map back to expected format
        return [{"technology": res["id"].replace(".md", ""), "reason": res["content"]} for res in search_results]

    def generate_architecture(self, requirements: dict[str, Any]) -> str:
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
        user_query += (
            f"Checker Constraint Evaluation (Azure Retail Price Live Sync):\n"
            f"{json.dumps(cost_evaluation, indent=2)}\n\n"
        )
        user_query += (
            "INSTRUCTION: You must critique the Maker Output against the "
            "Checker Costs. If the Monthly Cost exceeds the User Constraint "
            "budget, you MUST select an alternative 'Value' technology inside "
            "your rationale and adjust the architecture diagram output "
            "accordingly. Draft the markdown strictly according to the format, "
            "and ALWAYS include the ```d2 code block at the end."
        )

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

    def generate_d2_syntax(self, markdown: str) -> str | None:
        """
        Extracts D2 syntax from a markdown code block.
        """
        match = re.search(r"```d2\n(.*?)```", markdown, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
