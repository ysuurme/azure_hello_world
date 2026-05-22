from unittest.mock import MagicMock, patch

from src.agents._refinement import GrillQuestion, GrillRound
from src.agents.diagram_studio import DiagramBrief, DiagramStudioModule, ModuleResponse


def _make_module() -> DiagramStudioModule:
    return DiagramStudioModule(client_manager=MagicMock())


def _grill_incomplete() -> GrillRound:
    return GrillRound(
        questions=[
            GrillQuestion(
                question="What are the main components of the system?",
                recommendation="List 2-3 key services (e.g. API Gateway, Backend, Database)",
            ),
            GrillQuestion(
                question="What is the primary data flow direction?",
                recommendation="Left-to-right is standard for request/response flows",
            ),
        ],
        updated_brief={"subject": "My System", "components": [], "relationships": [], "complete": False},
        complete=False,
    )


def _grill_complete() -> GrillRound:
    return GrillRound(
        questions=[],
        updated_brief={
            "subject": "API System",
            "components": [
                {"name": "API Gateway", "shape": "rectangle", "group": None},
                {"name": "Backend", "shape": "rectangle", "group": None},
                {"name": "Database", "shape": "cylinder", "group": None},
            ],
            "relationships": [
                {"from_component": "API Gateway", "to_component": "Backend", "label": "routes"},
                {"from_component": "Backend", "to_component": "Database", "label": "queries"},
            ],
            "layout_direction": "right",
            "complete": True,
        },
        complete=True,
    )


class TestModuleContract:
    def test_module_attributes_are_correct(self):
        module = _make_module()
        assert module.name == "Diagram Studio"
        assert module.slash_command == "/diagram"
        assert module.description

    def test_brief_class_is_diagram_brief(self):
        assert DiagramStudioModule.brief_class is DiagramBrief

    def test_handle_returns_module_response(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            result = module.handle("/diagram a thing with boxes", {})
        assert isinstance(result, ModuleResponse)


class TestFirstTurnGrillRound:
    def test_underspecified_description_returns_in_refinement(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            result = module.handle("/diagram a thing with some boxes", {})
        assert result.status == "in_refinement"

    def test_grill_response_contains_questions(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            result = module.handle("/diagram a thing", {})
        assert "Q1" in result.response_text

    def test_each_question_has_recommendation(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            result = module.handle("/diagram a thing", {})
        assert "Recommended" in result.response_text

    def test_updated_state_has_grilling_phase(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            result = module.handle("/diagram a thing", {})
        assert result.updated_state.get("phase") == "grilling"

    def test_no_artifacts_on_grill_round(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            result = module.handle("/diagram a thing", {})
        assert result.artifacts == {}

    def test_description_stripped_from_slash_command(self):
        captured: dict = {}
        module = _make_module()

        def capture_grill(description: str, partial_brief: dict) -> GrillRound:
            captured["description"] = description
            return _grill_incomplete()

        with patch.object(module, "grill_round", side_effect=capture_grill):
            module.handle("/diagram medallion architecture", {})

        assert captured["description"] == "medallion architecture"


class TestRichDescriptionCompletedInFirstRound:
    def test_rich_description_returns_completed(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                    result = module.handle("/diagram API connects to Database with a query", {})
        assert result.status == "completed"

    def test_rich_description_has_d2_artifact(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                    result = module.handle("/diagram a detailed system", {})
        assert "d2" in result.artifacts
        assert result.artifacts["d2"] == "A -> B"

    def test_rich_description_has_svg_artifact(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                    result = module.handle("/diagram a detailed system", {})
        assert "svg" in result.artifacts
        assert result.artifacts["svg"] == b"<svg/>"

    def test_rich_description_no_svg_when_engine_fails(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = None
                    result = module.handle("/diagram a detailed system", {})
        assert "svg" not in result.artifacts

    def test_rich_description_error_when_d2_generation_fails(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value=None):
                result = module.handle("/diagram a detailed system", {})
        assert result.status == "error"

    def test_rich_description_includes_d2_in_response_text(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="API -> Backend"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                    result = module.handle("/diagram detailed system", {})
        assert "API -> Backend" in result.response_text


class TestMultiTurnGrillLoop:
    def test_initial_underspecified_yields_in_refinement(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            turn1 = module.handle("/diagram a thing with some boxes", {})
        assert turn1.status == "in_refinement"
        assert turn1.updated_state["phase"] == "grilling"

    def test_answers_fold_into_brief_and_complete(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            turn1 = module.handle("/diagram a thing with some boxes", {})

        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="API -> Backend"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                    turn2 = module.handle(
                        "3 components: API Gateway, Backend, Database. Flows left to right.",
                        turn1.updated_state,
                    )

        assert turn2.status == "completed"
        assert "d2" in turn2.artifacts
        assert "svg" in turn2.artifacts

    def test_full_state_machine_transitions(self):
        """init → in_refinement (grilling) → completed: all three state transitions."""
        module = _make_module()

        # Transition 1: init → grilling
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            t1 = module.handle("/diagram a thing with some boxes", {})
        assert t1.status == "in_refinement"
        assert t1.updated_state["phase"] == "grilling"

        # Transition 2: grilling → completed (answers complete the brief)
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="API -> Backend -> Database"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = b"<svg bytes/>"
                    t2 = module.handle("API Gateway, Backend, Database left to right", t1.updated_state)

        assert t2.status == "completed"
        assert t2.artifacts.get("d2") == "API -> Backend -> Database"
        assert t2.artifacts.get("svg") == b"<svg bytes/>"

    def test_grill_turn_passes_original_description_as_context(self):
        captured: dict = {}
        module = _make_module()

        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            t1 = module.handle("/diagram medallion architecture", {})

        def capture_grill(description: str, partial_brief: dict) -> GrillRound:
            captured["description"] = description
            return _grill_complete()

        with patch.object(module, "grill_round", side_effect=capture_grill):
            with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                    module.handle("bronze, silver, gold layers", t1.updated_state)

        assert "medallion architecture" in captured["description"]
        assert "bronze, silver, gold layers" in captured["description"]

    def test_svg_bytes_propagate_to_final_response(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            t1 = module.handle("/diagram a system", {})

        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="X -> Y"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_cls.return_value.generate_svg.return_value = b"<svg>real svg</svg>"
                    t2 = module.handle("answer", t1.updated_state)

        assert t2.artifacts["svg"] == b"<svg>real svg</svg>"


class TestSketchFlagForwarding:
    def test_sketch_true_forwarded_to_engine(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
                with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                    mock_engine = MagicMock()
                    mock_engine.generate_svg.return_value = b"<svg/>"
                    mock_cls.return_value = mock_engine
                    module.handle("/diagram a test diagram", {})

        mock_engine.generate_svg.assert_called_once()
        _, kwargs = mock_engine.generate_svg.call_args
        assert kwargs.get("sketch") is True
