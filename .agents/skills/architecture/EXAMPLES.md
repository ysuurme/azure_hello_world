# Architecture — Examples

Golden end-to-end session demonstrating the `architecture` skill. See [SKILL.md](SKILL.md)
for the quick-start and [REFERENCE.md](REFERENCE.md) for the full metric reference and
step-by-step procedures.

---

## Example 1: Blast-Radius Report for a New Streaming Module

**Context:** The `refine` Agent Brief (see [refine/EXAMPLES.md](../refine/EXAMPLES.md)) has
been signed off. Before opening any implementation file the agent runs `architecture` to
compute the blast radius of adding `src/streaming/`.

### Step 1 — Generate dependency graph (output to filesystem only)

```bash
mkdir -p docs/arch

# Write graph to disk — never load the raw file into context
uv run pydeps src --max-bacon=2 --show-deps --no-show > docs/arch/deps.json
```

Extract summary only — this is what enters the context window:

```bash
python -c "
import json
data = json.load(open('docs/arch/deps.json'))
mods = data if isinstance(data, list) else data.get('modules', [])
print(f'Modules: {len(mods)}')
circulars = [m for m in mods if isinstance(m, dict) and m.get('circular')]
print(f'Circular dependencies: {len(circulars)}')
"
```

```
Modules: 2       (src.main, src.config)
Circular dependencies: 0
```

### Step 2 — Identify changed modules

```bash
git diff --name-only HEAD
# → (no commits yet on this branch — new files only)
```

From the Agent Brief, the change adds `src/streaming/` (new bounded context). `src/main.py`
requires a routing addition to wire in the new endpoint.

### Step 3 — Classify affected modules

| Module | Relationship to change | Classification | Reason |
|--------|----------------------|----------------|--------|
| `src/streaming/` | New module | Safe | New bounded context; no existing callers |
| `src/main.py` | Requires routing change | At-risk | Routing table change; test coverage required |
| `src/config.py` | Read-only dependency | Safe | No ownership change; no new config needed |

No layer boundary violations detected. No circular dependencies.

### Step 4 — Module depth check

`src/streaming/` is new — no depth classification yet.

`src/main.py` fan-in: 0 external modules import it (it is the entry point).
Fan-out: 1 (`src.config`). Not a God Object risk.

### Step 5 — Write blast-radius report to disk

```bash
cat > docs/arch/blast-radius.md << 'EOF'
## Blast-Radius Report — SSE Streaming Endpoint

**Changed:** src/streaming/ (new), src/main.py (routing addition)
**At-risk:** src/main.py — routing table change; ensure tests cover the new /stream route
**Safe:** src/config.py — read-only dependency; no ownership change

**Recommendation:** proceed — blast radius is bounded to src/main.py routing only.
No boundary violations detected. No circular dependencies.
EOF
```

### Step 6 — Post as PR comment

```bash
gh pr comment <PR_NUMBER> --body "$(cat docs/arch/blast-radius.md)"
```

### Step 7 — GitHub Issue cross-reference

```bash
gh search issues --repo ysuurme/my_template_repo "streaming SSE" \
  --json number,title,state \
  | jq '.[] | "#\(.number): \(.title) [\(.state)]"'
# → (no overlapping open issues found)
```

### Outcome

Architecture session completes cleanly:

- No circular dependencies.
- `src/main.py` is at-risk but bounded — test coverage gate is sufficient.
- Module Map updated with `streaming | src/streaming/ | src/streaming/ | StreamHandler`.
- Blast-radius report posted as PR comment.

**Next:** `plan` session consumes this report to set scope for issue decomposition.

---

## Example 2: Blocking a Merge Due to Circular Dependency

**Context:** A feature branch modifies `src/utils/m_http.py` to import from
`src/domain/service.py`. A dependency graph reveals a cycle:

```
src.domain.service → src.utils.m_http → src.domain.service
```

**Agent action:**

1. Writes blast-radius report with classification **Blocked**.
2. Posts PR comment:

   ```
   ## Blast-Radius Report — Domain Service Refactor

   **Changed:** src/utils/m_http.py
   **Blocked:** Circular dependency detected:
     src.domain.service → src.utils.m_http → src.domain.service

   **Recommendation:** block — do not merge.
   Fix: move the dependency from src/utils/m_http.py into src/domain/ to break the cycle,
   or extract the shared concern into a new module that neither layer imports transitively.
   ```

3. Opens a GitHub Issue labelled `HITL`:

   ```bash
   gh issue create \
     --title "fix(arch): break circular dependency between utils and domain" \
     --label "HITL" \
     --body "Circular dependency: src.domain.service → src.utils.m_http → src.domain.service.
   Requires a boundary decision before the fix can be implemented mechanically."
   ```

The PR is not merged until the circular dependency issue is closed.
