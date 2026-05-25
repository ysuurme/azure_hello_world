import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- Core Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Azure AI Foundry ---
# The endpoint for the AI Foundry project, e.g., "https://<REGION>.api.azureml.ms"
# This can be the raw endpoint or the full connection string.
AZURE_AAIF_PROJECT_ENDPOINT = os.getenv("AZURE_AAIF_PROJECT_ENDPOINT")

# --- AI Models ---
# Structure allows easy reconfiguration of models cleanly per agent
AGENT_MODELS = {
    "intake_reviewer": "mistral-small-2503",
    "architecture_composer": "Mistral-Large-3",
    "diagram_grill": "Mistral-Large-3",  # critical requirements review — reasoning model
    "diagram_studio": "Codestral-2501",  # D2 code emission — code model
}

# --- Architecture RAG & Design ---
TEMPLATE_PATH = PROJECT_ROOT / "architecture" / "000_architecture_template.md"
SECOND_BRAIN_PATH = os.getenv("SECOND_BRAIN_PATH")
DESIGNS_ARCHIVE_DIR = (
    Path(SECOND_BRAIN_PATH) / "architecture" / "designs" / "approved"
    if SECOND_BRAIN_PATH
    else PROJECT_ROOT / "designs" / "approved"
)

# --- Diagram store (project-scoped working artifacts; ADR-016 project-local) ---
# When AZURE_DIAGRAM_STORAGE_ACCOUNT is set, diagrams persist to Azure Blob
# (container AZURE_DIAGRAM_CONTAINER) via DefaultAzureCredential. When unset the
# store falls back to the local filesystem (CI / offline dev).
DIAGRAM_STORAGE_ACCOUNT = os.getenv("AZURE_DIAGRAM_STORAGE_ACCOUNT")
DIAGRAM_CONTAINER = os.getenv("AZURE_DIAGRAM_CONTAINER", "diagrams")
DIAGRAM_STORE_DIR = PROJECT_ROOT / "designs" / "diagrams"

# --- Executable Engines ---
D2_BINARY_PATH = os.environ.get("D2_BINARY_PATH", "d2")

# --- Logging ---
LOG_PROFILE = "PRD"  # "PRD" | "TEST" | "DEBUG"
LOG_SEPARATOR_WIDTH = 80
LOG_LINE_WIDTH = 120
DIR_LOG = PROJECT_ROOT / "logs"


class _Settings:
    """Simple settings object that reads from environment variables."""

    log_profile: str = os.getenv("LOG_PROFILE", LOG_PROFILE)
    log_separator_width: int = LOG_SEPARATOR_WIDTH
    log_line_width: int = LOG_LINE_WIDTH
    log_dir: Path = DIR_LOG
    port: int = int(os.getenv("PORT", "8080"))
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")


settings = _Settings()

# --- Azure Authentication Mode ---
# Controls whether the app should prefer interactive Azure CLI login (default)
# or explicitly use Service Principal credentials from environment variables.
#
# SUPPORTED VALUES:
#   cli (default) — DefaultAzureCredential prefers `az login`; the cloud runtime
#                   uses the container's User-Assigned Managed Identity (UAMI);
#                   CI uses the OIDC federated credential (ADR-015, issue #68).
#   sp            — MANUAL-ONLY LOCAL PATH. Forces Service Principal credential
#                   lookup via AZURE_CLIENT_ID, AZURE_TENANT_ID, and
#                   AZURE_CLIENT_SECRET. Intended exclusively for local testing
#                   with a manually obtained SP secret — never used by CI or the
#                   cloud runtime, and AZURE_CLIENT_SECRET is never stored in
#                   Terraform state or injected into the container environment.
#
# Empty SP placeholder values in `.env` are silently removed so the `cli` flow
# can continue to work alongside a partially-populated .env file.
AZURE_AUTH_MODE = os.getenv("AZURE_AUTH_MODE", "cli").lower()
USE_AZURE_SERVICE_PRINCIPAL = AZURE_AUTH_MODE in ("sp", "service_principal", "client_secret")
