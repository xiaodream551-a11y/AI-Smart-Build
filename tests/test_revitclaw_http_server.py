# -*- coding: utf-8 -*-
"""Tests for RevitClaw HTTP server (portable layer, no .NET dependency)."""

import json
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import offline_runtime
offline_runtime.bootstrap()

from revitclaw.http_server import RevitClawServer, _route_request


class TestRouteRequest:
    def _make_deps(self):
        handler = MagicMock()
        handler.has_pending.return_value = False
        llm = MagicMock()
        return handler, llm

    def test_health(self):
        handler, llm = self._make_deps()
        status, body = _route_request("GET", "/api/health", None, handler, llm, "/tmp")
        assert status == 200
        data = json.loads(body)
        assert data["status"] == "ok"
        assert data["revit"] is True

    def test_chat_empty_message(self):
        handler, llm = self._make_deps()
        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": ""}),
            handler, llm, "/tmp",
        )
        assert status == 400

    def test_chat_reset(self):
        handler, llm = self._make_deps()
        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": "/reset"}),
            handler, llm, "/tmp",
        )
        data = json.loads(body)
        assert data["action"] == "reset"
        llm.reset.assert_called_once()

    def test_chat_calls_llm_and_queues(self):
        handler, llm = self._make_deps()
        llm.chat.return_value = (u"已创建柱子", {"action": "create_column", "params": {}})

        mock_event = MagicMock()
        mock_event.wait.return_value = True
        handler.enqueue_command.return_value = mock_event
        handler.get_result.return_value = {
            "success": True,
            "message": u"已创建柱子",
            "action": "create_column",
            "screenshot": "shot.png",
        }

        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": u"创建柱子"}),
            handler, llm, "/tmp",
        )
        data = json.loads(body)
        assert data["success"] is True
        assert data["screenshot_url"] == "/api/screenshot/shot.png"

    def test_chat_llm_error(self):
        handler, llm = self._make_deps()
        llm.chat.side_effect = Exception("API failed")

        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": "test"}),
            handler, llm, "/tmp",
        )
        assert status == 500

    def test_chat_query_action_no_queue(self):
        """Query actions should still be queued to Revit handler (they need doc access)."""
        handler, llm = self._make_deps()
        llm.chat.return_value = (u"共有10根柱", {"action": "query_count", "params": {}})

        mock_event = MagicMock()
        mock_event.wait.return_value = True
        handler.enqueue_command.return_value = mock_event
        handler.get_result.return_value = {
            "success": True, "message": u"共有10根柱",
            "action": "query_count", "screenshot": "",
        }

        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": u"查询柱数"}),
            handler, llm, "/tmp",
        )
        data = json.loads(body)
        assert data["success"] is True


class TestRevitClawServer:
    def test_init(self):
        handler = MagicMock()
        llm = MagicMock()
        server = RevitClawServer(handler, llm, port=8888, screenshot_dir="/tmp")
        assert server.port == 8888
        assert not server.is_running()
