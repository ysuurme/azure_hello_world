import os
from pathlib import Path

# --- Core Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- AI Models ---
# Structure allows easy reconfiguration of models cleanly per agent
AGENT_MODELS = {
    "intake_reviewer": "gpt-4o-mini",
    "architecture_composer": "DeepSeek-V3.1"
}

# --- Architecture RAG & Design ---
TEMPLATE_PATH = PROJECT_ROOT / "architecture" / "architecture_template.md"
DESIGNS_ARCHIVE_DIR = PROJECT_ROOT / "designs" / "approved"

# --- Executable Engines ---
D2_BINARY_PATH = os.environ.get("D2_BINARY_PATH", "d2")

# --- Logging ---
LOG_PROFILE = "PRD"          # "PRD" | "TEST" | "DEBUG"
LOG_SEPARATOR_WIDTH = 80
LOG_LINE_WIDTH = 120
DIR_LOG = PROJECT_ROOT / "logs"
