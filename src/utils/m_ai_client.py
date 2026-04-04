import os
from typing import Any

import azure.ai.projects as projects
from azure.core.exceptions import ClientAuthenticationError
from dotenv import load_dotenv

import src.config as config
from src.utils.m_log import f_log

load_dotenv()

# Module-level cache to avoid re-initialisation and duplicate logs
_cached_aiproject_client: projects.AIProjectClient | None = None


class _AuthManager:
    """Manage Azure authentication.

    Uses DefaultAzureCredential which supports:
    - interactive login (local dev via `az login`)
    - environment-based Service Principal (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
    - managed identity (when running in Azure)
    """

    def __init__(self) -> None:
        self._cached_credential: Any = None

    def get_azure_credential(self) -> Any:
        """Return a DefaultAzureCredential instance (cached).

        Raises ClientAuthenticationError when credentials cannot be created.
        """
        if self._cached_credential is not None:
            return self._cached_credential

        try:
            # If the app is configured to *explicitly* use a service principal,
            # require the SP env vars to be present and non-empty. Otherwise,
            # remove empty SP placeholders so DefaultAzureCredential can fall
            # back to other credential types (e.g., Azure CLI `az login`).
            if config.USE_AZURE_SERVICE_PRINCIPAL:
                missing = [v for v in ("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_SECRET") if not os.getenv(v)]
                if missing:
                    raise RuntimeError(
                        f"AZURE_AUTH_MODE is set to service principal but missing env vars: {', '.join(missing)}"
                    )
            else:
                for _v in ("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_SECRET"):
                    _val = os.getenv(_v)
                    if _val is not None and _val.strip() == "":
                        os.environ.pop(_v, None)
                        f_log(f"Removed empty env var {_v} to allow DefaultAzureCredential fallback.", c_type="debug")

            # Import here to allow tests to monkeypatch azure.identity.DefaultAzureCredential
            from azure.identity import DefaultAzureCredential

            cred = DefaultAzureCredential()
            f_log("Created DefaultAzureCredential.", c_type="debug")
            self._cached_credential = cred
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
    bootstrap and should rely on `get_openai_client()` which yields the
    OpenAI-style client from `AIProjectClient.get_openai_client()`.
    """

    def __init__(self) -> None:
        self._auth = _AuthManager()

    def get_credential(self) -> Any:
        """Return the shared credential from the internal AuthManager."""
        return self._auth.get_azure_credential()

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
        cred = self.get_credential()

        try:
            # Handle potential connection strings by extracting the endpoint
            # In AIProjectClient 2.0.1, constructor expects `endpoint` as first arg.
            clean_endpoint = endpoint
            if ";" in endpoint:
                # Basic parsing: find endpoint=...
                for part in endpoint.split(";"):
                    if part.strip().startswith("endpoint="):
                        clean_endpoint = part.split("=", 1)[1].strip()
                        break
            
            clean_endpoint = clean_endpoint.replace("endpoint=", "").strip()
            
            client = projects.AIProjectClient(endpoint=clean_endpoint, credential=cred)
            _cached_aiproject_client = client
            f_log("AIProjectClient initialized.", c_type="success")
            return client
        except Exception as e:
            f_log(f"Failed to initialize AIProjectClient: {e}", c_type="error")
            raise

    def get_openai_client(self):
        """Return an OpenAI-style client from the AIProjectClient.

        This yields the client returned by `AIProjectClient.get_openai_client()` and
        should be used as a context manager:

            with client_manager.get_openai_client() as openai_client:
                resp = openai_client.responses.create(...)

        Raises RuntimeError if the AIProjectClient does not expose `get_openai_client`.
        """
        aiproject = self.get_aiproject_client()
        get_client = getattr(aiproject, "get_openai_client", None)
        if not callable(get_client):
            raise RuntimeError(
                "AIProjectClient does not expose 'get_openai_client' "
                "— update SDK or use a different surface"
            )
        return get_client()
