from unittest.mock import MagicMock, patch

from src.utils.m_diagram_engine import DiagramEngine


def _make_subprocess_mock(output_file_index: int = 2):
    """Return a subprocess.run mock that writes a dummy SVG to the output file."""

    def mock_run(cmd, *args, **kwargs):
        with open(cmd[output_file_index], "wb") as f:
            f.write(b"<svg></svg>")
        return MagicMock(returncode=0)

    return mock_run


class TestSketchFlag:
    def test_sketch_flag_present_when_true(self):
        captured: dict = {}

        def mock_run(cmd, *args, **kwargs):
            captured["cmd"] = list(cmd)
            with open(cmd[2], "wb") as f:
                f.write(b"<svg></svg>")
            return MagicMock(returncode=0)

        engine = DiagramEngine()
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=mock_run):
            engine.generate_svg("A -> B", sketch=True)

        assert "--sketch" in captured["cmd"]

    def test_sketch_flag_absent_when_false(self):
        captured: dict = {}

        def mock_run(cmd, *args, **kwargs):
            captured["cmd"] = list(cmd)
            with open(cmd[2], "wb") as f:
                f.write(b"<svg></svg>")
            return MagicMock(returncode=0)

        engine = DiagramEngine()
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=mock_run):
            engine.generate_svg("A -> B", sketch=False)

        assert "--sketch" not in captured["cmd"]

    def test_sketch_defaults_to_true(self):
        captured: dict = {}

        def mock_run(cmd, *args, **kwargs):
            captured["cmd"] = list(cmd)
            with open(cmd[2], "wb") as f:
                f.write(b"<svg></svg>")
            return MagicMock(returncode=0)

        engine = DiagramEngine()
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=mock_run):
            engine.generate_svg("A -> B")

        assert "--sketch" in captured["cmd"]

    def test_sketch_flag_position_after_output_file(self):
        captured: dict = {}

        def mock_run(cmd, *args, **kwargs):
            captured["cmd"] = list(cmd)
            with open(cmd[2], "wb") as f:
                f.write(b"<svg></svg>")
            return MagicMock(returncode=0)

        engine = DiagramEngine()
        with patch("src.utils.m_diagram_engine.subprocess.run", side_effect=mock_run):
            engine.generate_svg("A -> B", sketch=True)

        cmd = captured["cmd"]
        sketch_idx = cmd.index("--sketch")
        assert sketch_idx > 2
