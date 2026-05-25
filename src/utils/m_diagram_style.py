"""Diagram aesthetic standard.

A single, named source of truth for how diagrams look, so every generated diagram shares a
consistent feel instead of the LLM reinventing styling each time. Three layers:
  - engine config (sketch / theme / pad) applied by DiagramEngine,
  - a D2 `classes` preamble injected ahead of every diagram (the palette/shapes),
  - conventions text fed to the D2 generator so it applies the classes rather than freestyling.

In-repo default for now; a future revision loads/overrides the active standard from versioned
platform storage so the house style can evolve (see ISSUES.md). Returned via get_diagram_style().
"""

from __future__ import annotations

from dataclasses import dataclass

# Injected ahead of every generated diagram. The generator references these classes; it must NOT
# redefine them (kept here so the palette is identical across all diagrams).
_DEFAULT_PREAMBLE = """\
classes: {
  service: { style: { fill: "#e8f0fe"; stroke: "#1a73e8"; border-radius: 8 } }
  datastore: { shape: cylinder; style: { fill: "#fce8e6"; stroke: "#c5221f" } }
  queue: { shape: hexagon; style: { fill: "#fef7e0"; stroke: "#f9ab00" } }
  external: { style: { fill: "#f1f3f4"; stroke: "#5f6368"; stroke-dash: 3 } }
  boundary: { style: { fill: "transparent"; stroke: "#9aa0a6"; stroke-dash: 4; border-radius: 12 } }
}
"""

_DEFAULT_CONVENTIONS = (
    "House style — these D2 classes are ALREADY DEFINED elsewhere; do NOT emit a `classes:` block, but you "
    "MUST tag EVERY shape with the class that fits its role using `<shape>.class: <name>`:\n"
    "- service: application / compute components\n"
    "- datastore: databases and persistent stores\n"
    "- queue: brokers, topics, event buses\n"
    "- external: third-party / out-of-scope systems\n"
    "- boundary: a container used for a trust/network boundary or logical group\n"
    "Example (note every shape is tagged):\n"
    '  services: "Services" {\n'
    '    order_svc: "Order Service"; order_svc.class: service\n'
    '    db: "Orders DB"; db.class: datastore\n'
    "  }\n"
    "Conventions: group related components inside containers (blocks-in-blocks); use a `boundary`-classed "
    "container for trust/network zones; reference nested shapes by full path in edges; label every edge "
    "with what flows; solid arrows for sync, dashed (`style.stroke-dash: 4`) for async/events."
)


@dataclass(frozen=True)
class DiagramStyle:
    name: str = "default"
    sketch: bool = True
    theme: int | None = 0  # D2 theme id; 0 = neutral so the explicit palette dominates
    pad: int = 20
    d2_preamble: str = _DEFAULT_PREAMBLE
    conventions: str = _DEFAULT_CONVENTIONS


DEFAULT_STYLE = DiagramStyle()


def get_diagram_style() -> DiagramStyle:
    """Return the active diagram aesthetic standard (in-repo default; platform-backed later)."""
    return DEFAULT_STYLE
