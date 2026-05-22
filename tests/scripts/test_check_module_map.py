"""Tests for .github/scripts/check-module-map.ps1."""

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parent.parent.parent / ".github" / "scripts" / "check-module-map.ps1"
)
PWSH = shutil.which("pwsh") or "pwsh"

pytestmark = pytest.mark.skipif(
    not shutil.which("pwsh"),
    reason="pwsh not available",
)

_MINIMAL_CONTEXT = """\
# CONTEXT.md

## Module Map

| Module | Path | Bounded Context | Entry points |
|---|---|---|---|
| config | `src/config.py` | `src/` | `Settings` |
"""


def _context_with(*domains: str) -> str:
    rows = "\n".join(f"| {d} | `src/{d}/` | `src/{d}/` | TBD |" for d in domains)
    return _MINIMAL_CONTEXT + rows + "\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    )


def _commit(repo: Path, files: dict[str, str | None], message: str) -> str:
    for rel_path, content in files.items():
        full = repo / rel_path
        if content is None:
            if full.exists():
                full.unlink()
                parent = full.parent
                while parent != repo:
                    try:
                        parent.rmdir()
                        parent = parent.parent
                    except OSError:
                        break
        else:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _setup_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    _git(tmp_path, "config", "user.email", "test@test.com")
    _git(tmp_path, "config", "user.name", "Test User")
    return tmp_path


def _run(repo: Path, base_ref: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PWSH, "-NoProfile", "-File", str(SCRIPT), "-BaseRef", base_ref],
        cwd=repo,
        capture_output=True,
        text=True,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_no_new_domain_passes(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    base = _commit(repo, {"CONTEXT.md": _MINIMAL_CONTEXT}, "base")
    _commit(repo, {"README.md": "# readme"}, "add readme")
    result = _run(repo, base)
    assert result.returncode == 0


def test_new_domain_missing_row_fails(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    base = _commit(repo, {"CONTEXT.md": _MINIMAL_CONTEXT}, "base")
    _commit(repo, {"src/newdomain/__init__.py": ""}, "add domain without row")
    result = _run(repo, base)
    assert result.returncode == 1
    assert "src/newdomain/" in result.stdout


def test_new_domain_with_row_passes(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    base = _commit(repo, {"CONTEXT.md": _MINIMAL_CONTEXT}, "base")
    _commit(
        repo,
        {
            "src/newdomain/__init__.py": "",
            "CONTEXT.md": _context_with("newdomain"),
        },
        "add domain with row",
    )
    result = _run(repo, base)
    assert result.returncode == 0


def test_renamed_domain_passes(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    base = _commit(
        repo,
        {
            "src/olddomain/__init__.py": "# old",
            "CONTEXT.md": _context_with("olddomain"),
        },
        "base with olddomain",
    )
    _commit(
        repo,
        {
            "src/olddomain/__init__.py": None,
            "src/newdomain/__init__.py": "",
            "CONTEXT.md": _context_with("newdomain"),
        },
        "rename olddomain to newdomain",
    )
    result = _run(repo, base)
    assert result.returncode == 0


def test_multiple_new_domains_one_missing_fails(tmp_path: Path) -> None:
    repo = _setup_repo(tmp_path)
    base = _commit(repo, {"CONTEXT.md": _MINIMAL_CONTEXT}, "base")
    _commit(
        repo,
        {
            "src/domain_a/__init__.py": "",
            "src/domain_b/__init__.py": "",
            "CONTEXT.md": _context_with("domain_a"),
        },
        "add two domains but only one row",
    )
    result = _run(repo, base)
    assert result.returncode == 1
    assert "src/domain_b/" in result.stdout
