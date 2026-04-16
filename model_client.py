"""
Client for the diagnostic model endpoint.

Usage:
    # Interactive mode (prompts you for input)
    python model_client.py

    # One-shot mode (pass text as argument)
    python model_client.py "your input text here"

    # Pipe mode
    echo "your text" | python model_client.py -

Requirements:
    pip install requests
"""

import json
import sys
import time
import argparse
from typing import Any

import requests


# ---- Configuration --------------------------------------------------------
ENDPOINT = "https://me-780bd07f496f4391ab60fcdbb637c521.ecs.us-east-1.on.aws/generate"
API_KEY = "REMOVED"

# How long to wait for the model to respond before giving up (seconds).
# Diagnostic / LLM-style models can be slow, so this is generous.
REQUEST_TIMEOUT = 300

# Whether to verify TLS certificates. Keep True unless you know you need otherwise.
VERIFY_TLS = True
# ---------------------------------------------------------------------------


def call_model(text: str, extra_fields: dict | None = None) -> dict[str, Any]:
    """
    Send `text` to the model endpoint and return the parsed JSON response.

    `extra_fields` lets you merge in additional request params (e.g. max_tokens,
    temperature) without editing this function.
    """
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Most "text in -> JSON out" endpoints accept one of these field names.
    # We send the common ones so the server can pick up whichever it expects.
    payload: dict[str, Any] = {
        "text": text,
        "input": text,
        "prompt": text,
    }
    if extra_fields:
        payload.update(extra_fields)

    started = time.monotonic()
    try:
        response = requests.post(
            ENDPOINT,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            verify=VERIFY_TLS,
        )
    except requests.exceptions.Timeout:
        raise SystemExit(f"Request timed out after {REQUEST_TIMEOUT}s. "
                         f"Try increasing REQUEST_TIMEOUT at the top of the script.")
    except requests.exceptions.SSLError as e:
        raise SystemExit(f"TLS error: {e}\n"
                         f"If the server uses a self-signed cert, set VERIFY_TLS = False.")
    except requests.exceptions.ConnectionError as e:
        raise SystemExit(f"Could not connect to the endpoint: {e}")

    elapsed = time.monotonic() - started

    # Raise a helpful error if the server returned a non-2xx status.
    if not response.ok:
        body_preview = response.text[:500]
        raise SystemExit(
            f"HTTP {response.status_code} from server after {elapsed:.1f}s\n"
            f"Response body (first 500 chars):\n{body_preview}"
        )

    # Parse JSON. If the server lied about Content-Type, fall back to raw text.
    try:
        data = response.json()
    except ValueError:
        return {"_raw_text": response.text, "_elapsed_seconds": round(elapsed, 2)}

    # Attach timing info so the caller can see how long it took.
    if isinstance(data, dict):
        data.setdefault("_elapsed_seconds", round(elapsed, 2))
    return data


def read_input(cli_text: str | None) -> str:
    """Get the input text from argv, stdin, or an interactive prompt."""
    if cli_text == "-":
        return sys.stdin.read().strip()
    if cli_text:
        return cli_text
    # Interactive fallback
    print("Enter your text (end with an empty line):")
    lines: list[str] = []
    try:
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send text to the model endpoint.")
    parser.add_argument(
        "text",
        nargs="?",
        help="Input text. Use '-' to read from stdin. Omit for interactive mode.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print the full JSON response instead of trying to pull out a 'result' field.",
    )
    args = parser.parse_args()

    text = read_input(args.text)
    if not text:
        raise SystemExit("No input text provided.")

    print(f"→ Sending {len(text)} chars to the model…", file=sys.stderr)
    result = call_model(text)

    if args.raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Try to show the most likely "answer" field first, then fall back to full JSON.
    for key in ("response", "result", "output", "answer", "text", "generated_text"):
        if isinstance(result, dict) and key in result:
            print(result[key])
            print(f"\n— done in {result.get('_elapsed_seconds', '?')}s —",
                  file=sys.stderr)
            return

    # Unknown shape — just pretty-print everything.
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
