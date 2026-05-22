from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.config import DESIGNS_ARCHIVE_DIR
from src.utils.m_log import f_log

if TYPE_CHECKING:
    from src.agents.diagram_studio import DiagramBrief


def _brief_to_markdown(brief: DiagramBrief) -> str:
    subject = getattr(brief, "subject", "") or "Diagram Brief"
    lines = [
        f"# {subject}",
        "",
        "## Metadata",
        "",
        "| Property | Value |",
        "|----------|-------|",
        f"| Subject | {subject} |",
        f"| Layout Direction | {getattr(brief, 'layout_direction', 'right')} |",
        f"| Sketch | {getattr(getattr(brief, 'style', None), 'sketch', True)} |",
        "",
        "## Components",
        "",
        "| Name | Shape | Group |",
        "|------|-------|-------|",
    ]
    for c in getattr(brief, "components", []):
        lines.append(f"| {c.name} | {c.shape} | {c.group or ''} |")
    lines += [
        "",
        "## Relationships",
        "",
        "| From | To | Label |",
        "|------|----|-------|",
    ]
    for r in getattr(brief, "relationships", []):
        lines.append(f"| {r.from_component} | {r.to_component} | {r.label or ''} |")
    return "\n".join(lines)


class ArchitecturePersister:
    """Persists approved artefacts (architecture markdown, SVGs, diagram trios) to the designs/ directory."""

    def __init__(self, save_path: str = None) -> None:
        self.save_path = save_path or DESIGNS_ARCHIVE_DIR
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    def archive_solution(self, project_name: str, markdown_content: str, svg_bytes: bytes = None) -> str:
        """Dumps generated solution to filesystem with timestamp. Returns the created directory path."""
        safe_name = "".join([c if c.isalnum() else "_" for c in project_name])
        timestamp = str(int(time.time()))
        project_dir = os.path.join(self.save_path, f"{safe_name}_{timestamp}")

        os.makedirs(project_dir, exist_ok=True)
        f_log(f"Archiving generated solution to {project_dir}", level="process")

        with open(os.path.join(project_dir, "architecture.md"), "w", encoding="utf-8") as f:
            f.write(markdown_content)

        if svg_bytes:
            with open(os.path.join(project_dir, "diagram.svg"), "wb") as f:
                f.write(svg_bytes)

        f_log("Archival sequence successful.", level="success")
        return project_dir

    def persist_diagram(self, name: str, brief: DiagramBrief, d2_source: str, svg_bytes: bytes) -> Path:
        """Writes brief.md, source.d2, and render.svg under diagrams/<name>_<timestamp>/. Re-raises on failure."""
        timestamp = str(int(time.time()))
        diagram_dir = Path(self.save_path) / "diagrams" / f"{name}_{timestamp}"
        try:
            diagram_dir.mkdir(parents=True, exist_ok=True)
            f_log(f"Persisting diagram trio to {diagram_dir}", level="process")
            (diagram_dir / "brief.md").write_text(_brief_to_markdown(brief), encoding="utf-8")
            (diagram_dir / "source.d2").write_text(d2_source, encoding="utf-8")
            (diagram_dir / "render.svg").write_bytes(svg_bytes)
            f_log("Diagram trio persisted successfully.", level="success")
        except Exception as e:
            f_log(f"Diagram persistence failed: {e}", level="error")
            raise
        return diagram_dir
