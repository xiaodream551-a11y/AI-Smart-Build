# -*- coding: utf-8 -*-
"""End-to-end integration tests: user input -> client.chat() -> parse_command -> normalize -> dispatch."""

import json
import sys
import types

import pytest

from tools.offline_runtime import make_story_levels

from ai.client import DeepSeekClient
from ai.parser import parse_command, normalize_command, dispatch_command


def _make_api_response(content):
    """Build a mock DeepSeek API JSON response string."""
    return json.dumps({
        "choices": [
            {"message": {"content": content}}
        ]
    })


def _make_client(monkeypatch, reply_content):
    """Create a DeepSeekClient with _http_post patched to return *reply_content*."""
    client = DeepSeekClient(api_key="test-key")
    monkeypatch.setattr(
        client,
        "_http_post",
        lambda payload, timeout_ms=None: _make_api_response(reply_content),
    )
    return client


# ---------------------------------------------------------------------------
# Scenario 1: Normal create_column flow
# ---------------------------------------------------------------------------

class TestCreateColumnFlow:
    """Mock the API returning a valid create_column JSON and verify the full chain."""

    MOCK_REPLY = json.dumps({
        "action": "create_column",
        "params": {
            "x": 6000,
            "y": 0,
            "base_floor": 1,
            "top_floor": 2,
            "section": "500x500",
        },
    })

    def test_client_returns_reply(self, monkeypatch):
        client = _make_client(monkeypatch, self.MOCK_REPLY)
        reply = client.chat(u"在坐标(6000,0)处创建一根500x500的柱子")
        assert "create_column" in reply

    def test_parse_and_normalize(self, monkeypatch):
        client = _make_client(monkeypatch, self.MOCK_REPLY)
        reply = client.chat(u"在坐标(6000,0)处创建一根500x500的柱子")
        command = parse_command(reply)

        assert command["action"] == "create_column"
        assert command["params"]["x"] == 6000
        assert command["params"]["y"] == 0
        assert command["params"]["base_floor"] == 1
        assert command["params"]["top_floor"] == 2
        assert command["params"]["section"] == "500x500"

    def test_dispatch_calls_engine(self, monkeypatch):
        records = {}
        fake_module = types.ModuleType("engine.column")

        def fake_create_column(doc, x, y, base_level, top_level, section):
            records["x"] = x
            records["y"] = y
            records["base_level"] = base_level.Name
            records["top_level"] = top_level.Name
            records["section"] = section

        fake_module.create_column = fake_create_column
        monkeypatch.setitem(sys.modules, "engine.column", fake_module)

        client = _make_client(monkeypatch, self.MOCK_REPLY)
        reply = client.chat(u"在坐标(6000,0)处创建一根500x500的柱子")
        command = parse_command(reply)

        levels = make_story_levels(3)
        result = dispatch_command(None, command, levels)

        assert "柱" in result
        assert records["x"] == 6000
        assert records["section"] == "500x500"
        assert records["base_level"] == u"\u00b10.000"
        assert records["top_level"] == "F1"


# ---------------------------------------------------------------------------
# Scenario 2: Normal generate_frame flow
# ---------------------------------------------------------------------------

class TestGenerateFrameFlow:
    """Mock the API returning a generate_frame command and verify dispatch."""

    MOCK_REPLY = json.dumps({
        "action": "generate_frame",
        "params": {
            "x_spans": [6000, 6000],
            "y_spans": [6000],
            "num_floors": 3,
            "floor_height": 3600,
            "column_section": "500x500",
            "beam_section": "300x600",
        },
    })

    def test_full_chain(self, monkeypatch):
        records = {}
        fake_module = types.ModuleType("engine.frame_generator")

        def fake_generate_frame(doc, params):
            records["params"] = dict(params)
            return {"grids": 6, "levels": 4, "columns": 18, "beams": 24, "floors": 9}

        def fake_format_stats(stats):
            return u"已生成框架：柱{}根, 梁{}根".format(stats["columns"], stats["beams"])

        fake_module.generate_frame = fake_generate_frame
        fake_module.format_stats = fake_format_stats
        monkeypatch.setitem(sys.modules, "engine.frame_generator", fake_module)

        client = _make_client(monkeypatch, self.MOCK_REPLY)
        reply = client.chat(u"生成一个2跨x1跨、3层的框架")
        command = parse_command(reply)
        result = dispatch_command(None, command)

        assert u"柱18根" in result
        assert records["params"]["num_floors"] == 3
        assert records["params"]["floor_height"] == 3600
        assert records["params"]["beam_section_x"] == "300x600"
        assert records["params"]["beam_section_y"] == "300x600"


# ---------------------------------------------------------------------------
# Scenario 3: Markdown-wrapped JSON should still parse
# ---------------------------------------------------------------------------

class TestMarkdownWrappedJson:
    """API returns JSON inside markdown code blocks; parser should strip them."""

    MOCK_REPLY_MD = (
        u"以下是你的建模指令：\n\n"
        u"```json\n"
        u'{"action":"create_beam","params":{"start_x":0,"start_y":0,"end_x":6000,"end_y":0,"floor":2,"section":"300x600"}}\n'
        u"```\n"
    )

    def test_parse_strips_markdown_and_extracts_command(self, monkeypatch):
        client = _make_client(monkeypatch, self.MOCK_REPLY_MD)
        reply = client.chat(u"在第二层创建一根梁")
        command = parse_command(reply)

        assert command["action"] == "create_beam"
        assert command["params"]["start_x"] == 0
        assert command["params"]["end_x"] == 6000
        assert command["params"]["floor"] == 2
        assert command["params"]["section"] == "300x600"

    def test_dispatch_after_parsing(self, monkeypatch):
        records = {}
        fake_module = types.ModuleType("engine.beam")

        def fake_create_beam(doc, start_x, start_y, end_x, end_y, level, section):
            records["start_x"] = start_x
            records["level"] = level.Name
            records["section"] = section

        fake_module.create_beam = fake_create_beam
        monkeypatch.setitem(sys.modules, "engine.beam", fake_module)

        client = _make_client(monkeypatch, self.MOCK_REPLY_MD)
        reply = client.chat(u"在第二层创建一根梁")
        command = parse_command(reply)

        levels = make_story_levels(3)
        result = dispatch_command(None, command, levels)

        assert u"梁" in result
        assert records["level"] == "F2"
        assert records["section"] == "300x600"


# ---------------------------------------------------------------------------
# Scenario 4: API returns an error payload
# ---------------------------------------------------------------------------

class TestApiErrorHandling:
    """When the API returns an error payload, client.chat should raise a user-friendly error."""

    def test_error_message_in_response(self, monkeypatch):
        client = DeepSeekClient(api_key="test-key")
        monkeypatch.setattr(
            client,
            "_http_post",
            lambda payload, timeout_ms=None: json.dumps({
                "error": {"message": "Insufficient balance"}
            }),
        )

        with pytest.raises(Exception, match="Insufficient balance"):
            client.chat(u"创建一根柱子")

        # Conversation should be rolled back to just the system prompt
        assert len(client.conversation) == 1
        assert client.conversation[0]["role"] == "system"

    def test_invalid_json_response(self, monkeypatch):
        client = DeepSeekClient(api_key="test-key")
        monkeypatch.setattr(
            client,
            "_http_post",
            lambda payload, timeout_ms=None: "<html>502 Bad Gateway</html>",
        )

        with pytest.raises(Exception, match=u"合法 JSON"):
            client.chat(u"创建一根柱子")

        assert len(client.conversation) == 1

    def test_http_exception_produces_api_error(self, monkeypatch):
        client = DeepSeekClient(api_key="test-key")

        def failing_http_post(payload, timeout_ms=None):
            raise OSError("connection refused")

        monkeypatch.setattr(client, "_http_post", failing_http_post)

        with pytest.raises(Exception, match=u"API 请求失败"):
            client.chat(u"统计柱子数量")

        assert len(client.conversation) == 1

    def test_unparseable_reply_raises_value_error(self):
        """When the LLM returns plain text that is not JSON, parse_command should raise."""
        with pytest.raises(ValueError, match=u"无法从回复中提取 JSON 指令"):
            parse_command(u"我不太理解你的意思，请换个说法。")


# ---------------------------------------------------------------------------
# Scenario 5: Batch command (API returns a JSON array)
# ---------------------------------------------------------------------------

class TestBatchCommandFlow:
    """API returns a JSON array of commands; they should be wrapped as a batch."""

    MOCK_REPLY_BATCH = json.dumps([
        {
            "action": "create_column",
            "params": {"x": 0, "y": 0, "base_floor": 1, "top_floor": 2, "section": "500x500"},
        },
        {
            "action": "create_column",
            "params": {"x": 6000, "y": 0, "base_floor": 1, "top_floor": 2, "section": "500x500"},
        },
    ])

    def test_parse_wraps_array_as_batch(self, monkeypatch):
        client = _make_client(monkeypatch, self.MOCK_REPLY_BATCH)
        reply = client.chat(u"在(0,0)和(6000,0)各创建一根柱子")
        command = parse_command(reply)

        assert command["action"] == "batch"
        assert len(command["params"]["commands"]) == 2
        assert command["params"]["commands"][0]["action"] == "create_column"
        assert command["params"]["commands"][1]["params"]["x"] == 6000

    def test_dispatch_batch_aggregates_results(self, monkeypatch):
        call_log = []
        fake_module = types.ModuleType("engine.column")

        def fake_create_column(doc, x, y, base_level, top_level, section):
            call_log.append(x)

        fake_module.create_column = fake_create_column
        monkeypatch.setitem(sys.modules, "engine.column", fake_module)

        client = _make_client(monkeypatch, self.MOCK_REPLY_BATCH)
        reply = client.chat(u"在(0,0)和(6000,0)各创建一根柱子")
        command = parse_command(reply)

        levels = make_story_levels(3)
        result = dispatch_command(None, command, levels)

        assert u"批量执行 2 条指令" in result
        assert call_log == [0, 6000]

    def test_single_item_array_unwrapped(self, monkeypatch):
        """A single-element array should be unwrapped, not treated as a batch."""
        single_array_reply = json.dumps([
            {"action": "query_count", "params": {"element_type": "column"}},
        ])

        client = _make_client(monkeypatch, single_array_reply)
        reply = client.chat(u"统计柱子数量")
        command = parse_command(reply)

        assert command["action"] == "query_count"
        assert "commands" not in command.get("params", {})


# ---------------------------------------------------------------------------
# Scenario 6: Full round-trip with alias normalization
# ---------------------------------------------------------------------------

class TestAliasNormalization:
    """Chinese action/param aliases should be normalized through the full chain."""

    MOCK_REPLY_CHINESE = json.dumps({
        u"action": u"创建梁",
        u"params": {
            u"start_x": 0,
            u"start_y": 0,
            u"end_x": 6000,
            u"end_y": 0,
            u"楼层": u"三层",
            u"截面": "500",
        },
    })

    def test_full_chain_normalizes_aliases(self, monkeypatch):
        client = _make_client(monkeypatch, self.MOCK_REPLY_CHINESE)
        reply = client.chat(u"在三层创建一根梁")
        command = parse_command(reply)

        assert command["action"] == "create_beam"
        assert command["params"]["floor"] == 3
        assert command["params"]["section"] == "500x500"
