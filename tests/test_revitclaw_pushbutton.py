# -*- coding: utf-8 -*-
"""Tests for RevitClaw pushbutton script."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import offline_runtime
offline_runtime.bootstrap()

# Load the pushbutton script as a module
pushbutton_script = offline_runtime.load_module_from_path(
    "revitclaw_pushbutton",
    "AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/script.py",
)


class TestRevitClawPushbutton:
    def test_module_loads(self):
        assert hasattr(pushbutton_script, "main")
        assert hasattr(pushbutton_script, "_on_idling")
        assert hasattr(pushbutton_script, "_read_and_clear_pending")

    def test_pending_file_path(self):
        assert pushbutton_script._PENDING_FILE.endswith("pending.json")
        assert "revitclaw" in pushbutton_script._PENDING_FILE

    def test_read_empty_pending(self, tmp_path):
        """Returns empty list when file doesn't exist."""
        mod = pushbutton_script
        original = mod._PENDING_FILE
        mod._PENDING_FILE = str(tmp_path / "nope.json")
        try:
            assert mod._read_and_clear_pending() == []
        finally:
            mod._PENDING_FILE = original

    def test_read_and_clear(self, tmp_path):
        """Reads commands and clears the file."""
        import json
        pending = tmp_path / "pending.json"
        pending.write_text(json.dumps([{"action": "create_column", "params": {}}]))

        mod = pushbutton_script
        original = mod._PENDING_FILE
        mod._PENDING_FILE = str(pending)
        try:
            cmds = mod._read_and_clear_pending()
            assert len(cmds) == 1
            assert cmds[0]["action"] == "create_column"
            # File should be cleared
            assert json.loads(pending.read_text()) == []
        finally:
            mod._PENDING_FILE = original
