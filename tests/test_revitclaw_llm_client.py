# -*- coding: utf-8 -*-
"""Tests for RevitClaw IronPython LLM client."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import offline_runtime
offline_runtime.bootstrap()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "AISmartBuild.extension" / "lib"))

from revitclaw.llm_client import RevitClawLLMClient, parse_command_from_reply


class TestParseCommandFromReply:
    def test_pure_json(self):
        text = '{"action": "create_column", "params": {"x": 0}}'
        cmd = parse_command_from_reply(text)
        assert cmd["action"] == "create_column"

    def test_markdown_fenced(self):
        text = '```json\n{"action": "create_beam", "params": {}}\n```'
        cmd = parse_command_from_reply(text)
        assert cmd["action"] == "create_beam"

    def test_mixed_text_with_json(self):
        text = u'\u597d\u7684\uff0c\u6211\u6765\u521b\u5efa\u3002\n{"action": "create_column", "params": {"x": 0}}'
        cmd = parse_command_from_reply(text)
        assert cmd["action"] == "create_column"

    def test_plain_text_returns_none(self):
        assert parse_command_from_reply(u"\u6ca1\u6709JSON\u5185\u5bb9") is None

    def test_batch_array(self):
        text = '[{"action": "create_column"}, {"action": "create_beam"}]'
        cmd = parse_command_from_reply(text)
        assert cmd["action"] == "batch"
        assert len(cmd["params"]["commands"]) == 2


class TestRevitClawLLMClient:
    def test_init_loads_config(self):
        client = RevitClawLLMClient(
            api_url="https://example.com/v1/chat/completions",
            api_key="test-key",
            model="glm-4-flash",
        )
        assert client.api_url == "https://example.com/v1/chat/completions"
        assert client.model == "glm-4-flash"

    def test_build_payload(self):
        client = RevitClawLLMClient(
            api_url="https://example.com/v1/chat/completions",
            api_key="test-key",
            model="glm-4-flash",
        )
        client.conversation = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "test"},
        ]
        payload = client._build_payload()
        assert payload["model"] == "glm-4-flash"
        assert len(payload["messages"]) == 2

    def test_conversation_trimming(self):
        client = RevitClawLLMClient(
            api_url="https://example.com/v1/chat/completions",
            api_key="test-key",
            model="glm-4-flash",
            max_turns=2,
        )
        client.conversation = [{"role": "system", "content": "prompt"}]
        # Add 5 turn pairs (10 messages)
        for i in range(5):
            client.conversation.append({"role": "user", "content": "q{}".format(i)})
            client.conversation.append({"role": "assistant", "content": "a{}".format(i)})
        client._trim_conversation()
        # system + max_turns*2 = 1 + 4 = 5
        assert len(client.conversation) == 5
        assert client.conversation[0]["role"] == "system"

    def test_reset_clears_conversation(self):
        client = RevitClawLLMClient(
            api_url="https://example.com/v1/chat/completions",
            api_key="test-key",
            model="glm-4-flash",
        )
        client.conversation.append({"role": "user", "content": "test"})
        client.reset()
        assert len(client.conversation) == 1
        assert client.conversation[0]["role"] == "system"
