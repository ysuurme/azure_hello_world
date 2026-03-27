from src.utils.m_log import f_log
from typing import Dict, Any

from src.utils.agent_factory import get_foundry_agent_client
from src.utils.tools import calculate_cost

class ArchitectureAdvisorAgent:
    """
    Core Architecture Sentinel Agent logic.
    Follows Object-Oriented Clarity: Source of truth for agent state.
    """
    def __init__(self) -> None:
        # Initialize the connection via the Factory (Single Responsibility)
        self.client = get_foundry_agent_client()
        
        # Define the Maker-Checker system prompt
        self.system_prompt = (
            "You are the Azure Architecture Sentinel, an elite Technical Design Authority. "
            "You follow a Maker-Checker reasoning loop. "
            "1. Maker: Formulate an architecture proposal prioritizing internal docs from the GitHub repo, "
            "supplemented by Microsoft Well-Architected Framework (WAF) guidance. "
            "ALWAYS prioritize calling the knowledge_base_retrieve tool before proposing. "
            "2. Checker: Critique your proposal against the Security and Cost pillars of the WAF. "
            "3. Refinement: Evaluate the design utilizing the calculate_cost tool. If the proposal "
            "exceeds optimal budgets, provide a 'Value' alternative and present a Trade-off Matrix."
        )

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Executes the reasoning loop.
        """
        f_log(f"Agent processing query: {query}", c_type="reasoning")
        
        # In a fully deployed Phase 1, the client would orchestrate the thread.
        # For this execution step, we return the structured scaffold response.
        if not self.client:
           f_log("No live Foundry Client found. Executing Local Mock Path.", c_type="warning")
           
        # Example Tool Execution (Standard Library First)
        cost_assessment = calculate_cost(["Front Door", "Multi-Region App Service"])
           
        return {
            "status": "success",
            "recommendation": "Mocked Recommendation generated using Maker-Checker loop.",
            "insight": {
                "base_query": query,
                "cost_evaluation": cost_assessment
            }
        }
