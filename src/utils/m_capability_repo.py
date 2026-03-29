import os
import yaml
from typing import Dict, Any, List
from src.utils.m_log import f_log
from src.utils.m_ingest import IngestionPipeline

class CapabilityRepository:
    """
    Manages Capability Markdown CRUD operations. 
    Triggers the AI Search Ingestion logic upon modification.
    """
    def __init__(self, storage_path: str = "capabilities") -> None:
        self.storage_path = storage_path
        self.ingester = IngestionPipeline(search_client=None)
        
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def write_capability(self, filename: str, frontmatter: Dict[str, Any], body: str) -> str:
        f_log(f"Writing capability {filename}", c_type="process")
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
        f_log(f"Triggering ingestion for {file_path}", c_type="process")
        # In actual deployment, invoke search ingest logic here
        self.ingester.ingest_local_markdown(self.storage_path)
