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
    "intake_reviewer": "gpt-5-mini",
    "architecture_composer": "DeepSeek-V3.1",
    "diagram_studio": "gpt-5-mini",
}

# --- Architecture RAG & Design ---
TEMPLATE_PATH = PROJECT_ROOT / "architecture" / "000_architecture_template.md"
SECOND_BRAIN_PATH = os.getenv("SECOND_BRAIN_PATH")
DESIGNS_ARCHIVE_DIR = (
    Path(SECOND_BRAIN_PATH) / "architecture" / "designs" / "approved"
    if SECOND_BRAIN_PATH
    else PROJECT_ROOT / "designs" / "approved"
)

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
# Set `AZURE_AUTH_MODE=sp` or `AZURE_AUTH_MODE=service_principal` to force
# service-principal usage via `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and
# `AZURE_CLIENT_SECRET`. Default is `cli` which allows `az login` to be used
# when available; empty SP placeholders in `.env` will be ignored so CLI can
# continue to work locally.
AZURE_AUTH_MODE = os.getenv("AZURE_AUTH_MODE", "cli").lower()
USE_AZURE_SERVICE_PRINCIPAL = AZURE_AUTH_MODE in ("sp", "service_principal", "client_secret")
