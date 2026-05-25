import re
from unittest.mock import MagicMock, patch

import pytest

from src.agents._refinement import GrillQuestion, GrillRound
from src.agents.diagram_studio import (
    _D2_PATTERN,
    _D2_SYSTEM_PROMPT,
    DiagramBrief,
    DiagramStudioModule,
    ModuleResponse,
)
from src.utils.m_diagram_store import DiagramRecord, DiagramSummary


def _make_module() -> DiagramStudioModule:
    """Module with an injected mock store so generation never touches blob/credentials."""
    module = DiagramStudioModule(client_manager=MagicMock())
    module._store = MagicMock()
    module._store.save.return_value = "api-system"
    return module


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

        assert "medallion architecture" in captured["description"]
        assert "/diagram" not in captured["description"]


class TestRichDescriptionAwaitingApproval:
    """A fully-specified description on the first turn goes straight to awaiting_approval."""

    def test_rich_description_returns_awaiting_approval(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            result = module.handle("/diagram API connects to Database with a query", {})
        assert result.status == "awaiting_approval"

    def test_brief_markdown_is_in_response(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            result = module.handle("/diagram a detailed system", {})
        assert "API System" in result.response_text

    def test_no_artifacts_at_approval_stage(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            result = module.handle("/diagram a detailed system", {})
        assert result.artifacts == {}

    def test_updated_state_has_awaiting_approval_phase(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            result = module.handle("/diagram a detailed system", {})
        assert result.updated_state.get("phase") == "awaiting_approval"

    def test_brief_preserved_in_state(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            result = module.handle("/diagram a detailed system", {})
        assert result.updated_state.get("brief", {}).get("subject") == "API System"


class TestMultiTurnGrillLoop:
    def test_initial_underspecified_yields_in_refinement(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            turn1 = module.handle("/diagram a thing with some boxes", {})
        assert turn1.status == "in_refinement"
        assert turn1.updated_state["phase"] == "grilling"

    def test_answers_fold_into_brief_and_reach_awaiting_approval(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            turn1 = module.handle("/diagram a thing with some boxes", {})

        with patch.object(module, "grill_round", return_value=_grill_complete()):
            turn2 = module.handle(
                "3 components: API Gateway, Backend, Database. Flows left to right.",
                turn1.updated_state,
            )

        assert turn2.status == "awaiting_approval"

    def test_full_state_machine_transitions(self):
        """init → in_refinement → awaiting_approval → completed: all four state transitions."""
        module = _make_module()

        # Transition 1: init → grilling
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            t1 = module.handle("/diagram a thing with some boxes", {})
        assert t1.status == "in_refinement"
        assert t1.updated_state["phase"] == "grilling"

        # Transition 2: grilling → awaiting_approval
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            t2 = module.handle("API Gateway, Backend, Database left to right", t1.updated_state)
        assert t2.status == "awaiting_approval"
        assert t2.updated_state["phase"] == "awaiting_approval"

        # Transition 3: awaiting_approval → completed (user approves)
        with patch.object(module, "_generate_d2_from_brief", return_value="API -> Backend -> Database"):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_cls.return_value.generate_svg.return_value = b"<svg bytes/>"
                t3 = module.handle("yes", t2.updated_state)

        assert t3.status == "completed"
        assert "API -> Backend -> Database" in t3.artifacts.get("d2")
        assert t3.artifacts.get("svg") == b"<svg bytes/>"

    def test_grill_turn_passes_original_description_as_context(self):
        captured: dict = {}
        module = _make_module()

        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            t1 = module.handle("/diagram medallion architecture", {})

        def capture_grill(description: str, partial_brief: dict) -> GrillRound:
            captured["description"] = description
            return _grill_complete()

        with patch.object(module, "grill_round", side_effect=capture_grill):
            module.handle("bronze, silver, gold layers", t1.updated_state)

        assert "medallion architecture" in captured["description"]
        assert "bronze, silver, gold layers" in captured["description"]

    def test_svg_bytes_propagate_to_final_response(self):
        module = _make_module()
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            t1 = module.handle("/diagram a system", {})

        with patch.object(module, "grill_round", return_value=_grill_complete()):
            t2 = module.handle("answer", t1.updated_state)

        with patch.object(module, "_generate_d2_from_brief", return_value="X -> Y"):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_cls.return_value.generate_svg.return_value = b"<svg>real svg</svg>"
                t3 = module.handle("yes", t2.updated_state)

        assert t3.artifacts["svg"] == b"<svg>real svg</svg>"


class TestApprovalGate:
    """Approval gate: awaiting_approval phase routing."""

    _APPROVAL_INPUTS = ["yes", "approved", "looks good", "lgtm", "ship it"]
    _REVISION_INPUTS = [
        "please change the layout to vertical",
        "add a load balancer",
        "no thanks",
        "can you make it horizontal",
    ]

    @pytest.mark.parametrize("phrase", _APPROVAL_INPUTS)
    def test_approval_phrase_triggers_generation(self, phrase: str):
        module = _make_module()
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": _grill_complete().updated_brief,
        }
        with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                result = module.handle(phrase, state)
        assert result.status == "completed"

    @pytest.mark.parametrize("phrase", _APPROVAL_INPUTS)
    def test_approval_is_case_insensitive(self, phrase: str):
        module = _make_module()
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": _grill_complete().updated_brief,
        }
        with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                result = module.handle(phrase.upper(), state)
        assert result.status == "completed"

    @pytest.mark.parametrize("revision", _REVISION_INPUTS)
    def test_non_approval_re_enters_grill_loop(self, revision: str):
        module = _make_module()
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": _grill_complete().updated_brief,
        }
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            result = module.handle(revision, state)
        assert result.status == "in_refinement"

    def test_revision_preserves_prior_brief(self):
        module = _make_module()
        prior_brief = _grill_complete().updated_brief
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": prior_brief,
        }

        captured: dict = {}

        def capture_grill(description: str, partial_brief: dict) -> GrillRound:
            captured["brief"] = partial_brief
            return _grill_incomplete()

        with patch.object(module, "grill_round", side_effect=capture_grill):
            module.handle("please change the layout to vertical", state)

        assert captured["brief"] == prior_brief

    def test_revision_does_not_persist(self):
        module = _make_module()
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": _grill_complete().updated_brief,
        }
        with patch.object(module, "grill_round", return_value=_grill_incomplete()):
            module.handle("please change the layout to vertical", state)

        module._store.save.assert_not_called()

    def test_happy_path_persists_trio(self):
        module = _make_module()
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": _grill_complete().updated_brief,
        }
        with patch.object(module, "_generate_d2_from_brief", return_value="API -> DB"):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                result = module.handle("yes", state)

        module._store.save.assert_called_once()
        assert result.artifacts.get("slug") == "api-system"
        # The persisted D2 is self-contained: the house-style class preamble is prepended.
        saved_d2 = module._store.save.call_args.args[1]
        assert "classes:" in saved_d2 and "API -> DB" in saved_d2

    def test_happy_path_response_contains_d2(self):
        module = _make_module()
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": _grill_complete().updated_brief,
        }
        with patch.object(module, "_generate_d2_from_brief", return_value="API -> Backend"):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_cls.return_value.generate_svg.return_value = b"<svg/>"
                result = module.handle("yes", state)
        assert "API -> Backend" in result.response_text

    def test_d2_generation_failure_returns_error(self):
        module = _make_module()
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": _grill_complete().updated_brief,
        }
        with patch.object(module, "_generate_d2_from_brief", return_value=None):
            result = module.handle("yes", state)
        assert result.status == "error"

    def test_no_svg_when_engine_fails(self):
        module = _make_module()
        state = {
            "phase": "awaiting_approval",
            "description": "API system",
            "brief": _grill_complete().updated_brief,
        }
        with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_cls.return_value.generate_svg.return_value = None
                result = module.handle("yes", state)
        assert "svg" not in result.artifacts


class TestStyleForwarding:
    def test_style_forwarded_to_engine_with_sketch(self):
        module = _make_module()

        # First: grill completes → awaiting_approval
        with patch.object(module, "grill_round", return_value=_grill_complete()):
            approval_state = module.handle("/diagram a test diagram", {}).updated_state

        # Then: approve → generate
        with patch.object(module, "_generate_d2_from_brief", return_value="A -> B"):
            with patch("src.agents.diagram_studio.DiagramEngine") as mock_cls:
                mock_engine = MagicMock()
                mock_engine.generate_svg.return_value = b"<svg/>"
                mock_cls.return_value = mock_engine
                module.handle("yes", approval_state)

        mock_engine.generate_svg.assert_called_once()
        _, kwargs = mock_engine.generate_svg.call_args
        assert kwargs["style"].sketch is True


class TestDiagramSubcommands:
    """list / open / delete subcommands for multi-session diagram management."""

    def test_list_returns_saved_diagrams(self):
        module = _make_module()
        module._store.list.return_value = [DiagramSummary(slug="payment", subject="Payment Service")]
        result = module.handle("/diagram list", {})
        assert result.status == "completed"
        assert "payment" in result.response_text

    def test_list_empty_prompts_creation(self):
        module = _make_module()
        module._store.list.return_value = []
        result = module.handle("/diagram list", {})
        assert "No saved diagrams" in result.response_text

    def test_open_loads_diagram_into_awaiting_approval(self):
        module = _make_module()
        module._store.load.return_value = DiagramRecord(
            slug="payment", brief=_grill_complete().updated_brief, d2="A -> B", svg=b"<svg/>"
        )
        result = module.handle("/diagram open payment", {})
        assert result.status == "awaiting_approval"
        assert result.updated_state["slug"] == "payment"
        assert result.artifacts.get("svg") == b"<svg/>"

    def test_open_missing_diagram_returns_not_found(self):
        module = _make_module()
        module._store.load.return_value = None
        result = module.handle("/diagram open nope", {})
        assert "no diagram named" in result.response_text.lower()

    def test_delete_calls_store(self):
        module = _make_module()
        module._store.delete.return_value = True
        result = module.handle("/diagram delete payment", {})
        module._store.delete.assert_called_once_with("payment")
        assert "Deleted" in result.response_text


class TestSystemPromptAnchor:
    """Anchor section is present in _D2_SYSTEM_PROMPT and output-contract regex is intact."""

    def test_system_prompt_ends_with_d2_anchor_block(self):
        assert _D2_SYSTEM_PROMPT.rstrip().endswith("```")
        assert "```d2" in _D2_SYSTEM_PROMPT

    def test_anchor_contains_direction_declaration(self):
        assert "direction:" in _D2_SYSTEM_PROMPT

    def test_anchor_references_all_semantic_classes(self):
        for cls in ("service", "datastore", "queue", "external", "boundary"):
            assert f"class: {cls}" in _D2_SYSTEM_PROMPT, f"Anchor missing semantic class: {cls}"

    def test_anchor_demonstrates_glob_base_style(self):
        assert "*.style" in _D2_SYSTEM_PROMPT

    def test_anchor_contains_nested_boundary_container(self):
        assert "class: boundary" in _D2_SYSTEM_PROMPT

    def test_anchor_contains_per_node_style_override(self):
        assert "style.fill:" in _D2_SYSTEM_PROMPT

    def test_anchor_contains_labelled_edges(self):
        assert re.search(r"->\s+\w[\w.]*\s*:", _D2_SYSTEM_PROMPT)

    def test_output_contract_regex_matches_d2_fence(self):
        sample = '```d2\ndirection: right\nA -> B: "request"\n```'
        assert _D2_PATTERN.search(sample) is not None

    def test_output_contract_regex_captures_body(self):
        body = 'direction: right\nA -> B: "request"'
        match = _D2_PATTERN.search(f"```d2\n{body}\n```")
        assert match is not None
        assert body in match.group(1)
