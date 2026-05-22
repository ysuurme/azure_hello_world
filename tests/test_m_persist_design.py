from pathlib import Path

import pytest

from src.utils.m_persist_design import ArchitecturePersister


class TestArchitecturePersister:
    def test_archive_writes_markdown_and_svg(self, tmp_path: Path) -> None:
        persister = ArchitecturePersister(save_path=str(tmp_path))
        project_dir = persister.archive_solution(
            project_name="smoke_test",
            markdown_content="# Architecture",
            svg_bytes=b"<svg></svg>",
        )

        assert (Path(project_dir) / "architecture.md").exists()
        assert (Path(project_dir) / "diagram.svg").exists()

    def test_archive_path_uses_second_brain_when_set(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        second_brain = tmp_path / "second_brain"
        monkeypatch.setenv("SECOND_BRAIN_PATH", str(second_brain))

        import importlib

        import src.config as cfg

        importlib.reload(cfg)

        expected_dir = second_brain / "architecture" / "designs" / "approved"
        assert cfg.DESIGNS_ARCHIVE_DIR == expected_dir

    def test_archive_path_falls_back_without_second_brain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SECOND_BRAIN_PATH", raising=False)

        import importlib

        import src.config as cfg

        importlib.reload(cfg)

        assert cfg.DESIGNS_ARCHIVE_DIR == cfg.PROJECT_ROOT / "designs" / "approved"
