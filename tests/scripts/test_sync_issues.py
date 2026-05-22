"""Tests for the metadata-header stripping logic in .github/scripts/sync-issues.ps1.

Two layers of coverage:

1. Oracle snippet tests — replicate the strip logic as a PS function and verify
   it correctly removes LABELS:, ESTIMATE:, and PRIORITY: lines in all positions.

2. File-based checks — verify that sync-issues.ps1 uses -replace (regex) to
   strip headers, not just Select-Object -Skip (which only handles consecutive
   headers at the top of the body).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent.parent / ".github" / "scripts" / "sync-issues.ps1"
PWSH = shutil.which("pwsh") or "pwsh"

pytestmark = pytest.mark.skipif(
    not shutil.which("pwsh"),
    reason="pwsh not available",
)

# Oracle: the strip logic replicated from sync-issues.ps1.
# These tests verify the Oracle behaviour; the file-based tests verify the
# actual script implements the same pattern.
_STRIP_SNIPPET = r"""
function Strip-MetadataHeaders([string]$Body) {
    $Body = $Body -replace '(?m)^LABELS:\s*.+(\r?\n|$)', ''
    $Body = $Body -replace '(?m)^ESTIMATE:\s*\d+(\r?\n|$)', ''
    $Body = $Body -replace '(?m)^PRIORITY:\s*P[0-4](\r?\n|$)', ''
    return $Body.TrimStart()
}
"""


def _ps(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PWSH, "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
    )


# ── Oracle snippet tests ──────────────────────────────────────────────────────


def test_strip_removes_labels_header() -> None:
    """LABELS: header line is removed from the body."""
    result = _ps(
        _STRIP_SNIPPET
        + r"""
$body = "LABELS: enhancement`n**Goal**: Foo"
$out = Strip-MetadataHeaders $body
if ($out -notmatch 'LABELS:' -and $out -match '\*\*Goal\*\*: Foo') { exit 0 } else {
    Write-Host "Got: $out"; exit 1
}
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_strip_removes_estimate_header() -> None:
    """ESTIMATE: header line is removed from the body."""
    result = _ps(
        _STRIP_SNIPPET
        + r"""
$body = "ESTIMATE: 5`n**Goal**: Bar"
$out = Strip-MetadataHeaders $body
if ($out -notmatch 'ESTIMATE:' -and $out -match '\*\*Goal\*\*: Bar') { exit 0 } else {
    Write-Host "Got: $out"; exit 1
}
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_strip_removes_priority_header() -> None:
    """PRIORITY: header line is removed from the body."""
    result = _ps(
        _STRIP_SNIPPET
        + r"""
$body = "PRIORITY: P2`n**Goal**: Baz"
$out = Strip-MetadataHeaders $body
if ($out -notmatch 'PRIORITY:' -and $out -match '\*\*Goal\*\*: Baz') { exit 0 } else {
    Write-Host "Got: $out"; exit 1
}
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_strip_removes_all_three_headers_in_sequence() -> None:
    """All three metadata headers are removed; markdown body is preserved."""
    result = _ps(
        _STRIP_SNIPPET
        + r"""
$body = "LABELS: enhancement`nESTIMATE: 3`nPRIORITY: P2`n**Goal**: Keep this"
$out = Strip-MetadataHeaders $body
$ok = ($out -notmatch 'LABELS:') -and ($out -notmatch 'ESTIMATE:') -and ($out -notmatch 'PRIORITY:') -and ($out -match '\*\*Goal\*\*: Keep this')
if ($ok) { exit 0 } else { Write-Host "Got: $out"; exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_strip_removes_headers_in_any_order() -> None:
    """Headers in a non-standard order are all stripped."""
    result = _ps(
        _STRIP_SNIPPET
        + r"""
$body = "PRIORITY: P1`nLABELS: AFK`nESTIMATE: 8`n**Goal**: Content"
$out = Strip-MetadataHeaders $body
$ok = ($out -notmatch 'LABELS:') -and ($out -notmatch 'ESTIMATE:') -and ($out -notmatch 'PRIORITY:') -and ($out -match '\*\*Goal\*\*: Content')
if ($ok) { exit 0 } else { Write-Host "Got: $out"; exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_strip_preserves_body_without_headers() -> None:
    """Body with no metadata headers is returned unchanged (modulo TrimStart)."""
    result = _ps(
        _STRIP_SNIPPET
        + r"""
$body = "**Goal**: Just content`n**Description**: More content"
$out = Strip-MetadataHeaders $body
if ($out -eq $body) { exit 0 } else {
    Write-Host "Expected: $body`nGot: $out"; exit 1
}
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_strip_removes_headers_separated_by_blank_line() -> None:
    """Headers separated by a blank line are all stripped.

    Regression: the previous Select-Object -Skip approach stopped stripping on
    the first empty line, leaving subsequent headers in the body.
    """
    result = _ps(
        _STRIP_SNIPPET
        + r"""
$body = "LABELS: enhancement`n`nESTIMATE: 3`n**Goal**: Content"
$out = Strip-MetadataHeaders $body
$ok = ($out -notmatch 'LABELS:') -and ($out -notmatch 'ESTIMATE:') -and ($out -match '\*\*Goal\*\*: Content')
if ($ok) { exit 0 } else { Write-Host "Got: $out"; exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ── File-based checks ─────────────────────────────────────────────────────────


def test_script_strips_labels_with_regex_replace() -> None:
    """sync-issues.ps1 uses -replace to strip LABELS: header lines."""
    content = SCRIPT.read_text(encoding="utf-8")
    assert "(?m)^LABELS:" in content, "sync-issues.ps1 must use -replace '(?m)^LABELS:...' to strip LABELS headers"


def test_script_strips_estimate_with_regex_replace() -> None:
    """sync-issues.ps1 uses -replace to strip ESTIMATE: header lines."""
    content = SCRIPT.read_text(encoding="utf-8")
    assert "(?m)^ESTIMATE:" in content, (
        "sync-issues.ps1 must use -replace '(?m)^ESTIMATE:...' to strip ESTIMATE headers"
    )


def test_script_strips_priority_with_regex_replace() -> None:
    """sync-issues.ps1 uses -replace to strip PRIORITY: header lines."""
    content = SCRIPT.read_text(encoding="utf-8")
    assert "(?m)^PRIORITY:" in content, (
        "sync-issues.ps1 must use -replace '(?m)^PRIORITY:...' to strip PRIORITY headers"
    )
