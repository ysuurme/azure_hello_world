import os
from pathlib import Path
from typing import Any

import yaml

from src.config import PROJECT_ROOT, SECOND_BRAIN_PATH
from src.utils.m_ingest import IngestionPipeline
from src.utils.m_log import f_log


def _resolve_default_path() -> Path:
    if SECOND_BRAIN_PATH:
        path = Path(SECOND_BRAIN_PATH) / "capabilities"
        if not path.exists():
            raise OSError(f"SECOND_BRAIN_PATH is set to '{SECOND_BRAIN_PATH}' but '{path}' does not exist on disk.")
        return path
    return PROJECT_ROOT / "capabilities"


class CapabilityRepository:
    """
    Manages Capability Markdown CRUD operations.
    Triggers the AI Search Ingestion logic upon modification.
    """

    def __init__(self, storage_path: str | None = None) -> None:
        if storage_path is None:
            storage_path = str(_resolve_default_path())

        self.storage_path = storage_path
        self.ingester = IngestionPipeline(search_client=None)

        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def write_capability(self, filename: str, frontmatter: dict[str, Any], body: str) -> str:
        f_log(f"Writing capability {filename}", level="process")
        full_path = os.path.join(self.storage_path, filename)

        yaml_content = yaml.dump(frontmatter, sort_keys=False)
        content = f"---\n{yaml_content}---\n\n{body}"

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        self._trigger_ingestion(full_path)
        return full_path

    def _trigger_ingestion(self, file_path: str) -> None:
        """
        Idempotent sync hook to Azure AI Search.
        """
        f_log(f"Triggering ingestion for {file_path}", level="process")
        # In actual deployment, invoke search ingest logic here
        self.ingester.ingest_local_markdown(self.storage_path)
