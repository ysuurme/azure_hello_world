from unittest.mock import MagicMock, patch

from src.utils.m_diagram_engine import DiagramEngine
from src.utils.m_diagram_style import DiagramStyle


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
