from pathlib import Path

import pytest

from src.agents.diagram_studio import ComponentSpec, DiagramBrief, DiagramStyle, RelationshipSpec
from src.utils.m_persist_design import ArchitecturePersister


def _make_brief() -> DiagramBrief:
    return DiagramBrief(
        subject="Test Diagram",
        components=[
            ComponentSpec(name="API", shape="rectangle", group=None),
            ComponentSpec(name="DB", shape="cylinder", group=None),
        ],
        relationships=[
            RelationshipSpec(from_component="API", to_component="DB", label="queries"),
        ],
        layout_direction="right",
        style=DiagramStyle(sketch=True),
    )


class TestPersistDiagram:
    def test_all_three_files_exist(self, tmp_path: Path) -> None:
        persister = ArchitecturePersister(save_path=str(tmp_path))
        diagram_dir = persister.persist_diagram(
            name="test_diagram",
            brief=_make_brief(),
            d2_source="API -> DB: queries",
            svg_bytes=b"<svg><text>test</text></svg>",
        )

        assert (diagram_dir / "brief.md").exists()
        assert (diagram_dir / "source.d2").exists()
        assert (diagram_dir / "render.svg").exists()

    def test_directory_is_under_diagrams_subdir(self, tmp_path: Path) -> None:
        persister = ArchitecturePersister(save_path=str(tmp_path))
        diagram_dir = persister.persist_diagram(
            name="my_diagram",
            brief=_make_brief(),
            d2_source="A -> B",
            svg_bytes=b"<svg/>",
        )

        assert diagram_dir.parent == tmp_path / "diagrams"

    def test_brief_md_contains_subject(self, tmp_path: Path) -> None:
        persister = ArchitecturePersister(save_path=str(tmp_path))
        diagram_dir = persister.persist_diagram(
            name="subject_check",
            brief=_make_brief(),
            d2_source="A -> B",
            svg_bytes=b"<svg/>",
        )

        content = (diagram_dir / "brief.md").read_text(encoding="utf-8")
        assert "Test Diagram" in content

    def test_source_d2_contains_code(self, tmp_path: Path) -> None:
        persister = ArchitecturePersister(save_path=str(tmp_path))
        d2 = "API -> DB: queries"
        diagram_dir = persister.persist_diagram(
            name="d2_check",
            brief=_make_brief(),
            d2_source=d2,
            svg_bytes=b"<svg/>",
        )

        assert (diagram_dir / "source.d2").read_text(encoding="utf-8") == d2

    def test_render_svg_contains_bytes(self, tmp_path: Path) -> None:
        persister = ArchitecturePersister(save_path=str(tmp_path))
        svg = b"<svg><rect/></svg>"
        diagram_dir = persister.persist_diagram(
            name="svg_check",
            brief=_make_brief(),
            d2_source="A -> B",
            svg_bytes=svg,
        )

        assert (diagram_dir / "render.svg").read_bytes() == svg

    def test_persistence_failure_is_logged_and_reraised(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        persister = ArchitecturePersister(save_path=str(tmp_path))
        with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                persister.persist_diagram(
                    name="fail_test",
                    brief=_make_brief(),
                    d2_source="A -> B",
                    svg_bytes=b"<svg/>",
                )
