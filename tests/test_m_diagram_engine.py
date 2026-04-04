from src.utils.m_diagram_engine import DiagramEngine


class TestDiagramEngine:
    def test_generate_svg_success(self):
        """
        Tests that valid D2 syntax produces a valid SVG output.
        """
        engine = DiagramEngine()
        d2_syntax = "direction: right; User -> Agent"
        svg_bytes = engine.generate_svg(d2_syntax)
        
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
