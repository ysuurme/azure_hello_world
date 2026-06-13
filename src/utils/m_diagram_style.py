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
  person:   { shape: person;   style: { fill: "#e3f2fd"; stroke: "#1565c0" } }
  service:  { style: { fill: "#f3e5f5"; stroke: "#7b1fa2"; border-radius: 8 } }
  cylinder: { shape: cylinder; style: { fill: "#e8f5e9"; stroke: "#2e7d32" } }
  datastore: { shape: cylinder; style: { fill: "#e8f5e9"; stroke: "#2e7d32" } }
  queue:    { shape: queue;    style: { fill: "#f3e5f5"; stroke: "#6a1b9a" } }
  cloud:    { shape: cloud;    style: { fill: "#f5f5f5"; stroke: "#616161" } }
  external: { style: { fill: "#f5f5f5"; stroke: "#616161"; stroke-dash: 3 } }
  hexagon:  { shape: hexagon;  style: { fill: "#f3e5f5"; stroke: "#4527a0" } }
  document: { shape: page;     style: { fill: "#e8f5e9"; stroke: "#388e3c" } }
  security: { style: { fill: "#fff8e1"; stroke: "#f57f17" } }
  boundary: { style: { fill: "transparent"; stroke: "#9aa0a6"; stroke-dash: 4; border-radius: 12; opacity: 0.4 } }
}
"""

_DEFAULT_CONVENTIONS = (
    "House style — classes ARE ALREADY DEFINED in the preamble; do NOT emit a `classes:` block.\n"
    "Tag EVERY shape with its class using `<id>.class: <name>`.\n\n"
    "SHAPE SELECTION — pick the class whose role matches:\n"
    "  IF actor / client / user / browser / mobile app         → class: person\n"
    "  IF application service / API / microservice / UI layer  → class: service\n"
    "  IF database / cache / object store / persistent storage → class: cylinder\n"
    "  IF message broker / event bus / stream / pub-sub topic  → class: queue\n"
    "  IF external SaaS / third-party / out-of-scope system    → class: cloud\n"
    "  IF serverless function / lambda / ephemeral worker      → class: hexagon\n"
    "  IF log / config file / manifest / schema / artifact     → class: document\n"
    "  IF identity provider / auth service / firewall / WAF    → class: security\n"
    "  IF trust zone / network boundary / logical group (container) → class: boundary\n\n"
    "FILL COLOUR — applied automatically by class, do NOT override:\n"
    "  ingress/public (#e3f2fd)        : person\n"
    "  compute/app (#f3e5f5)           : service, hexagon, queue\n"
    "  stateful storage (#e8f5e9)      : cylinder, document\n"
    "  security/identity (#fff8e1)     : security\n"
    "  external/untrusted (#f5f5f5)    : cloud, external\n\n"
    "CONTAINMENT:\n"
    "  Wrap every trust zone or network segment in a boundary-classed container.\n"
    "  boundary containers use stroke-dash and opacity: 0.4 — enclosed shapes stay focal.\n\n"
    "EDGE RULES (all mandatory):\n"
    "  Every edge MUST carry a label (protocol, event name, or payload type).\n"
    "  Primary synchronous path        : style.stroke-width: 3\n"
    "  Async / event-driven flow       : style.stroke-dash: 4\n"
    "  Streaming / WebSocket / replication: animated: true\n"
    "  One-to-many cardinality         : target-arrowhead.shape: cf-many\n\n"
    "MULTIPLE FLAG:\n"
    "  Set `<id>.multiple: true` for any scaled / replicated / pooled component.\n\n"
    "EXAMPLE (three shapes, three fills, labelled edges):\n"
    '  region: "Azure Region" {\n'
    "    class: boundary\n"
    '    gw: "API Gateway"; gw.class: service\n'
    '    svc: "Order Service"; svc.class: service\n'
    '    db: "Orders DB"; db.class: cylinder\n'
    "  }\n"
    "Conventions: group related components inside containers (blocks-in-blocks); use a `boundary`-classed "
    "container for trust/network zones; reference nested shapes by full path in edges; label every edge "
    "with what flows; solid arrows for sync, dashed (`style.stroke-dash: 4`) for async/events.\n"
    "Direction selection: use `direction: right` for temporal/streaming/pipeline flows (data moves left to "
    "right through stages); use `direction: down` for multi-tier infrastructure stacks (client → gateway → "
    "service → data tiers layered top to bottom)."
)


@dataclass(frozen=True)
class DiagramStyle:
    name: str = "default"
    sketch: bool = True
    theme: int | None = 0  # D2 theme id; 0 = neutral so the explicit palette dominates
    pad: int = 20
    layout_engine: str = "elk"
    d2_preamble: str = _DEFAULT_PREAMBLE
    conventions: str = _DEFAULT_CONVENTIONS


DEFAULT_STYLE = DiagramStyle()


def get_diagram_style() -> DiagramStyle:
    """Return the active diagram aesthetic standard (in-repo default; platform-backed later)."""
    return DEFAULT_STYLE
