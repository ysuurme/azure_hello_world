import shutil
from unittest.mock import MagicMock, patch

import pytest

from src.utils.m_diagram_engine import DiagramEngine
from src.utils.m_diagram_style import DiagramStyle

_D2_AVAILABLE = shutil.which("d2") is not None

_NESTED_CONTAINER_D2 = """\
direction: down
services: "Services" {
  api: "API Gateway"
  api.class: service
  workers: "Workers" {
    worker_a: "Worker A"
    worker_a.class: service
    worker_b: "Worker B"
    worker_b.class: service
  }
}
storage: "Storage" {
  db: "Database"
  db.class: datastore
  cache: "Cache"
  cache.class: datastore
}
services.api -> services.workers.worker_a: dispatch
services.workers.worker_a -> storage.db: write
services.workers.worker_b -> storage.cache: read
"""


def _capture_run(captured: dict):
    """subprocess.run mock that records argv and writes a dummy SVG to the output file (last arg)."""

    def mock_run(cmd, *args, **kwargs):
        captured["cmd"] = list(cmd)
        with open(cmd[-1], "wb") as f:
            f.write(b"<svg></svg>")
        return MagicMock(returncode=0)

    return mock_run


class TestStyleApplication:
    def test_sketch_flag_present_when_style_sketch_true(self):
        captured: dict = {}
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=_capture_run(captured)):
            DiagramEngine().generate_svg("A -> B", style=DiagramStyle(sketch=True))
        assert "--sketch" in captured["cmd"]

    def test_sketch_flag_absent_when_style_sketch_false(self):
        captured: dict = {}
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=_capture_run(captured)):
            DiagramEngine().generate_svg("A -> B", style=DiagramStyle(sketch=False))
        assert "--sketch" not in captured["cmd"]

    def test_sketch_defaults_to_true_from_default_style(self):
        captured: dict = {}
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=_capture_run(captured)):
            DiagramEngine().generate_svg("A -> B")
        assert "--sketch" in captured["cmd"]

    def test_theme_and_pad_applied_from_style(self):
        captured: dict = {}
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=_capture_run(captured)):
            DiagramEngine().generate_svg("A -> B", style=DiagramStyle(theme=5, pad=33))
        cmd = captured["cmd"]
        assert cmd[cmd.index("--theme") + 1] == "5"
        assert cmd[cmd.index("--pad") + 1] == "33"

    def test_layout_engine_default_is_elk(self):
        captured: dict = {}
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=_capture_run(captured)):
            DiagramEngine().generate_svg("A -> B")
        cmd = captured["cmd"]
        assert cmd[cmd.index("--layout") + 1] == "elk"

    def test_layout_engine_sourced_from_style(self):
        captured: dict = {}
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=_capture_run(captured)):
            DiagramEngine().generate_svg("A -> B", style=DiagramStyle(layout_engine="dagre"))
        cmd = captured["cmd"]
        assert cmd[cmd.index("--layout") + 1] == "dagre"

    def test_layout_flag_always_present_in_cli_call(self):
        captured: dict = {}
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=_capture_run(captured)):
            DiagramEngine().generate_svg("A -> B", style=DiagramStyle(sketch=False))
        assert "--layout" in captured["cmd"]

    def test_renders_d2_as_is(self):
        captured: dict = {}

        def mock_run(cmd, *args, **kwargs):
            with open(cmd[-2], encoding="utf-8") as f:  # input file is second-to-last
                captured["d2"] = f.read()
            with open(cmd[-1], "wb") as f:
                f.write(b"<svg></svg>")
            return MagicMock(returncode=0)

        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=mock_run):
            DiagramEngine().generate_svg("foo -> bar")

        assert captured["d2"] == "foo -> bar"


@pytest.mark.integration
@pytest.mark.skipif(not _D2_AVAILABLE, reason="D2 binary not installed; run inside the container or install D2 locally")
class TestELKSmoke:
    """Calls the real D2 binary to confirm ELK renders nested-container diagrams without error.

    Run locally:  uv run pytest -m integration
    Run in-container: docker exec <container> uv run pytest -m integration
    """

    def test_elk_renders_nested_container_to_svg(self):
        """ELK must produce non-empty SVG from a blocks-in-blocks diagram with ancestor→descendant edges."""
        svg = DiagramEngine().generate_svg(_NESTED_CONTAINER_D2, style=DiagramStyle(layout_engine="elk"))
        assert svg is not None, "generate_svg returned None — D2/ELK binary error"
        assert len(svg) > 0
        assert b"<svg" in svg

    def test_elk_is_default_in_generated_output(self):
        """DiagramStyle default (elk) must produce valid SVG without caller specifying layout_engine."""
        svg = DiagramEngine().generate_svg(_NESTED_CONTAINER_D2)
        assert svg is not None, "generate_svg returned None with default DiagramStyle"
        assert b"<svg" in svg
