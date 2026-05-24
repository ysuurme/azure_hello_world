from pathlib import Path
from unittest.mock import patch

import pytest

from src.tools.setup import (
    load_answers,
    main,
    prompt_for_answers,
    replace_tokens,
    set_github_variable,
)

# --- load_answers ---


def test_load_answers_parses_yaml(tmp_path: Path) -> None:
    answers_file = tmp_path / ".copier-answers.yml"
    answers_file.write_text(
        "project_name: my-project\ndescription: My desc\nproject_type: application\n",
        encoding="utf-8",
    )
    result = load_answers(answers_file)
    assert result["project_name"] == "my-project"
    assert result["description"] == "My desc"
    assert result["project_type"] == "application"


def test_load_answers_returns_all_keys_including_private(tmp_path: Path) -> None:
    answers_file = tmp_path / ".copier-answers.yml"
    answers_file.write_text(
        "_commit: abc123\n_src_path: /tmp/tpl\nproject_name: proj\n",
        encoding="utf-8",
    )
    result = load_answers(answers_file)
    assert result["project_name"] == "proj"
    assert "_commit" in result


# --- replace_tokens ---


def test_replace_tokens_substitutes_all_three() -> None:
    content = "# __PROJECT_NAME__\n__PROJECT_DESCRIPTION__\nType: __PROJECT_TYPE__"
    answers = {
        "project_name": "my-app",
        "description": "A great app",
        "project_type": "application",
    }
    result = replace_tokens(content, answers)
    assert "my-app" in result
    assert "A great app" in result
    assert "application" in result
    assert "__PROJECT_NAME__" not in result
    assert "__PROJECT_DESCRIPTION__" not in result
    assert "__PROJECT_TYPE__" not in result


def test_replace_tokens_is_idempotent() -> None:
    content = "# __PROJECT_NAME__\n__PROJECT_DESCRIPTION__\nType: __PROJECT_TYPE__"
    answers = {
        "project_name": "my-app",
        "description": "A great app",
        "project_type": "application",
    }
    first = replace_tokens(content, answers)
    second = replace_tokens(first, answers)
    assert first == second


def test_replace_tokens_no_op_when_already_replaced() -> None:
    content = "# my-app\nA great app\nType: application"
    answers = {
        "project_name": "my-app",
        "description": "A great app",
        "project_type": "application",
    }
    result = replace_tokens(content, answers)
    assert result == content


def test_replace_tokens_uses_empty_string_for_missing_key() -> None:
    content = "# __PROJECT_NAME__"
    result = replace_tokens(content, {})
    assert result == "# "


# --- set_github_variable ---


def test_set_github_variable_calls_gh_cli() -> None:
    with patch("src.tools.setup.subprocess.run") as mock_run:
        set_github_variable("application")
    mock_run.assert_called_once_with(
        ["gh", "variable", "set", "PROJECT_TYPE", "--body", "application"],
        check=True,
    )


# --- prompt_for_answers ---


def test_prompt_for_answers_returns_user_input() -> None:
    inputs = iter(["my-app", "My description", "agent"])
    with patch("builtins.input", side_effect=inputs):
        result = prompt_for_answers()
    assert result == {
        "project_name": "my-app",
        "description": "My description",
        "project_type": "agent",
    }


def test_prompt_for_answers_uses_defaults_on_empty_input() -> None:
    with patch("builtins.input", return_value=""):
        result = prompt_for_answers()
    assert result["project_name"] == "my-project"
    assert result["description"] == "A new project"
    assert result["project_type"] == "application"


def test_prompt_for_answers_uses_default_for_empty_field_only() -> None:
    inputs = iter(["custom-name", "", ""])
    with patch("builtins.input", side_effect=inputs):
        result = prompt_for_answers()
    assert result["project_name"] == "custom-name"
    assert result["description"] == "A new project"
    assert result["project_type"] == "application"


# --- main ---


def test_main_uses_fallback_when_answers_file_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    context_file = tmp_path / "CONTEXT.md"
    context_file.write_text(
        "# __PROJECT_NAME__\n__PROJECT_DESCRIPTION__\nType: __PROJECT_TYPE__\n",
        encoding="utf-8",
    )

    inputs = iter(["fallback-proj", "Fallback desc", "application"])
    with (
        patch("src.tools.setup._CONTEXT_FILE", context_file),
        patch("builtins.input", side_effect=inputs),
        patch("src.tools.setup.set_github_variable") as mock_gh,
    ):
        main()

    result = context_file.read_text(encoding="utf-8")
    assert "fallback-proj" in result
    assert "Fallback desc" in result
    assert "application" in result
    assert "__PROJECT_NAME__" not in result
    mock_gh.assert_called_once_with("application")


def test_main_replaces_tokens_and_sets_github_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    answers_file = tmp_path / ".copier-answers.yml"
    answers_file.write_text(
        "project_name: hello-world\ndescription: Hello desc\nproject_type: agent\n",
        encoding="utf-8",
    )

    context_file = tmp_path / "CONTEXT.md"
    context_file.write_text(
        "# __PROJECT_NAME__\n__PROJECT_DESCRIPTION__\nType: __PROJECT_TYPE__\n",
        encoding="utf-8",
    )

    with (
        patch("src.tools.setup._ANSWERS_FILE", answers_file),
        patch("src.tools.setup._CONTEXT_FILE", context_file),
        patch("src.tools.setup.set_github_variable") as mock_gh,
    ):
        main()

    result = context_file.read_text(encoding="utf-8")
    assert "hello-world" in result
    assert "Hello desc" in result
    assert "agent" in result
    assert "__PROJECT_NAME__" not in result
    mock_gh.assert_called_once_with("agent")


def test_main_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    answers_file = tmp_path / ".copier-answers.yml"
    answers_file.write_text(
        "project_name: hello-world\ndescription: Hello desc\nproject_type: agent\n",
        encoding="utf-8",
    )

    context_file = tmp_path / "CONTEXT.md"
    context_file.write_text(
        "# __PROJECT_NAME__\n__PROJECT_DESCRIPTION__\nType: __PROJECT_TYPE__\n",
        encoding="utf-8",
    )

    with (
        patch("src.tools.setup._ANSWERS_FILE", answers_file),
        patch("src.tools.setup._CONTEXT_FILE", context_file),
        patch("src.tools.setup.set_github_variable"),
    ):
        main()
        content_after_first = context_file.read_text(encoding="utf-8")
        main()
        content_after_second = context_file.read_text(encoding="utf-8")

    assert content_after_first == content_after_second
