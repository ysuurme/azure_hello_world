import os
from src.utils.m_log import f_log
from typing import Optional

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

def get_foundry_agent_client() -> Optional[AIProjectClient]:
    """
    Factory function to initialize the Azure AI Foundry Agent Service Client safely.
    Follows Single Responsibility rule and strictly avoids embedded API keys.
    """
    endpoint = os.environ.get("AIPROJECT_CONNECTION_STRING") or os.environ.get("AIFOUNDRY_CONNECTION_STRING")
    
    if not endpoint:
        f_log("AIPROJECT_CONNECTION_STRING not found in .env.", c_type="warning")
        return None
        
    f_log("Initializing DefaultAzureCredential for AI Foundry.", c_type="process")
    try:
        credential = DefaultAzureCredential()
        
        # Determine if this is a classic ';' separated connection string or a direct endpoint URI
        if ";" in endpoint:
            client = AIProjectClient.from_connection_string(
                credential=credential, 
                conn_str=endpoint
            )
        else:
            # If the user pasted a raw URI (optionally prefixed by "endpoint=")
            clean_endpoint = endpoint.replace("endpoint=", "").strip()
            client = AIProjectClient(
                endpoint=clean_endpoint,
                credential=credential
            )
            
        f_log("Foundry client connected successfully.", c_type="success")
        return client
    except Exception as e:
        f_log(f"Failed to authenticate with Azure AI Foundry: {str(e)}", c_type="error")
        return None
