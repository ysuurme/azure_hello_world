"""Populate CONTEXT.md sentinel tokens from .copier-answers.yml."""

import subprocess
import sys
from pathlib import Path

import yaml

_SENTINELS: dict[str, str] = {
    "__PROJECT_NAME__": "project_name",
    "__PROJECT_DESCRIPTION__": "description",
    "__PROJECT_TYPE__": "project_type",
}

_CONTEXT_FILE = Path("CONTEXT.md")
_ANSWERS_FILE = Path(".copier-answers.yml")

# (key, prompt label, default value)
_PROMPTS: list[tuple[str, str, str]] = [
    ("project_name", "Project name", "my-project"),
    ("description", "Project description", "A new project"),
    ("project_type", "Project type (application/agent/data)", "application"),
]


def load_answers(answers_path: Path) -> dict:
    return yaml.safe_load(answers_path.read_text(encoding="utf-8"))


def prompt_for_answers() -> dict:
    """Prompt the user for required fields; pressing Enter accepts the shown default."""
    answers = {}
    for key, label, default in _PROMPTS:
        value = input(f"{label} [{default}]: ").strip()
        answers[key] = value if value else default
    return answers


def replace_sentinels(content: str, answers: dict) -> str:
    for sentinel, key in _SENTINELS.items():
        value = answers.get(key, "")
        content = content.replace(sentinel, str(value))
    return content


def set_github_variable(project_type: str) -> None:
    subprocess.run(
        ["gh", "variable", "set", "PROJECT_TYPE", "--body", project_type],
        check=True,
    )


def main() -> None:
    if _ANSWERS_FILE.exists():
        answers = load_answers(_ANSWERS_FILE)
    else:
        print(
            f"Warning: {_ANSWERS_FILE} not found. Enter values manually (press Enter for defaults).",
            file=sys.stderr,
        )
        answers = prompt_for_answers()

    content = _CONTEXT_FILE.read_text(encoding="utf-8")
    updated = replace_sentinels(content, answers)
    _CONTEXT_FILE.write_text(updated, encoding="utf-8")

    project_type = answers.get("project_type", "")
    set_github_variable(project_type)


if __name__ == "__main__":
    main()
