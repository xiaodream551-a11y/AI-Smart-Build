# -*- coding: utf-8 -*-
"""RevitClaw LLM client with conversation management.

Works in both CPython (Mac offline server) and IronPython (Revit).
Uses urllib so it runs without third-party HTTP libraries.
"""

import json
import re
import ssl

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen  # type: ignore[no-redef]

from ai.prompt import SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# JSON command extraction
# ---------------------------------------------------------------------------

def parse_command_from_reply(text):
    """Extract a JSON command dict from an LLM reply string.

    Handles:
    - Pure JSON object/array
    - Markdown fenced code blocks (```json ... ```)
    - Mixed prose + embedded JSON

    Returns a dict with an "action" key, or None if no valid command found.
    For JSON arrays, wraps them in {"action": "batch", "params": {"commands": [...]}}.
    """
    if not text or not text.strip():
        return None

    cleaned = text.strip()

    # Strip markdown fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # Try direct parse
    result = _try_parse_json(cleaned)
    if result is not None:
        return _normalize_command(result)

    # Scan for the first balanced { ... } or [ ... ]
    for opener, closer in [("{", "}"), ("[", "]")]:
        extracted = _extract_balanced(cleaned, opener, closer)
        if extracted is not None:
            result = _try_parse_json(extracted)
            if result is not None:
                return _normalize_command(result)

    return None


def _try_parse_json(text):
    """Attempt json.loads; return parsed object or None."""
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


def _extract_balanced(text, opener, closer):
    """Find the first balanced substring delimited by opener/closer."""
    start = text.find(opener)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            if in_string:
                escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


def _normalize_command(parsed):
    """Normalize parsed JSON into a command dict with an 'action' key."""
    if isinstance(parsed, list):
        return {"action": "batch", "params": {"commands": parsed}}

    if isinstance(parsed, dict) and "action" in parsed:
        return parsed

    return None


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------

class RevitClawLLMClient(object):
    """LLM client with conversation state management.

    Parameters
    ----------
    api_url : str
        Full chat completions endpoint URL.
    api_key : str
        Bearer token for the API.
    model : str
        Model identifier (e.g. "glm-4-flash", "deepseek-chat").
    max_turns : int
        Maximum number of user/assistant turn pairs to keep.
    timeout_s : int
        HTTP request timeout in seconds.
    """

    def __init__(self, api_url, api_key, model, max_turns=20, timeout_s=30):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.max_turns = max_turns
        self.timeout_s = timeout_s
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    def reset(self):
        """Clear conversation history, keeping only the system prompt."""
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    def chat(self, user_message):
        """Send a user message and return (reply_text, command_or_None).

        Appends the user message, trims history, calls the API,
        appends the assistant reply, and parses any JSON command.
        """
        self.conversation.append({"role": "user", "content": user_message})
        self._trim_conversation()

        reply_text = self._call_api()

        self.conversation.append({"role": "assistant", "content": reply_text})
        self._trim_conversation()

        command = parse_command_from_reply(reply_text)
        return reply_text, command

    def _build_payload(self):
        """Build the request payload dict."""
        return {
            "model": self.model,
            "messages": list(self.conversation),
            "temperature": 0.1,
        }

    def _trim_conversation(self):
        """Keep system message + last max_turns*2 messages."""
        if len(self.conversation) <= 1:
            return

        system_msg = self.conversation[0]
        history = self.conversation[1:]

        max_history = self.max_turns * 2
        if len(history) > max_history:
            history = history[-max_history:]

        self.conversation = [system_msg] + history

    def _call_api(self):
        """POST to the chat completions endpoint and return the reply text.

        Uses urllib with a permissive SSL context for macOS dev environments
        where system certificates may not be configured.
        """
        payload = json.dumps(self._build_payload(), ensure_ascii=False).encode("utf-8")

        req = Request(self.api_url, data=payload)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Authorization", "Bearer {}".format(self.api_key))

        # Permissive SSL context for dev -- avoids macOS certificate errors
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        response = urlopen(req, timeout=self.timeout_s, context=ctx)
        raw = response.read().decode("utf-8")
        response.close()

        result = json.loads(raw)
        return result["choices"][0]["message"]["content"]
