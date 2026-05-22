from unittest.mock import patch, MagicMock
from src.utils.m_diagram_engine import DiagramEngine


class TestDiagramEngine:
    def test_generate_svg_success(self):
        """
        Tests that valid D2 syntax produces a valid SVG output.
        """
        engine = DiagramEngine()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b'<svg xmlns="http://www.w3.org/2000/svg"><text>User</text><text>Agent</text></svg>'

        with patch("src.utils.m_diagram_engine.subprocess.run", return_value=mock_result):
            svg_bytes = engine.generate_svg("direction: right; User -> Agent")

        assert svg_bytes is not None
        assert b"<svg" in svg_bytes
        assert b"User" in svg_bytes
        assert b"Agent" in svg_bytes

    def test_generate_svg_invalid_syntax(self):
        """
        Tests that invalid D2 syntax returns None gracefully.
        """
        engine = DiagramEngine()
        d2_syntax = "invalid syntax {{"
        svg_bytes = engine.generate_svg(d2_syntax)

        assert svg_bytes is None

    def test_binary_not_found(self):
        """
        Tests the failure path when the D2 binary is not available.
        """
        engine = DiagramEngine(binary_path="/non/existent/path/to/d2")
        d2_syntax = "User -> Agent"
        svg_bytes = engine.generate_svg(d2_syntax)

        assert svg_bytes is None
