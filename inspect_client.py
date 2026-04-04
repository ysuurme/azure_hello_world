from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import os
from dotenv import load_dotenv

load_dotenv()
endpoint = os.getenv("AZURE_AAIF_PROJECT_ENDPOINT", "https://example.com")
cred = DefaultAzureCredential()

try:
    client = AIProjectClient(endpoint=endpoint, credential=cred)
    print(f"Attributes: {dir(client)}")
    if hasattr(client, 'inference'):
        print(f"Inference attributes: {dir(client.inference)}")
    else:
        print("No 'inference' attribute.")
except Exception as e:
    print(f"Error: {e}")
