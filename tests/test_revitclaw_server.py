# -*- coding: utf-8 -*-
"""Tests for RevitClaw relay server."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add revitclaw to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "revitclaw"))

from server import app, _state, _try_parse_command, _lock


@pytest.fixture
def client():
    """Flask test client with fresh state."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        # Reset state before each test
        with _lock:
            _state["revit_mode"] = False
            _state["command_queue"] = []
            _state["result_queue"] = []
            _state["conversation"] = [
                {"role": "system", "content": "test prompt"},
            ]
        yield c


# ──────────────────────────────────────────────
# Route tests
# ──────────────────────────────────────────────

class TestHealthEndpoint:
    def test_returns_ok(self, client):
        resp = client.get("/api/health")
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["revit"] is False

    def test_shows_revit_mode(self, client):
        with _lock:
            _state["revit_mode"] = True
        resp = client.get("/api/health")
        assert resp.get_json()["revit"] is True


class TestChatEndpoint:
    def test_empty_message_rejected(self, client):
        resp = client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 400

    def test_reset_command(self, client):
        resp = client.post("/api/chat", json={"message": "/reset"})
        data = resp.get_json()
        assert data["success"] is True
        assert data["action"] == "reset"
        assert len(_state["conversation"]) == 1

    def test_help_command(self, client):
        resp = client.post("/api/chat", json={"message": "/help"})
        data = resp.get_json()
        assert data["success"] is True
        assert "RevitClaw" in data["reply"]

    def test_status_command(self, client):
        resp = client.post("/api/chat", json={"message": "/status"})
        data = resp.get_json()
        assert data["success"] is True
        assert "离线" in data["reply"]

    def test_queue_empty(self, client):
        resp = client.post("/api/chat", json={"message": "/queue"})
        data = resp.get_json()
        assert "空" in data["reply"]

    def test_queue_with_items(self, client):
        with _lock:
            _state["command_queue"] = [
                {"action": "create_column", "params": {}},
                {"action": "create_beam", "params": {}},
            ]
        resp = client.post("/api/chat", json={"message": "/queue"})
        data = resp.get_json()
        assert "2 条" in data["reply"]

    @patch("server._call_llm")
    def test_chat_returns_reply(self, mock_llm, client):
        mock_llm.return_value = ("已创建柱子", {"action": "create_column", "params": {}})
        resp = client.post("/api/chat", json={"message": "创建一根柱子"})
        data = resp.get_json()
        assert data["success"] is True
        assert data["reply"] == "已创建柱子"

    @patch("server._call_llm")
    def test_chat_offline_mode_no_queue(self, mock_llm, client):
        mock_llm.return_value = ("ok", {"action": "create_column", "params": {}})
        client.post("/api/chat", json={"message": "test"})
        assert len(_state["command_queue"]) == 0

    @patch("server._call_llm")
    def test_chat_revit_mode_queues_command(self, mock_llm, client):
        with _lock:
            _state["revit_mode"] = True
        mock_llm.return_value = ("ok", {"action": "create_column", "params": {}})
        client.post("/api/chat", json={"message": "test"})
        assert len(_state["command_queue"]) == 1
        assert _state["command_queue"][0]["action"] == "create_column"

    @patch("server._call_llm")
    def test_chat_llm_error(self, mock_llm, client):
        mock_llm.side_effect = Exception("API error")
        resp = client.post("/api/chat", json={"message": "test"})
        assert resp.status_code == 500


class TestPollEndpoint:
    def test_poll_empty_queue(self, client):
        resp = client.get("/api/poll")
        data = resp.get_json()
        assert data["has_command"] is False

    def test_poll_returns_command(self, client):
        with _lock:
            _state["command_queue"] = [
                {"action": "create_column", "params": {"x": 0, "y": 0}},
            ]
        resp = client.get("/api/poll")
        data = resp.get_json()
        assert data["has_command"] is True
        assert data["command"]["action"] == "create_column"
        assert len(_state["command_queue"]) == 0

    def test_poll_fifo_order(self, client):
        with _lock:
            _state["command_queue"] = [
                {"action": "first", "params": {}},
                {"action": "second", "params": {}},
            ]
        r1 = client.get("/api/poll").get_json()
        r2 = client.get("/api/poll").get_json()
        assert r1["command"]["action"] == "first"
        assert r2["command"]["action"] == "second"


class TestResultEndpoint:
    def test_post_result(self, client):
        resp = client.post("/api/result", json={
            "action": "create_column", "success": True, "message": "ok",
        })
        assert resp.get_json()["status"] == "ok"
        assert len(_state["result_queue"]) == 1


# ──────────────────────────────────────────────
# Command parsing tests
# ──────────────────────────────────────────────

class TestTryParseCommand:
    def test_valid_json(self):
        text = '{"action": "create_column", "params": {"x": 0}}'
        cmd = _try_parse_command(text)
        assert cmd["action"] == "create_column"

    def test_markdown_fenced(self):
        text = '```json\n{"action": "create_beam", "params": {}}\n```'
        cmd = _try_parse_command(text)
        assert cmd["action"] == "create_beam"

    def test_json_array_becomes_batch(self):
        text = '[{"action": "create_column"}, {"action": "create_beam"}]'
        cmd = _try_parse_command(text)
        assert cmd["action"] == "batch"

    def test_mixed_text_with_json(self):
        text = '好的，我来创建柱子。\n{"action": "create_column", "params": {"x": 0}}'
        cmd = _try_parse_command(text)
        assert cmd is not None
        assert cmd["action"] == "create_column"

    def test_plain_text_returns_none(self):
        cmd = _try_parse_command("这是一段普通文字，没有JSON")
        assert cmd is None

    def test_empty_returns_none(self):
        assert _try_parse_command("") is None


# ──────────────────────────────────────────────
# Screenshot endpoint tests
# ──────────────────────────────────────────────

class TestScreenshotEndpoint:
    def test_screenshot_not_found(self, client):
        resp = client.get("/api/screenshot/nonexistent.png")
        assert resp.status_code == 404

    def test_screenshot_serves_file(self, client, tmp_path):
        # Create a temp screenshot
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG fake image data")
        with _lock:
            _state["screenshot_dir"] = str(tmp_path)
        resp = client.get("/api/screenshot/test.png")
        assert resp.status_code == 200
        assert b"PNG" in resp.data

    def test_screenshot_blocks_path_traversal(self, client, tmp_path):
        with _lock:
            _state["screenshot_dir"] = str(tmp_path)
        resp = client.get("/api/screenshot/../../../etc/passwd")
        assert resp.status_code == 404
