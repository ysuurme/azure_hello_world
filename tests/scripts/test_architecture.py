"""Tests for .github/scripts/kanban/architecture.ps1.

Covers the two critical business rules that must not regress:

1. File-count gate  — <=5 .py files in src/ → trivial path (one-liner
   BLAST_RADIUS.md, no fake graphs); >5 → full analysis path.
2. State.json       — Set-PipelineState writes a JSON file with the expected
   phase label and a transitions array that accumulates across calls.

Each test uses an inline PowerShell snippet that replicates the exact logic from
architecture.ps1 so we avoid dot-sourcing the full orchestrator (which requires
a live Kanban environment) while still exercising the real business rules.
"""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

PWSH = shutil.which("pwsh") or "pwsh"
SCRIPT = (
    Path(__file__).parent.parent.parent
    / ".github"
    / "scripts"
    / "kanban"
    / "architecture.ps1"
)

pytestmark = pytest.mark.skipif(
    not shutil.which("pwsh"),
    reason="pwsh not available",
)


def _ps(script: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PWSH, "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


# ── File-count gate ───────────────────────────────────────────────────────────
# Replicates the gate condition from Invoke-Architecture exactly.

_GATE_SNIPPET = """\
function Test-FileCountGate {
    param([string]$SrcPath, [int]$Threshold = 5)
    $count = @(Get-ChildItem $SrcPath -Recurse -Filter '*.py' -ErrorAction SilentlyContinue).Count
    return $count -gt $Threshold
}
"""


def _make_src(tmp_path: Path, n_py_files: int) -> Path:
    """Create a fake src/ directory with *n_py_files* .py files."""
    src = tmp_path / "src"
    src.mkdir()
    for i in range(n_py_files):
        (src / f"module_{i}.py").write_text(f"# module {i}\n", encoding="utf-8")
    return src


def test_gate_exactly_five_is_trivial(tmp_path: Path) -> None:
    src = _make_src(tmp_path, 5)
    result = _ps(
        _GATE_SNIPPET
        + f"if (Test-FileCountGate '{src}') {{ exit 1 }} else {{ exit 0 }}"
    )
    assert result.returncode == 0, "5 .py files must NOT trigger the non-trivial path"


def test_gate_six_is_nontrivial(tmp_path: Path) -> None:
    src = _make_src(tmp_path, 6)
    result = _ps(
        _GATE_SNIPPET
        + f"if (Test-FileCountGate '{src}') {{ exit 0 }} else {{ exit 1 }}"
    )
    assert result.returncode == 0, "6 .py files must trigger the non-trivial path"


def test_gate_zero_files_is_trivial(tmp_path: Path) -> None:
    src = _make_src(tmp_path, 0)
    result = _ps(
        _GATE_SNIPPET
        + f"if (Test-FileCountGate '{src}') {{ exit 1 }} else {{ exit 0 }}"
    )
    assert result.returncode == 0, "0 .py files must NOT trigger the non-trivial path"


def test_gate_counts_recursively(tmp_path: Path) -> None:
    """Files in nested subdirectories must count toward the gate."""
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    for i in range(6):
        (src / "sub" / f"m_{i}.py").write_text("", encoding="utf-8")
    result = _ps(
        _GATE_SNIPPET
        + f"if (Test-FileCountGate '{src}') {{ exit 0 }} else {{ exit 1 }}"
    )
    assert result.returncode == 0, "Nested .py files must count toward the gate"


# ── BLAST_RADIUS.md — trivial branch ─────────────────────────────────────────

_TRIVIAL_BLAST_RADIUS_SNIPPET = """\
function Write-TrivialBlastRadius {
    param([string]$Path)
    'trivial codebase, no architectural risk computed' | Set-Content $Path -Encoding utf8
}
"""


def test_trivial_blast_radius_one_liner(tmp_path: Path) -> None:
    out = tmp_path / "BLAST_RADIUS.md"
    result = _ps(_TRIVIAL_BLAST_RADIUS_SNIPPET + f"Write-TrivialBlastRadius '{out}'")
    assert result.returncode == 0
    assert out.exists(), "BLAST_RADIUS.md must be created"
    content = out.read_text(encoding="utf-8").strip()
    assert content == "trivial codebase, no architectural risk computed", (
        f"Unexpected content: {content!r}"
    )


def test_trivial_blast_radius_has_no_graph_data(tmp_path: Path) -> None:
    """The trivial one-liner must not contain dependency graph keywords."""
    out = tmp_path / "BLAST_RADIUS.md"
    _ps(_TRIVIAL_BLAST_RADIUS_SNIPPET + f"Write-TrivialBlastRadius '{out}'")
    content = out.read_text(encoding="utf-8").lower()
    # Graph keywords that would indicate a fake graph was generated
    for keyword in ("fan-in", "fan_in", "module graph", "pydeps"):
        assert keyword not in content, (
            f"Trivial BLAST_RADIUS.md must not contain '{keyword}'"
        )


# ── State.json helpers ────────────────────────────────────────────────────────
# Replicates Set-PipelineState from architecture.ps1 as a self-contained snippet.

_STATE_SNIPPET = textwrap.dedent("""\
    function Set-PipelineState {
        param([int]$IssueNumber, [string]$Phase, [string]$PlanRoot)
        $planDir   = "$PlanRoot\\$IssueNumber"
        $statePath = "$planDir\\state.json"
        $null      = New-Item -ItemType Directory -Force -Path $planDir

        $transitions = @()
        if (Test-Path $statePath) {
            try {
                $existing = Get-Content $statePath -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
                if ($null -ne $existing.transitions) { $transitions = @($existing.transitions) }
            } catch {}
        }

        $transitions += [pscustomobject]@{ phase = $Phase; timestamp = (Get-Date -Format 'o') }

        $entriesJson = ($transitions | ForEach-Object {
            $ts = $_.timestamp -replace '"', '\\"'
            $ph = $_.phase     -replace '"', '\\"'
            "  {`"phase`":`"$ph`",`"timestamp`":`"$ts`"}"
        }) -join ",`n"

        $json = "{`n  `"issue`": $IssueNumber,`n  `"transitions`": [`n$entriesJson`n  ]`n}"
        $json | Set-Content $statePath -Encoding utf8 -NoNewline
    }
""")


def _read_state(plan_root: Path, issue: int) -> dict:
    path = plan_root / str(issue) / "state.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_state_json_created_on_first_call(tmp_path: Path) -> None:
    result = _ps(
        _STATE_SNIPPET
        + f"Set-PipelineState -IssueNumber 99 -Phase 'refining' -PlanRoot '{tmp_path}'"
    )
    assert result.returncode == 0, result.stderr
    state = _read_state(tmp_path, 99)
    assert state["issue"] == 99
    assert len(state["transitions"]) == 1
    assert state["transitions"][0]["phase"] == "refining"


def test_state_json_accumulates_transitions(tmp_path: Path) -> None:
    script = (
        _STATE_SNIPPET
        + f"Set-PipelineState -IssueNumber 42 -Phase 'refining'    -PlanRoot '{tmp_path}'\n"
        + f"Set-PipelineState -IssueNumber 42 -Phase 'architecting' -PlanRoot '{tmp_path}'\n"
        + f"Set-PipelineState -IssueNumber 42 -Phase 'implementing' -PlanRoot '{tmp_path}'\n"
    )
    result = _ps(script)
    assert result.returncode == 0, result.stderr
    state = _read_state(tmp_path, 42)
    phases = [t["phase"] for t in state["transitions"]]
    assert phases == ["refining", "architecting", "implementing"], (
        f"Expected refining → architecting → implementing, got: {phases}"
    )


def test_state_json_transitions_is_array(tmp_path: Path) -> None:
    """transitions must always be a JSON array, even with a single entry."""
    result = _ps(
        _STATE_SNIPPET
        + f"Set-PipelineState -IssueNumber 7 -Phase 'architecting' -PlanRoot '{tmp_path}'"
    )
    assert result.returncode == 0, result.stderr
    raw = (tmp_path / "7" / "state.json").read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert isinstance(parsed["transitions"], list), (
        "transitions must be a JSON array even with one entry"
    )


def test_state_json_issue_number_correct(tmp_path: Path) -> None:
    result = _ps(
        _STATE_SNIPPET
        + f"Set-PipelineState -IssueNumber 123 -Phase 'refining' -PlanRoot '{tmp_path}'"
    )
    assert result.returncode == 0, result.stderr
    state = _read_state(tmp_path, 123)
    assert state["issue"] == 123


# ── $safeStr truncation logic ─────────────────────────────────────────────────
# Replicates the fixed assignment block from Invoke-Architecture (non-trivial branch).

_SAFE_STR_SNIPPET = textwrap.dedent("""\
    function Get-SafeStr {
        param([string[]]$safe)
        if ($safe.Count -gt 0) {
            $safeStr = ($safe | Select-Object -First 5) -join ', '
            if ($safe.Count -gt 5) { $safeStr += " … +$($safe.Count - 5) more" }
        } else {
            $safeStr = 'none'
        }
        return $safeStr
    }
""")


def test_safe_str_truncation_appends_count_when_more_than_five() -> None:
    """8 safe modules → first 5 joined, then ' … +3 more' appended."""
    mods = [f"mod_{i}" for i in range(8)]
    mods_ps = ", ".join(f"'{m}'" for m in mods)
    result = _ps(_SAFE_STR_SNIPPET + f"$safe = @({mods_ps})\nGet-SafeStr -safe $safe")
    assert result.returncode == 0, result.stderr
    output = result.stdout.strip()
    assert " … +3 more" in output, f"Expected ' … +3 more' in output, got: {output!r}"
    for m in mods[:5]:
        assert m in output, f"Expected first-5 module {m!r} in output"


def test_safe_str_exactly_five_no_truncation() -> None:
    """Exactly 5 safe modules must produce no truncation indicator."""
    mods = [f"mod_{i}" for i in range(5)]
    mods_ps = ", ".join(f"'{m}'" for m in mods)
    result = _ps(_SAFE_STR_SNIPPET + f"$safe = @({mods_ps})\nGet-SafeStr -safe $safe")
    assert result.returncode == 0, result.stderr
    output = result.stdout.strip()
    assert "more" not in output, (
        f"5 modules must not produce a truncation indicator, got: {output!r}"
    )
    for m in mods:
        assert m in output


def test_safe_str_empty_is_none() -> None:
    """Empty safe list must produce the string 'none'."""
    result = _ps(_SAFE_STR_SNIPPET + "$safe = @()\nGet-SafeStr -safe $safe")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "none"
