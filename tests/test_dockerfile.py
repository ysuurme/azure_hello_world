"""Content tests for Dockerfile and .dockerignore at the project root."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"


def test_dockerfile_exists() -> None:
    assert DOCKERFILE.exists(), "Dockerfile must exist at project root"


def test_dockerignore_exists() -> None:
    assert DOCKERIGNORE.exists(), ".dockerignore must exist at project root"


def test_dockerfile_no_pip() -> None:
    assert "pip install" not in DOCKERFILE.read_text(), "Dockerfile must not contain 'pip install'"


def test_dockerfile_no_jinja2() -> None:
    assert "{{" not in DOCKERFILE.read_text(), "Dockerfile must not contain Jinja2 syntax"


def test_dockerignore_no_jinja2() -> None:
    assert "{{" not in DOCKERIGNORE.read_text(), ".dockerignore must not contain Jinja2 syntax"


def test_dockerfile_two_stage_build() -> None:
    content = DOCKERFILE.read_text()
    assert "AS builder" in content, "Dockerfile must have a 'builder' stage"
    assert "AS runtime" in content, "Dockerfile must have a 'runtime' stage"


def test_dockerfile_uv_binary_copy() -> None:
    assert "ghcr.io/astral-sh/uv" in DOCKERFILE.read_text(), (
        "Dockerfile must copy the uv binary from ghcr.io/astral-sh/uv"
    )


def test_dockerfile_no_hard_entrypoint() -> None:
    assert "ENTRYPOINT" not in DOCKERFILE.read_text(), (
        "Dockerfile must not contain a hard ENTRYPOINT — command is caller-specified via docker-compose"
    )


def test_dockerfile_exposes_backend_port() -> None:
    assert "8000" in DOCKERFILE.read_text(), "Dockerfile must EXPOSE backend port 8000"


def test_dockerfile_exposes_frontend_port() -> None:
    assert "8501" in DOCKERFILE.read_text(), "Dockerfile must EXPOSE Streamlit frontend port 8501"


def test_dockerfile_env_vars() -> None:
    content = DOCKERFILE.read_text()
    assert "UV_COMPILE_BYTECODE" in content
    assert "UV_LINK_MODE" in content
    assert "PYTHONDONTWRITEBYTECODE" in content
    assert "PYTHONUNBUFFERED" in content


def test_dockerignore_excludes_venv_and_env() -> None:
    content = DOCKERIGNORE.read_text()
    assert ".venv/" in content, ".dockerignore must exclude .venv/"
    assert ".env" in content, ".dockerignore must exclude .env"


def test_dockerfile_python313_builder() -> None:
    assert "python3.13-bookworm" in DOCKERFILE.read_text(), "Dockerfile builder stage must use python3.13-bookworm"


def test_dockerfile_python313_runtime() -> None:
    assert "python:3.13" in DOCKERFILE.read_text(), "Dockerfile runtime stage must use python:3.13"
