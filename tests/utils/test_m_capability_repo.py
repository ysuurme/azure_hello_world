import os
from unittest.mock import patch

import pytest

from src.utils.m_capability_repo import CapabilityRepository


def test_capability_repository_init_creates_dir(tmp_path):
    storage_path = tmp_path / "test_caps"
    assert not storage_path.exists()

    # Disable ingestion pipeline initialization inside init to isolate test
    with patch("src.utils.m_capability_repo.IngestionPipeline"):
        repo = CapabilityRepository(storage_path=str(storage_path))

    assert os.path.exists(repo.storage_path)


def test_write_capability_writes_file_and_triggers_ingestion(tmp_path):
    storage_path = tmp_path / "test_caps"

    with patch("src.utils.m_capability_repo.IngestionPipeline") as mock_pipeline:
        mock_pipeline_instance = mock_pipeline.return_value
        repo = CapabilityRepository(storage_path=str(storage_path))

        frontmatter = {"title": "Test Cap", "author": "Agent"}
        body = "This is the body of the capability."
        filename = "test_cap.md"

        full_path = repo.write_capability(filename, frontmatter, body)

        assert os.path.exists(full_path)
        with open(full_path, encoding="utf-8") as f:
            content = f.read()

        assert "title: Test Cap" in content
        assert "author: Agent" in content
        assert body in content

        # Verify ingestion was triggered
        mock_pipeline_instance.ingest_local_markdown.assert_called_once_with(str(storage_path))


def test_default_path_uses_second_brain_capabilities_when_set(tmp_path, monkeypatch):
    caps_path = tmp_path / "capabilities"
    caps_path.mkdir()

    monkeypatch.setattr("src.utils.m_capability_repo.SECOND_BRAIN_PATH", str(tmp_path))

    with patch("src.utils.m_capability_repo.IngestionPipeline"):
        repo = CapabilityRepository()

    assert repo.storage_path == str(caps_path)


def test_default_path_falls_back_to_project_root_without_second_brain(tmp_path, monkeypatch):
    monkeypatch.setattr("src.utils.m_capability_repo.SECOND_BRAIN_PATH", None)
    monkeypatch.setattr("src.utils.m_capability_repo.PROJECT_ROOT", tmp_path)

    with patch("src.utils.m_capability_repo.IngestionPipeline"):
        repo = CapabilityRepository()

    assert repo.storage_path == str(tmp_path / "capabilities")


def test_environment_error_when_second_brain_capabilities_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("src.utils.m_capability_repo.SECOND_BRAIN_PATH", str(tmp_path))
    # tmp_path/capabilities does not exist

    with patch("src.utils.m_capability_repo.IngestionPipeline"):
        with pytest.raises(OSError, match="does not exist on disk"):
            CapabilityRepository()
