"""Tests for the field-provisioning helpers in .github/scripts/setup.ps1.

Each test runs an inline PowerShell snippet that replicates the exact business
logic from setup.ps1, avoiding the need for a live GitHub Project while still
verifying the real decision rules.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

PWSH = shutil.which("pwsh") or "pwsh"

pytestmark = pytest.mark.skipif(
    not shutil.which("pwsh"),
    reason="pwsh not available",
)


def _ps(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PWSH, "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Set-EnvVar — pure filesystem helper (no gh calls)
# ---------------------------------------------------------------------------

_SET_ENV_VAR_FN = """\
function Set-EnvVar([string]$Path, [string]$Key, [string]$Value) {
    $lines  = if (Test-Path $Path) { Get-Content $Path } else { @() }
    $found  = $false
    $result = foreach ($line in $lines) {
        if ($line -match "^\\s*$([regex]::Escape($Key))\\s*=") {
            "$Key=$Value"
            $found = $true
        } else {
            $line
        }
    }
    if (-not $found) { $result += "$Key=$Value" }
    $result | Out-File $Path -Encoding utf8
}
"""


def test_set_env_var_creates_key_when_file_missing(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    result = _ps(
        _SET_ENV_VAR_FN
        + f'Set-EnvVar "{env_file}" "MY_KEY" "my_value"\n'
        + f'$c = Get-Content "{env_file}" -Raw\n'
        + "if ($c -match 'MY_KEY=my_value') { exit 0 } else { exit 1 }"
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_set_env_var_updates_existing_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("MY_KEY=old_value\n", encoding="utf-8")
    result = _ps(
        _SET_ENV_VAR_FN
        + f'Set-EnvVar "{env_file}" "MY_KEY" "new_value"\n'
        + f'$c = Get-Content "{env_file}" -Raw\n'
        + "if ($c -match 'MY_KEY=new_value' -and $c -notmatch 'old_value') { exit 0 } else { exit 1 }"
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_set_env_var_preserves_other_keys(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER=kept\nMY_KEY=old\n", encoding="utf-8")
    result = _ps(
        _SET_ENV_VAR_FN
        + f'Set-EnvVar "{env_file}" "MY_KEY" "new"\n'
        + f'$c = Get-Content "{env_file}" -Raw\n'
        + "if ($c -match 'OTHER=kept' -and $c -match 'MY_KEY=new') { exit 0 } else { exit 1 }"
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Field detection logic (mirrors setup.ps1 filter expressions)
# ---------------------------------------------------------------------------

_FIELD_DETECTION_FNS = """\
function Get-EstimateField([array]$Fields) {
    return $Fields | Where-Object { $_.name -match '^estimate$' } | Select-Object -First 1
}
function Get-PriorityField([array]$Fields) {
    return $Fields |
        Where-Object { $_.type -eq 'ProjectV2SingleSelectField' -and $_.name -match '^priority$' } |
        Select-Object -First 1
}
"""


def test_estimate_field_detected_when_present() -> None:
    result = _ps(
        _FIELD_DETECTION_FNS
        + """
$fields = @([PSCustomObject]@{ name = 'Estimate'; type = 'ProjectV2NumberField'; id = 'f1' })
if (Get-EstimateField $fields) { exit 0 } else { exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_estimate_field_not_detected_when_absent() -> None:
    result = _ps(
        _FIELD_DETECTION_FNS
        + """
$fields = @([PSCustomObject]@{ name = 'Status'; type = 'ProjectV2SingleSelectField'; id = 'f1' })
if (-not (Get-EstimateField $fields)) { exit 0 } else { exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_priority_field_detected_when_present() -> None:
    result = _ps(
        _FIELD_DETECTION_FNS
        + """
$fields = @([PSCustomObject]@{ name = 'Priority'; type = 'ProjectV2SingleSelectField'; id = 'f2'; options = @() })
if (Get-PriorityField $fields) { exit 0 } else { exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_priority_field_not_detected_when_absent() -> None:
    result = _ps(
        _FIELD_DETECTION_FNS
        + """
$fields = @([PSCustomObject]@{ name = 'Estimate'; type = 'ProjectV2NumberField'; id = 'f1' })
if (-not (Get-PriorityField $fields)) { exit 0 } else { exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_priority_field_not_matched_when_wrong_type() -> None:
    result = _ps(
        _FIELD_DETECTION_FNS
        + """
$fields = @([PSCustomObject]@{ name = 'Priority'; type = 'ProjectV2NumberField'; id = 'f1' })
if (-not (Get-PriorityField $fields)) { exit 0 } else { exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Field-provisioning command arguments (gh is shadowed by a mock function)
# ---------------------------------------------------------------------------

_MOCK_GH = """\
$script:ghCallArgs = @()
function gh {
    $script:ghCallArgs += ,$args
    $global:LASTEXITCODE = 0
}
"""


def test_estimate_field_create_called_with_number_type() -> None:
    result = _ps(
        _MOCK_GH
        + """
$fields = @()
$estimateField = $fields | Where-Object { $_.name -match '^estimate$' } | Select-Object -First 1
if (-not $estimateField) {
    gh project field-create 1 --owner testorg --name "Estimate" --data-type NUMBER 2>&1 | Out-Null
}
$call = ($script:ghCallArgs[0]) -join ' '
if ($call -match 'field-create' -and $call -match 'NUMBER' -and $call -match 'Estimate') {
    exit 0
} else {
    Write-Host "Unexpected call: $call"
    exit 1
}
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_priority_field_create_called_with_single_select_and_options() -> None:
    result = _ps(
        _MOCK_GH
        + """
$fields = @()
$priorityField = $fields |
    Where-Object { $_.type -eq 'ProjectV2SingleSelectField' -and $_.name -match '^priority$' } |
    Select-Object -First 1
if (-not $priorityField) {
    gh project field-create 1 --owner testorg --name "Priority" --data-type SINGLE_SELECT --single-select-options "P0,P1,P2,P3,P4" 2>&1 | Out-Null
}
$call = ($script:ghCallArgs[0]) -join ' '
if ($call -match 'field-create' -and $call -match 'SINGLE_SELECT' -and $call -match 'P0,P1,P2,P3,P4') {
    exit 0
} else {
    Write-Host "Unexpected call: $call"
    exit 1
}
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_create_called_when_estimate_field_exists() -> None:
    result = _ps(
        _MOCK_GH
        + """
$fields = @([PSCustomObject]@{ name = 'Estimate'; type = 'ProjectV2NumberField'; id = 'f1' })
$estimateField = $fields | Where-Object { $_.name -match '^estimate$' } | Select-Object -First 1
if (-not $estimateField) {
    gh project field-create 1 --owner testorg --name "Estimate" --data-type NUMBER 2>&1 | Out-Null
}
if ($script:ghCallArgs.Count -eq 0) { exit 0 } else { exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_create_called_when_priority_field_exists() -> None:
    result = _ps(
        _MOCK_GH
        + """
$fields = @([PSCustomObject]@{ name = 'Priority'; type = 'ProjectV2SingleSelectField'; id = 'f2'; options = @() })
$priorityField = $fields |
    Where-Object { $_.type -eq 'ProjectV2SingleSelectField' -and $_.name -match '^priority$' } |
    Select-Object -First 1
if (-not $priorityField) {
    gh project field-create 1 --owner testorg --name "Priority" --data-type SINGLE_SELECT --single-select-options "P0,P1,P2,P3,P4" 2>&1 | Out-Null
}
if ($script:ghCallArgs.Count -eq 0) { exit 0 } else { exit 1 }
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr
