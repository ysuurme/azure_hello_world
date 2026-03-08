import json
import logging
import azure.functions as func

from src.agents.arch_advisor import ArchitectureAdvisorAgent

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger entry point for AdvisorTrigger.
    Standard Library First: Use standard dict manipulation.
    Delegates work to agents for Single Responsibility.
    """
    logging.info('Architecture Sentinel processing a request.')

    try:
        req_body = req.get_json()
        query = req_body.get('query')
    except ValueError:
        return func.HttpResponse(
             "Invalid request payload. Please provide a JSON with a 'query' key.",
             status_code=400
        )

    if not query:
         return func.HttpResponse(
             "Query string is required.",
             status_code=400
         )

    # 2. Initialize our AI Agent with Object-Oriented Clarity (manage state and logic)
    try:
        agent = ArchitectureAdvisorAgent()
        agent_response = agent.process_query(query)
    except Exception as e:
        logging.error(f"Agent error: {e}")
        return func.HttpResponse(
             f"Error generating insight: {str(e)}",
             status_code=500
        )

    # 3. Output
    return func.HttpResponse(
        json.dumps(agent_response),
        mimetype="application/json",
        status_code=200
    )
