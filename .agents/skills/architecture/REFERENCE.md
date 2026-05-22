# Architecture — Reference

Deep-dive reference for the `architecture` skill. See [SKILL.md](SKILL.md) for the overview,
scope, and quick start. See [EXAMPLES.md](EXAMPLES.md) for a worked end-to-end session.

---

## Static Analysis Tool Matrix

| Language | Recommended Tools | Output Format | Notes |
|----------|------------------|---------------|-------|
| Python | `pydeps`, `pyreverse` | JSON, DOT, SVG | `pydeps` produces module-level dependency trees |
| TypeScript | `dependency-cruiser`, `madge` | JSON, DOT, text | `dependency-cruiser` enforces rules as code |
| Any | `codeflow` (when available) | JSON | Exports file + module dependency graph with metrics |

**Invocation principle:** Always write raw output to the filesystem. Never pipe raw graph data
directly into the context window — dependency graphs can be thousands of lines.

---

## Dependency Graph Generation

### Python (pydeps)

```bash
# Install in project venv
uv add --dev pydeps

# Generate module dependency graph (output to filesystem only)
uv run pydeps src --max-bacon=3 --show-deps --no-show > docs/arch/deps.json
```

### TypeScript (dependency-cruiser)

```bash
npx dependency-cruiser src --output-type json > docs/arch/deps.json
```

### Extracting a summary (load this into context, not the raw file)

```bash
# Python: count modules, edges, and circular dependencies
python -c "
import json, sys
data = json.load(open('docs/arch/deps.json'))
mods = data.get('modules', data if isinstance(data, list) else [])
print(f'Modules: {len(mods)}')
circulars = [m for m in mods if m.get('circular')]
print(f'Circular: {len(circulars)}')
"
```

---

## Module Depth Classification — Decision Rubric

```
interface_lines / implementation_lines → depth_ratio

depth_ratio > 0.5  → Shallow module  (interface ≈ implementation — refactoring trigger)
depth_ratio ≤ 0.2  → Deep module     (target state)
0.2 < ratio ≤ 0.5 → Borderline      (flag but do not block)
```

**God Object detection:** A single module with fan-in from > 3 distinct bounded contexts is a
God Object candidate. Flag in the blast-radius report; recommend splitting.

**Anemic domain model detection:** A domain module where < 20% of lines are logic (mostly
property accessors) is anemic. Flag for REFACTOR phase in `tdd`.

---

## Blast-Radius Computation — Step-by-Step

### Step 1 — Identify directly changed modules

```bash
git diff --name-only HEAD~1 | grep -E '\.(py|ts)$'
```

### Step 2 — Trace callers (fan-in)

For each changed module, find all modules that import it:

```bash
# Python — find all files that import a given module
grep -r "from src.module_a" src/ --include="*.py" -l
grep -r "import module_a" src/ --include="*.py" -l
```

### Step 3 — Trace dependencies (fan-out)

For each changed module, list all modules it imports:

```bash
# Python — list direct imports
grep -E "^(import|from)" src/module_a.py
```

### Step 4 — Classify each affected module

Against `CONTEXT.md` Bounded Contexts:

| Classification | Condition | Action |
|----------------|-----------|--------|
| **Safe** | Affected module is in the same bounded context as the change | No action |
| **At-risk** | Affected module crosses a bounded-context boundary | Flag in report |
| **Blocked** | Circular dependency or constraint violation | Block merge |

### Step 5 — Write the blast-radius report to disk

```bash
cat > docs/arch/blast-radius.md << 'EOF'
## Blast-Radius Report

**Changed:** <module-a>, <module-b>
**At-risk:** <module-c> (crosses domain boundary defined in CONTEXT.md §Bounded Contexts)
**Safe:** <module-d>, <module-e>

**Recommendation:** [proceed | refactor first | block]
EOF
```

### Step 6 — Post as PR comment

```bash
gh pr comment <PR_NUMBER> --body "$(cat docs/arch/blast-radius.md)"
```

---

## Metric Interpretation Guide

| Metric | Healthy | Warning | Block |
|--------|---------|---------|-------|
| Fragility score | 0.0–0.3 | 0.3–0.6 | > 0.6 |
| Coupling metric (inter-layer deps) | 0–3 | 4–6 | > 6 |
| Churn (modifications/month) | < 5 | 5–15 | > 15 and high fragility |
| Pattern grade | A–B | C–D | F |

**Fragility formula (simplified):**

```
fragility = outgoing_inter_layer_deps / (total_deps + 1)
```

A module that depends heavily on modules in other layers is fragile — changes in those
layers ripple back.

---

## GitHub Issue Research Loop — Full Procedure

```bash
# 1. List open architecture-related issues
gh issue list --label architecture --json number,title,body,labels \
  | jq '.[] | {number, title, labels: [.labels[].name]}'

# 2. Search for issues mentioning affected modules
gh search issues --repo <owner>/<repo> "<module-name>" \
  --json number,title,state

# 3. Cross-reference: for each at-risk module, check open issues
for module in module_a module_b; do
  echo "Module: $module"
  gh search issues --repo <owner>/<repo> "$module" \
    --json number,title,state \
    | jq '.[] | "  #\(.number): \(.title) [\(.state)]"'
done
```

Flag any overlap in the blast-radius report: "Open issue #N may be affected by this change."

---

## Refactoring Demand — Escalation Path

```
Pattern grade F  OR  fragility > 0.6
  └─ Block merge
  └─ Open a refactoring issue labelled HITL
  └─ Raise with `refine` to revise the boundary if needed
  └─ Do NOT proceed until the refactoring issue is closed

Shallow module detected
  └─ Flag in blast-radius report
  └─ Trigger REFACTOR phase in `tdd` for the current feature
  └─ Open a separate issue only if the module is in a different bounded context

Circular dependency
  └─ Block merge immediately — no exceptions
  └─ Open a fix issue labelled AFK if the fix is mechanical
  └─ Open a HITL issue if the fix requires boundary decisions
```
