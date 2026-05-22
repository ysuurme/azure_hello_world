import subprocess
import sys


_PROMPT_TEMPLATE = """Generate a conventional commit message for the following diff.

Rules:
- Format: <type>(<scope>): <description>
- Types: feat, fix, refactor, test, docs, chore, perf, ci, build, revert
- Scope: the module, file, or area changed (omit if not obvious)
- Description: imperative mood, <=72 chars, no period at end
- Add a blank line + body only if the change is complex or non-obvious
- Return ONLY the commit message — no explanation, no markdown fences

DIFF:
{diff}"""


def _staged_diff() -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e.stderr.strip()}")
        sys.exit(1)
    except FileNotFoundError:
        print("Git not found. Ensure git is installed and available on PATH.")
        sys.exit(1)


def _claude_cli(prompt: str) -> str | None:
    try:
        result = subprocess.run(
            ["claude", "-p", "-"], input=prompt, capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def _claude_sdk(prompt: str) -> str | None:
    try:
        import anthropic
        from anthropic.types import TextBlock

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if isinstance(block, TextBlock):
                return block.text.strip()
    except Exception:
        pass
    return None


# Future: add _gemini_cli(prompt) here as a third provider slot.


def generate_commit_message(diff: str) -> str:
    prompt = _PROMPT_TEMPLATE.format(diff=diff)

    msg = _claude_cli(prompt)
    if msg:
        return msg

    msg = _claude_sdk(prompt)
    if msg:
        return msg

    print("No AI provider available. Install the Claude CLI or set ANTHROPIC_API_KEY.")
    sys.exit(1)


def _commit(message: str) -> None:
    try:
        subprocess.run(["git", "commit", "-m", message], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Git commit failed: {e.stderr.strip() if e.stderr else e}")
        sys.exit(1)


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    diff = _staged_diff()
    if not diff:
        print("No staged changes. Stage your changes with `git add`.")
        sys.exit(1)

    message = generate_commit_message(diff)
    print(message)

    if not dry_run:
        _commit(message)


if __name__ == "__main__":
    main()
