from unittest.mock import patch

from src.utils.m_search import knowledge_base_retrieve


def test_knowledge_base_retrieve_returns_default_when_no_match(tmp_path):
    """Covers lines 28-29: no files match the query, returns default WAF guidance."""
    cap_dir = tmp_path / "capabilities"
    cap_dir.mkdir()
    md_file = cap_dir / "capability.md"
    md_file.write_text("This content has nothing relevant.", encoding="utf-8")

    with patch("src.utils.m_search.PROJECT_ROOT", tmp_path):
        results = knowledge_base_retrieve("zzznomatchzzz")

    assert len(results) == 1
    assert results[0]["id"] == "default-waf"
    assert "WAF" in results[0]["content"]


def test_knowledge_base_retrieve_handles_file_read_error(tmp_path):
    """Covers lines 24-25: file read raises an exception, error is logged and skipped."""
    cap_dir = tmp_path / "capabilities"
    cap_dir.mkdir()
    md_file = cap_dir / "bad_file.md"
    md_file.write_text("some content", encoding="utf-8")

    with patch("src.utils.m_search.PROJECT_ROOT", tmp_path):
        with patch("pathlib.Path.read_text", side_effect=OSError("permission denied")):
            results = knowledge_base_retrieve("some")

    # Should fall through to default result without raising
    assert isinstance(results, list)
    assert results[0]["id"] == "default-waf"
