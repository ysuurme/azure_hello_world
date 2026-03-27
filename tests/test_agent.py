import pytest
import azure.functions as func
from src.agent_trigger import main

def test_my_hobby_agent_missing_data():
    # Test that the agent handles invalid input cleanly (Mockability).
    req = func.HttpRequest(
        method='POST',
        url='/api/agent_trigger',
        body=b'{"wrong_key": "data"}'
    )
    
    response = main(req)
    # The parser should return None and trigger a 400
    assert response.status_code == 400
