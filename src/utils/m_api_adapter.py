import requests
from typing import Dict, Any
from src.utils.m_log import f_log

def fetch_architecture_insight(query: str, api_url: str) -> Dict[str, Any]:
    """
    Adapter bridging the Streamlit UI (Port 8501) and the Azure Function (Port 7071).
    This ensures the UI boundary contains zero HTTP logic, satisfying Hexagonal paradigms.
    """
    f_log(f"Routing query to Agent API at {api_url}", c_type="process")
    
    payload = {"query": query}
    # Industry standard exception for 'requests' over 'urllib' granted in SKILL.md
    response = requests.post(api_url, json=payload, timeout=120)
    
    # We raise for status early so the caller (UI) can handle HTTP failure gracefully (Guard clauses).
    response.raise_for_status()
    
    f_log("Agent API response received successfully.", c_type="success")
    return response.json()
