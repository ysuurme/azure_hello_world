import os
from dotenv import load_dotenv
load_dotenv()

from typing import Optional, Any

from src.utils.m_log import f_log

import azure.ai.projects as projects
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError

# Optional OpenAI imports — used when creating OpenAI/Azure OpenAI clients
try:
    from openai import OpenAI, AzureOpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore
    AzureOpenAI = None  # type: ignore

# Module-level caches to avoid re-initialisation and duplicate logs
_cached_aiproject_client: Optional[projects.AIProjectClient] = None
_cached_openai_client: Optional[Any] = None


class AuthManager:
    """Manage Azure authentication.

    By default this uses DefaultAzureCredential which supports:
    - interactive login (local dev via `az login`)
    - environment-based Service Principal (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
    - managed identity (when running in Azure)
    """

    def __init__(self) -> None:
        self.vault_url = os.getenv("AZURE_VAULT_URL")
        if not self.vault_url:
            f_log("AZURE_VAULT_URL not set; Key Vault operations will warn.", c_type="warning")

    def get_azure_credential(self) -> DefaultAzureCredential:
        """Return a DefaultAzureCredential instance.

        Raises ClientAuthenticationError when credentials cannot be created.
        """
        try:
            cred = DefaultAzureCredential()
            f_log("Created DefaultAzureCredential.", c_type="debug")
            return cred
        except ClientAuthenticationError as e:
            f_log(f"Azure authentication failed: {e}", c_type="error")
            raise
        except Exception as e:
            f_log(f"Unexpected error creating Azure credential: {e}", c_type="error")
            raise


class ClientManager:
    """Factory for creating authenticated AI clients.

    Usage:
        auth = AuthManager()
        cm = ClientManager(auth)
        aiproject = cm.get_aiproject_client()
    """

    def __init__(self, auth: Optional[AuthManager] = None) -> None:
        self.auth = auth or AuthManager()

    def get_aiproject_client(self) -> Optional[projects.AIProjectClient]:
        """Return an authenticated `AIProjectClient` for Azure AI Foundry `AZURE_AAIF_PROJECT_ENDPOINT`. 
        """
        endpoint = os.getenv("AZURE_AAIF_PROJECT_ENDPOINT")
        if not endpoint:
            f_log("No AI Project endpoint configured. Set AZURE_AAIF_PROJECT_ENDPOINT.", c_type="warning")
            return None

        global _cached_aiproject_client
        if _cached_aiproject_client is not None:
            return _cached_aiproject_client

        f_log("Initializing Azure credential for AIProjectClient.", c_type="process")
        cred = self.auth.get_azure_credential()

        try:
            # Connection-string style
            if ";" in endpoint:
                client = projects.AIProjectClient.from_connection_string(conn_str=endpoint)  # type: ignore
            else:
                clean = endpoint.replace("endpoint=", "").strip()
                client = projects.AIProjectClient(endpoint=clean, credential=cred)

            _cached_aiproject_client = client
            f_log("AIProjectClient initialized.", c_type="success")
            return client
        except Exception as e:
            f_log(f"Failed to initialize AIProjectClient: {e}", c_type="error")
            return None

    def get_azure_openai_client(self, api_version: str = "2024-02-01") -> Optional[Any]:
        """Return an Azure OpenAI client using Azure AD authentication.

        Requires `AZURE_OPENAI_ENDPOINT` to be set. Falls back to None if
        the `openai` package is not available.
        """
        if AzureOpenAI is None:
            f_log("azure-openai client library not installed.", c_type="warning")
            return None

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            f_log("AZURE_OPENAI_ENDPOINT not set.", c_type="warning")
            return None

        cred = self.auth.get_azure_credential()

        try:
            client = AzureOpenAI(api_version=api_version, azure_endpoint=endpoint, azure_ad_token_provider=cred.get_token)
            f_log("Azure OpenAI client initialized.", c_type="success")
            return client
        except Exception as e:
            f_log(f"Failed to initialize Azure OpenAI client: {e}", c_type="error")
            return None

    def get_openai_client(self) -> Optional[Any]:
        """Return a standard OpenAI client using `OPENAI_API_KEY`.

        This is provided for flexibility when users prefer API keys instead of Azure AD auth.
        """
        global _cached_openai_client
        if _cached_openai_client is not None:
            return _cached_openai_client

        if OpenAI is None:
            f_log("OpenAI python package not installed.", c_type="warning")
            return None

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            f_log("OPENAI_API_KEY not set.", c_type="warning")
            return None

        try:
            client = OpenAI(api_key=api_key)
            _cached_openai_client = client
            f_log("OpenAI client initialized.", c_type="success")
            return client
        except Exception as e:
            f_log(f"Failed to initialize OpenAI client: {e}", c_type="error")
            return None

