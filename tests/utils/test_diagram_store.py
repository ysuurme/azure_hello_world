from pathlib import Path
from unittest.mock import MagicMock

from src.utils.m_diagram_store import (
    BlobDiagramStore,
    FilesystemDiagramStore,
    get_diagram_store,
    slugify,
)


class TestSlugify:
    def test_lowercases_and_hyphenates(self):
        assert slugify("Payment Service Architecture") == "payment-service-architecture"

    def test_strips_punctuation_and_edges(self):
        assert slugify("  My!! Diagram??  ") == "my-diagram"

    def test_empty_falls_back(self):
        assert slugify("") == "diagram"

    def test_truncates_long_subjects(self):
        assert len(slugify("x" * 100)) <= 48


class TestFilesystemDiagramStore:
    def _brief(self, subject: str = "Payment Service") -> dict:
        return {"subject": subject, "components": [], "relationships": []}

    def test_save_then_load_round_trip(self, tmp_path: Path):
        store = FilesystemDiagramStore(root=tmp_path)
        slug = store.save(self._brief(), "A -> B", b"<svg/>")
        assert slug == "payment-service"

        record = store.load(slug)
        assert record is not None
        assert record.brief["subject"] == "Payment Service"
        assert record.d2 == "A -> B"
        assert record.svg == b"<svg/>"

    def test_save_overwrites_same_slug(self, tmp_path: Path):
        store = FilesystemDiagramStore(root=tmp_path)
        store.save(self._brief(), "v1", b"<svg/>")
        store.save(self._brief(), "v2", b"<svg/>")
        assert store.load("payment-service").d2 == "v2"

    def test_list_returns_summaries(self, tmp_path: Path):
        store = FilesystemDiagramStore(root=tmp_path)
        store.save(self._brief("Alpha"), "x", b"<svg/>")
        store.save(self._brief("Beta"), "y", b"<svg/>")
        subjects = {s.subject for s in store.list()}
        assert subjects == {"Alpha", "Beta"}

    def test_list_empty_when_no_root(self, tmp_path: Path):
        store = FilesystemDiagramStore(root=tmp_path / "does-not-exist")
        assert store.list() == []

    def test_load_missing_returns_none(self, tmp_path: Path):
        store = FilesystemDiagramStore(root=tmp_path)
        assert store.load("nope") is None

    def test_delete_removes_and_reports(self, tmp_path: Path):
        store = FilesystemDiagramStore(root=tmp_path)
        store.save(self._brief(), "A -> B", b"<svg/>")
        assert store.delete("payment-service") is True
        assert store.load("payment-service") is None

    def test_delete_missing_returns_false(self, tmp_path: Path):
        store = FilesystemDiagramStore(root=tmp_path)
        assert store.delete("nope") is False


class TestStoreFactory:
    def test_returns_filesystem_when_no_account(self, monkeypatch):
        monkeypatch.setattr("src.config.DIAGRAM_STORAGE_ACCOUNT", None)
        assert isinstance(get_diagram_store(), FilesystemDiagramStore)

    def test_returns_blob_when_account_configured(self, monkeypatch):
        monkeypatch.setattr("src.config.DIAGRAM_STORAGE_ACCOUNT", "sthelloarchdev")
        monkeypatch.setattr("src.config.DIAGRAM_CONTAINER", "diagrams")
        store = get_diagram_store(credential=MagicMock())
        assert isinstance(store, BlobDiagramStore)
