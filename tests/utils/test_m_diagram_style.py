"""Tests for the DiagramStyle semantic palette, shape, and edge heuristics (issue #74)."""

from __future__ import annotations

import re

import pytest

from src.utils.m_diagram_style import DEFAULT_STYLE, DiagramStyle, get_diagram_style

# A multi-tier D2 body that exercises person / service / cylinder / queue / cloud classes.
_MULTI_TIER_BODY = """\
direction: right
user: "Client"; user.class: person
region: "Azure Region" {
  class: boundary
  gw: "API Gateway"; gw.class: service
  svc: "Order Service"; svc.class: service
  db: "Orders DB"; db.class: cylinder
  topic: "Events"; topic.class: queue
}
ext: "Payment SaaS"; ext.class: cloud
user -> region.gw: "HTTPS" { style.stroke-width: 3 }
region.gw -> region.svc: "REST" { style.stroke-width: 3 }
region.svc -> region.db: "SQL" { style.stroke-width: 3 }
region.svc -> region.topic: "order.placed" { style.stroke-dash: 4 }
"""


class TestPreambleClassCoverage:
    """Acceptance criterion: preamble defines person, cylinder, queue, cloud, hexagon/code, document/page."""

    def test_person_class_defined(self):
        assert "person:" in DEFAULT_STYLE.d2_preamble

    def test_cylinder_class_defined(self):
        assert "cylinder:" in DEFAULT_STYLE.d2_preamble

    def test_queue_class_defined(self):
        assert "queue:" in DEFAULT_STYLE.d2_preamble

    def test_cloud_class_defined(self):
        assert "cloud:" in DEFAULT_STYLE.d2_preamble

    def test_compute_shape_defined(self):
        preamble = DEFAULT_STYLE.d2_preamble
        assert "hexagon:" in preamble or "code:" in preamble

    def test_document_shape_defined(self):
        preamble = DEFAULT_STYLE.d2_preamble
        assert "document:" in preamble or "page:" in preamble

    def test_boundary_class_retained(self):
        assert "boundary:" in DEFAULT_STYLE.d2_preamble

    def test_service_class_retained(self):
        assert "service:" in DEFAULT_STYLE.d2_preamble

    def test_preamble_opens_with_classes_block(self):
        assert DEFAULT_STYLE.d2_preamble.lstrip().startswith("classes:")


class TestPreambleFillColours:
    """Acceptance criterion: all five layered fill colours present in the preamble."""

    def test_ingress_fill_present(self):
        assert "#e3f2fd" in DEFAULT_STYLE.d2_preamble

    def test_stateful_fill_present(self):
        assert "#e8f5e9" in DEFAULT_STYLE.d2_preamble

    def test_security_fill_present(self):
        assert "#fff8e1" in DEFAULT_STYLE.d2_preamble

    def test_compute_fill_present(self):
        assert "#f3e5f5" in DEFAULT_STYLE.d2_preamble

    def test_external_fill_present(self):
        assert "#f5f5f5" in DEFAULT_STYLE.d2_preamble

    def test_all_five_fills_present(self):
        fills = {"#e3f2fd", "#e8f5e9", "#fff8e1", "#f3e5f5", "#f5f5f5"}
        found = {f for f in fills if f in DEFAULT_STYLE.d2_preamble}
        assert found == fills, f"Missing fills: {fills - found}"


class TestConventionsShapeRules:
    """Acceptance criterion: conventions encode explicit role→shape mapping rules."""

    @pytest.mark.parametrize("class_name", ["person", "cylinder", "queue", "cloud", "hexagon", "security", "boundary"])
    def test_class_name_in_conventions(self, class_name: str):
        assert class_name in DEFAULT_STYLE.conventions

    def test_document_or_page_in_conventions(self):
        assert "document" in DEFAULT_STYLE.conventions or "page" in DEFAULT_STYLE.conventions

    def test_class_tagging_syntax_in_conventions(self):
        assert ".class:" in DEFAULT_STYLE.conventions or "class:" in DEFAULT_STYLE.conventions

    def test_no_classes_block_instruction_present(self):
        conventions = DEFAULT_STYLE.conventions
        assert "do NOT emit" in conventions or "do not emit" in conventions.lower()


class TestConventionsEdgeRules:
    """Acceptance criterion: conventions encode explicit relationship→edge-style rules."""

    def test_sync_stroke_width_rule(self):
        assert "stroke-width" in DEFAULT_STYLE.conventions

    def test_async_stroke_dash_rule(self):
        assert "stroke-dash" in DEFAULT_STYLE.conventions

    def test_animated_stream_rule(self):
        assert "animated" in DEFAULT_STYLE.conventions

    def test_edge_label_mandatory(self):
        conventions_lower = DEFAULT_STYLE.conventions.lower()
        assert "label" in conventions_lower or "must carry" in conventions_lower

    def test_multiple_flag_rule(self):
        assert "multiple" in DEFAULT_STYLE.conventions


class TestComposedDiagramTokenCounts:
    """Acceptance criterion: a multi-tier brief applies ≥3 distinct shapes and ≥3 distinct fill colours."""

    def test_preamble_has_at_least_six_distinct_shape_classes(self):
        known_shapes = {"person", "cylinder", "queue", "cloud", "hexagon", "code", "page", "document"}
        found = {s for s in known_shapes if s + ":" in DEFAULT_STYLE.d2_preamble}
        assert len(found) >= 6

    def test_composed_d2_applies_at_least_three_distinct_classes(self):
        composed = DEFAULT_STYLE.d2_preamble + "\n" + _MULTI_TIER_BODY
        class_tags = re.findall(r"\.class:\s*(\w+)", composed)
        distinct = set(class_tags)
        assert len(distinct) >= 3, f"Only {len(distinct)} distinct class tags: {distinct}"

    def test_composed_d2_has_at_least_three_distinct_fill_colours(self):
        composed = DEFAULT_STYLE.d2_preamble + "\n" + _MULTI_TIER_BODY
        fills = re.findall(r'"(#[0-9a-fA-F]{6})"', composed)
        distinct = set(fills)
        assert len(distinct) >= 3, f"Only {len(distinct)} distinct fill colours: {distinct}"

    def test_composed_d2_has_all_five_fill_colours_from_preamble(self):
        composed = DEFAULT_STYLE.d2_preamble + "\n" + _MULTI_TIER_BODY
        fills = re.findall(r'"(#[0-9a-fA-F]{6})"', composed)
        expected = {"#e3f2fd", "#e8f5e9", "#fff8e1", "#f3e5f5", "#f5f5f5"}
        found = set(fills) & expected
        assert len(found) == 5, f"Missing fills: {expected - found}"


class TestDiagramStyleContract:
    """Existing contract: DiagramStyle is frozen, get_diagram_style returns the default."""

    def test_default_style_name(self):
        assert DEFAULT_STYLE.name == "default"

    def test_default_style_sketch_is_true(self):
        assert DEFAULT_STYLE.sketch is True

    def test_default_style_theme_is_zero(self):
        assert DEFAULT_STYLE.theme == 0

    def test_get_diagram_style_returns_default(self):
        assert get_diagram_style() is DEFAULT_STYLE

    def test_diagram_style_is_frozen(self):
        with pytest.raises((AttributeError, TypeError)):
            DEFAULT_STYLE.sketch = False  # type: ignore[misc]

    def test_custom_style_overrides_preamble(self):
        custom = DiagramStyle(name="custom", d2_preamble="classes: {}")
        assert custom.d2_preamble == "classes: {}"
        assert DEFAULT_STYLE.d2_preamble != "classes: {}"
