from unittest.mock import MagicMock, patch

from src.agents.diagram_studio import DiagramStudioModule, ModuleResponse


def _make_client_manager(d2_output: str = "A -> B") -> MagicMock:
    """Return a mocked ClientManager whose LLM returns d2_output inside a code block."""

    class _FakeResponse:
        output_text = f"```d2\n{d2_output}\n```"

    class _FakeResponses:
        def create(self, model, input):
            return _FakeResponse()

    class _FakeOpenAI:
        responses = _FakeResponses()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    cm = MagicMock()
    cm.get_openai_client.return_value = _FakeOpenAI()
    return cm


class TestDiagramStudioModuleContract:
    def test_module_attributes_are_correct(self):
        module = DiagramStudioModule(client_manager=MagicMock())
        assert module.name == "Diagram Studio"
        assert module.slash_command == "/diagram"
        assert module.description

    def test_handle_returns_module_response(self):
        module = DiagramStudioModule(client_manager=_make_client_manager())
        with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
            mock_cls.return_value.generate_svg.return_value = b"<svg/>"
            result = module.handle("/diagram A connects to B", {})
        assert isinstance(result, ModuleResponse)


class TestSingleShotD2Generation:
    def test_handle_includes_d2_code_in_response_text(self):
        module = DiagramStudioModule(client_manager=_make_client_manager("A -> B"))
        with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
            mock_cls.return_value.generate_svg.return_value = b"<svg/>"
            result = module.handle("/diagram A connects to B", {})
        assert "A -> B" in result.response_text

    def test_handle_sets_d2_artifact(self):
        module = DiagramStudioModule(client_manager=_make_client_manager("X -> Y"))
        with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
            mock_cls.return_value.generate_svg.return_value = b"<svg/>"
            result = module.handle("/diagram X to Y", {})
        assert "d2" in result.artifacts
        assert "X -> Y" in result.artifacts["d2"]

    def test_handle_sets_svg_artifact_when_engine_succeeds(self):
        module = DiagramStudioModule(client_manager=_make_client_manager())
        with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
            mock_cls.return_value.generate_svg.return_value = b"<svg/>"
            result = module.handle("/diagram test", {})
        assert "svg" in result.artifacts
        assert result.artifacts["svg"] == b"<svg/>"

    def test_handle_omits_svg_artifact_when_engine_returns_none(self):
        module = DiagramStudioModule(client_manager=_make_client_manager())
        with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
            mock_cls.return_value.generate_svg.return_value = None
            result = module.handle("/diagram test", {})
        assert "svg" not in result.artifacts

    def test_handle_status_completed_on_success(self):
        module = DiagramStudioModule(client_manager=_make_client_manager())
        with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
            mock_cls.return_value.generate_svg.return_value = b"<svg/>"
            result = module.handle("/diagram test", {})
        assert result.status == "completed"

    def test_handle_status_error_when_no_d2_generated(self):
        module = DiagramStudioModule(client_manager=_make_client_manager())
        with patch.object(module, "_generate_d2", return_value=None):
            result = module.handle("/diagram empty", {})
        assert result.status == "error"

    def test_description_stripped_from_slash_command(self):
        captured: dict = {}

        def fake_generate(description: str) -> str:
            captured["desc"] = description
            return "A -> B"

        module = DiagramStudioModule(client_manager=_make_client_manager())
        with patch.object(module, "_generate_d2", side_effect=fake_generate):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                module.handle("/diagram medallion architecture", {})

        assert captured["desc"] == "medallion architecture"


class TestSketchFlagForwarding:
    def test_sketch_true_forwarded_to_engine(self):
        module = DiagramStudioModule(client_manager=_make_client_manager("A -> B"))
        with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
            mock_engine = MagicMock()
            mock_engine.generate_svg.return_value = b"<svg/>"
            mock_cls.return_value = mock_engine
            module.handle("/diagram a test diagram", {})

        mock_engine.generate_svg.assert_called_once()
        _, kwargs = mock_engine.generate_svg.call_args
        assert kwargs.get("sketch") is True
