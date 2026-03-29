import os
from dotenv import load_dotenv
load_dotenv()

from typing import Optional, Any

from src.utils.m_log import f_log

import azure.ai.projects as projects
from azure.core.exceptions import ClientAuthenticationError

# Module-level cache to avoid re-initialisation and duplicate logs
_cached_aiproject_client: Optional[projects.AIProjectClient] = None


class AuthManager:
    """Manage Azure authentication.

    Uses DefaultAzureCredential which supports:
    - interactive login (local dev via `az login`)
    - environment-based Service Principal (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
    - managed identity (when running in Azure)
    """

    def get_azure_credential(self) -> Any:
        """Return a DefaultAzureCredential instance.

        Raises ClientAuthenticationError when credentials cannot be created.
        """
        try:
            # Import here to allow tests to monkeypatch azure.identity.DefaultAzureCredential
            from azure.identity import DefaultAzureCredential

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

    This implementation standardizes on `AIProjectClient` from Azure AI Foundry.
    Agents must be passed a single shared `ClientManager` instance at application
    bootstrap and should rely on `get_chat_completions_client()` which strictly
    uses the `AIProjectClient.inference.get_chat_completions_client()` surface.
    """

    def __init__(self, auth: Optional[AuthManager] = None) -> None:
        self.auth = auth or AuthManager()

    def get_aiproject_client(self) -> projects.AIProjectClient:
        """Return an authenticated `AIProjectClient` for Azure AI Foundry.

        Requires `AZURE_AAIF_PROJECT_ENDPOINT` to be set. Raises `RuntimeError`
        if the env var is missing or the client cannot be initialized.
        """
        endpoint = os.getenv("AZURE_AAIF_PROJECT_ENDPOINT")
        if not endpoint:
            raise RuntimeError("No AI Project endpoint configured. Set AZURE_AAIF_PROJECT_ENDPOINT.")

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
            raise

    def get_chat_completions_client(self):
        """Return the chat completions client from the AIProjectClient.

        This strictly requires the `inference.get_chat_completions_client` surface
        on `AIProjectClient`. If unavailable, a RuntimeError is raised — no
        alternate SDKs or fallbacks are permitted by this codebase.
        """
        aiproject = self.get_aiproject_client()

        inference = getattr(aiproject, "inference", None)
        if inference is None:
            raise RuntimeError("AIProjectClient has no 'inference' surface — ensure SDK version supports inference APIs")

        get_client = getattr(inference, "get_chat_completions_client", None)
        if not callable(get_client):
            raise RuntimeError("Inference surface does not expose 'get_chat_completions_client' — SDK mismatch")

        return get_client()


