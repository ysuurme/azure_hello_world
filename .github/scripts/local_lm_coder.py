#!/usr/bin/env python3
"""
Local LM code generation helper.

Calls LM Studio's Anthropic-compatible endpoint at /v1/messages.
Claude uses this via its Bash tool to delegate code generation to the local GPU model.

Usage:
    uv run python .github/scripts/local_lm_coder.py --task "write a function that..."
    uv run python .github/scripts/local_lm_coder.py --task "..." --context "$(cat src/foo.py)"

Exit codes: 0 = success, 1 = bad response, 2 = connection refused (LM Studio not running).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return {}
    env: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def call_local_lm(task: str, context: str, model: str, base_url: str) -> str:
    content = f"Context:\n{context}\n\nTask:\n{task}" if context else task
    payload = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": content}],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/v1/messages",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except urllib.error.URLError as exc:
        print(f"Connection error — is LM Studio running? {exc}", file=sys.stderr)
        sys.exit(2)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"Unexpected response format: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Delegate code generation to local LM")
    parser.add_argument("--task", required=True, help="What to generate or implement")
    parser.add_argument("--context", default="", help="Relevant existing code or file content")
    args = parser.parse_args()

    env = load_dotenv()
    model = os.environ.get("LOCAL_AI_MODEL") or env.get("LOCAL_AI_MODEL", "nerdsking-python-coder-3b-i")
    base_url = os.environ.get("LOCAL_AI_URL") or env.get("LOCAL_AI_URL", "http://127.0.0.1:1234")

    print(call_local_lm(args.task, args.context, model, base_url))


if __name__ == "__main__":
    main()
