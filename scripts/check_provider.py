"""
scripts/check_provider.py
─────────────────────────
NeuralCraft Studio — API Connection Tester

Usage:
    python scripts/check_provider.py

Reads credentials from environment (or .env) and sends a minimal
test prompt to the PRIMARY model to verify connectivity.
"""

import os
import sys
from pathlib import Path

# ── Load .env from project root ──────────────────────────────────────────────
try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("[ERROR] python-dotenv is not installed. Run: pip install python-dotenv")

# Walk up until we find a .env or .env.example (project root heuristic)
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")


def _get_required_env(key: str) -> str:
    """Return env var value or exit with a helpful message."""
    value = os.environ.get(key)
    if not value:
        sys.exit(
            f"[ERROR] Required environment variable '{key}' is not set.\n"
            f"        Copy .env.example to .env and fill in your credentials."
        )
    return value


def run_connection_test() -> None:
    """Send a minimal prompt to the primary model and report the result."""
    try:
        from openai import OpenAI, AuthenticationError, APIConnectionError, APIStatusError
    except ImportError:
        sys.exit("[ERROR] openai SDK is not installed. Run: pip install openai")

    api_key  = _get_required_env("PRIMARY_MODEL_API_KEY")
    base_url = os.environ.get("PRIMARY_MODEL_BASE_URL")  # optional override
    model    = _get_required_env("PRIMARY_MODEL_NAME")

    print(f"[INFO] Testing connection to model : {model}")
    print(f"[INFO] Base URL                    : {base_url or '(default OpenAI)'}")

    client_kwargs: dict = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with exactly one word: OK",
                }
            ],
            max_tokens=5,
        )
        reply = response.choices[0].message.content.strip()
        print(f"[SUCCESS] Model responded: '{reply}'")
        print("[SUCCESS] API connection is healthy ✓")

    except AuthenticationError:
        print(
            "[ERROR] Authentication failed (401/403).\n"
            "        Check that PRIMARY_MODEL_API_KEY is correct and active."
        )
        sys.exit(1)

    except APIConnectionError as exc:
        print(
            f"[ERROR] Could not reach the API endpoint.\n"
            f"        URL    : {base_url or 'https://api.openai.com'}\n"
            f"        Reason : {exc.__class__.__name__} — {exc}"
        )
        sys.exit(1)

    except APIStatusError as exc:
        print(
            f"[ERROR] API returned an unexpected status code.\n"
            f"        Status : {exc.status_code}\n"
            f"        Body   : {exc.message}"
        )
        sys.exit(1)

    except Exception as exc:  # noqa: BLE001
        print(
            f"[ERROR] An unexpected error occurred: {exc.__class__.__name__}: {exc}"
        )
        sys.exit(1)


if __name__ == "__main__":
    run_connection_test()
