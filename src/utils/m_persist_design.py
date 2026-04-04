import os
import time

from src.config import DESIGNS_ARCHIVE_DIR
from src.utils.m_log import f_log


class ArchitecturePersister:
    """
    Saves final documentation and SVGs into long-term history / approved repository directories.
    Renamed to m_persist_design as requested for Single Responsibility clarity.
    """
    def __init__(self, save_path: str = None) -> None:
        self.save_path = save_path or DESIGNS_ARCHIVE_DIR
        if not os.path.exists(self.save_path):
             os.makedirs(self.save_path)
             
    def archive_solution(self, project_name: str, markdown_content: str, svg_bytes: bytes = None) -> str:
        """
        Dumps generated solution to filesystem with timestamp.
        Returns the created directory path.
        """
        safe_name = "".join([c if c.isalnum() else "_" for c in project_name])
        timestamp = str(int(time.time()))
        project_dir = os.path.join(self.save_path, f"{safe_name}_{timestamp}")
        
        os.makedirs(project_dir, exist_ok=True)
        f_log(f"Archiving generated solution to {project_dir}", c_type="process")
        
        # Save Markdown payload
        with open(os.path.join(project_dir, "architecture.md"), "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        # Save SVG payload
        if svg_bytes:
            with open(os.path.join(project_dir, "diagram.svg"), "wb") as f:
                f.write(svg_bytes)
                
        f_log("Archival sequence successful.", c_type="success")
        return project_dir
