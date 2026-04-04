import azure.ai.projects as projects
from azure.identity import DefaultAzureCredential
import os
from dotenv import load_dotenv

load_dotenv()
endpoint = os.getenv("AZURE_AAIF_PROJECT_ENDPOINT", "https://example.com")
cred = DefaultAzureCredential()

try:
    client = projects.AIProjectClient(endpoint=endpoint, credential=cred)
    print("AIProjectClient initialized.")
    # Try common attributes for inference/deployments
    for attr in ["inference", "deployments", "models", "inference_client"]:
        if hasattr(client, attr):
            print(f"Found attribute: {attr}")
        else:
            print(f"No attribute: {attr}")
except Exception as e:
    print(f"Error: {e}")
