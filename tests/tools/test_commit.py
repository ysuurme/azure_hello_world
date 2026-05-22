import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.tools.commit import (
    _claude_cli,
    _claude_sdk,
    _commit,
    _staged_diff,
    generate_commit_message,
    main,
)


def test_generate_commit_message_uses_cli_when_available() -> None:
    with patch("src.tools.commit._claude_cli", return_value="feat(utils): add helper"):
        result = generate_commit_message("diff --git a/file.py b/file.py\n+new line")

    assert result == "feat(utils): add helper"


def test_generate_commit_message_falls_back_to_sdk() -> None:
    with patch("src.tools.commit._claude_cli", return_value=None):
        with patch(
            "src.tools.commit._claude_sdk",
            return_value="fix(config): correct env loading",
        ):
            result = generate_commit_message("diff")

    assert result == "fix(config): correct env loading"


def test_generate_commit_message_cli_takes_priority_over_sdk() -> None:
    with patch("src.tools.commit._claude_cli", return_value="feat: from cli"):
        with patch("src.tools.commit._claude_sdk", return_value="feat: from sdk") as mock_sdk:
            result = generate_commit_message("diff")

    mock_sdk.assert_not_called()
    assert result == "feat: from cli"


def test_generate_commit_message_exits_when_both_providers_fail() -> None:
    with patch("src.tools.commit._claude_cli", return_value=None):
        with patch("src.tools.commit._claude_sdk", return_value=None):
            with pytest.raises(SystemExit):
                generate_commit_message("diff")


# --- _staged_diff ---


def test_staged_diff_returns_stdout() -> None:
    mock_result = MagicMock()
    mock_result.stdout = "diff --git a/file.py"
    with patch("src.tools.commit.subprocess.run", return_value=mock_result):
        assert _staged_diff() == "diff --git a/file.py"


def test_staged_diff_exits_on_git_error() -> None:
    err = subprocess.CalledProcessError(1, "git", stderr="fatal error")
    with patch("src.tools.commit.subprocess.run", side_effect=err):
        with pytest.raises(SystemExit):
            _staged_diff()


def test_staged_diff_exits_when_git_not_found() -> None:
    with patch("src.tools.commit.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit):
            _staged_diff()


# --- _claude_cli ---


def test_claude_cli_returns_stripped_output_on_success() -> None:
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "feat: add feature\n"
    with patch("src.tools.commit.subprocess.run", return_value=mock_result):
        assert _claude_cli("prompt") == "feat: add feature"


def test_claude_cli_returns_none_on_nonzero_exit() -> None:
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    with patch("src.tools.commit.subprocess.run", return_value=mock_result):
        assert _claude_cli("prompt") is None


def test_claude_cli_returns_none_when_not_found() -> None:
    with patch("src.tools.commit.subprocess.run", side_effect=FileNotFoundError):
        assert _claude_cli("prompt") is None


# --- _claude_sdk ---


def test_claude_sdk_returns_text_from_response() -> None:
    from anthropic.types import TextBlock

    real_block = TextBlock(text="fix: correct issue", type="text")
    mock_response = MagicMock()
    mock_response.content = [real_block]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    with patch("anthropic.Anthropic", return_value=mock_client):
        result = _claude_sdk("prompt")
    assert result == "fix: correct issue"


def test_claude_sdk_returns_none_on_exception() -> None:
    import anthropic

    with patch.object(anthropic, "Anthropic", side_effect=Exception("api error")):
        assert _claude_sdk("prompt") is None


# --- _commit ---


def test_commit_runs_git_commit() -> None:
    with patch("src.tools.commit.subprocess.run") as mock_run:
        _commit("feat: test")
    mock_run.assert_called_once()


def test_commit_exits_on_git_error() -> None:
    err = subprocess.CalledProcessError(1, "git", stderr="conflict")
    with patch("src.tools.commit.subprocess.run", side_effect=err):
        with pytest.raises(SystemExit):
            _commit("feat: test")


# --- main ---


def test_main_exits_when_no_staged_changes() -> None:
    with patch("src.tools.commit._staged_diff", return_value=""):
        with pytest.raises(SystemExit):
            main()


def test_main_dry_run_skips_commit() -> None:
    with patch("src.tools.commit._staged_diff", return_value="some diff"):
        with patch("src.tools.commit.generate_commit_message", return_value="feat: thing"):
            with patch("src.tools.commit._commit") as mock_commit:
                with patch.object(sys, "argv", ["commit", "--dry-run"]):
                    main()
    mock_commit.assert_not_called()


def test_main_commits_when_not_dry_run() -> None:
    with patch("src.tools.commit._staged_diff", return_value="some diff"):
        with patch("src.tools.commit.generate_commit_message", return_value="feat: thing"):
            with patch("src.tools.commit._commit") as mock_commit:
                with patch.object(sys, "argv", ["commit"]):
                    main()
    mock_commit.assert_called_once_with("feat: thing")
