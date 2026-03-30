# -*- coding: utf-8 -*-
"""Tests for RevitClaw command handler."""

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Bootstrap offline runtime
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import offline_runtime
offline_runtime.bootstrap()

from revitclaw.handler import RevitClawHandler


class TestRevitClawHandler:
    def _make_handler(self, tmp_path):
        mock_doc = MagicMock()
        mock_db = MagicMock()
        return RevitClawHandler(
            doc=mock_doc,
            DB=mock_db,
            screenshot_dir=str(tmp_path),
        )

    def test_enqueue_and_dequeue(self, tmp_path):
        handler = self._make_handler(tmp_path)
        cmd = {"action": "create_column", "params": {"x": 0, "y": 0}}
        event = handler.enqueue_command(cmd)
        assert not event.is_set()
        assert handler.has_pending()

    def test_process_command_calls_dispatch(self, tmp_path):
        handler = self._make_handler(tmp_path)
        cmd = {"action": "query_summary", "params": {}}
        event = handler.enqueue_command(cmd)

        with patch("revitclaw.handler.dispatch_command", return_value=u"模型概况") as mock_dispatch:
            with patch("revitclaw.handler.capture_screenshot", return_value=None):
                handler.process_next()

        assert event.is_set()
        result = handler.get_result()
        assert result["success"] is True
        assert result["message"] == u"模型概况"

    def test_process_command_with_screenshot(self, tmp_path):
        handler = self._make_handler(tmp_path)
        cmd = {"action": "create_column", "params": {"x": 0}}
        handler.enqueue_command(cmd)

        fake_path = str(tmp_path / "shot.png")
        with patch("revitclaw.handler.dispatch_command", return_value=u"已创建"):
            with patch("revitclaw.handler.capture_screenshot", return_value=fake_path):
                with patch("revitclaw.handler.get_sorted_levels", return_value=[]):
                    handler.process_next()

        result = handler.get_result()
        assert result["screenshot"] == "shot.png"

    def test_process_command_handles_exception(self, tmp_path):
        handler = self._make_handler(tmp_path)
        cmd = {"action": "create_column", "params": {}}
        handler.enqueue_command(cmd)

        with patch("revitclaw.handler.dispatch_command", side_effect=Exception("boom")):
            with patch("revitclaw.handler.get_sorted_levels", return_value=[]):
                handler.process_next()

        result = handler.get_result()
        assert result["success"] is False
        assert "boom" in result["message"]

    def test_no_pending_does_nothing(self, tmp_path):
        handler = self._make_handler(tmp_path)
        assert not handler.has_pending()
        handler.process_next()  # should not raise
