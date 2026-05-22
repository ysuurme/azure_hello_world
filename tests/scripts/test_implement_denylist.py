"""Tests for the denylist guard in .github/scripts/kanban/implement.ps1.

The denylist blocks sensitive file names (*.key, *.pem, *.pfx, *secret*,
*credential*) from being staged, but exempts all paths under docs/adr/ so that
legitimately named ADRs (e.g. ADR-008-secrets-management.md) are never dropped.

Each test runs an inline PowerShell snippet that replicates the exact guard
logic from implement.ps1's Invoke-CommitAndPR denylist block. This avoids
dot-sourcing the full orchestrator script (which requires a live Kanban
environment) while still testing the real business rule.
"""

import shutil
import subprocess

import pytest

PWSH = shutil.which("pwsh") or "pwsh"

pytestmark = pytest.mark.skipif(
    not shutil.which("pwsh"),
    reason="pwsh not available",
)

# Replicates the denylist logic from implement.ps1 Invoke-CommitAndPR exactly.
_DENYLIST_SNIPPET = """\
function Test-SensitivePath {
    param([string]$Path)
    $denyPatterns = @('.env', '*.key', '*.pem', '*.pfx', '*secret*', '*credential*')
    if ($Path -like 'docs/adr/*') { return $false }
    $leaf = Split-Path $Path -Leaf
    return [bool]($denyPatterns | Where-Object { $leaf -like $_ })
}
"""


def _ps(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PWSH, "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
    )


# ── ADR exemptions ─────────────────────────────────────────────────────────────


def test_adr_secrets_management_not_blocked() -> None:
    result = _ps(
        _DENYLIST_SNIPPET
        + "if (Test-SensitivePath 'docs/adr/ADR-008-secrets-management.md') { exit 1 } else { exit 0 }"
    )
    assert result.returncode == 0, (
        "docs/adr/ADR-008-secrets-management.md must NOT be blocked by the denylist"
    )


def test_adr_credential_doc_not_blocked() -> None:
    result = _ps(
        _DENYLIST_SNIPPET
        + "if (Test-SensitivePath 'docs/adr/ADR-009-credential-rotation.md') { exit 1 } else { exit 0 }"
    )
    assert result.returncode == 0, (
        "ADR files matching *credential* under docs/adr/ must NOT be blocked by the denylist"
    )


# ── Sensitive files that must be blocked ──────────────────────────────────────


def test_key_file_is_blocked() -> None:
    result = _ps(
        _DENYLIST_SNIPPET
        + "if (Test-SensitivePath 'private.key') { exit 0 } else { exit 1 }"
    )
    assert result.returncode == 0, "*.key files must be blocked by the denylist"


def test_pem_file_is_blocked() -> None:
    result = _ps(
        _DENYLIST_SNIPPET
        + "if (Test-SensitivePath 'cert.pem') { exit 0 } else { exit 1 }"
    )
    assert result.returncode == 0, "*.pem files must be blocked by the denylist"


def test_pfx_file_is_blocked() -> None:
    result = _ps(
        _DENYLIST_SNIPPET
        + "if (Test-SensitivePath 'cert.pfx') { exit 0 } else { exit 1 }"
    )
    assert result.returncode == 0, "*.pfx files must be blocked by the denylist"


def test_secret_file_is_blocked() -> None:
    result = _ps(
        _DENYLIST_SNIPPET
        + "if (Test-SensitivePath 'my-secret-file.txt') { exit 0 } else { exit 1 }"
    )
    assert result.returncode == 0, "*secret* files must be blocked by the denylist"


def test_credential_file_is_blocked() -> None:
    result = _ps(
        _DENYLIST_SNIPPET
        + "if (Test-SensitivePath 'db-credentials.json') { exit 0 } else { exit 1 }"
    )
    assert result.returncode == 0, "*credential* files must be blocked by the denylist"
