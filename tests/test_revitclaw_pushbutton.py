# -*- coding: utf-8 -*-
"""Tests for RevitClaw pushbutton script."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_toggle_start(self):
        """main() should start the server when not running."""
        pushbutton_script._state.server = None
        with patch.object(pushbutton_script, "_start_server") as mock_start:
            pushbutton_script.main()
            mock_start.assert_called_once()

    def test_toggle_stop(self):
        """main() should stop the server when already running."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        pushbutton_script._state.server = mock_server
        try:
            with patch.object(pushbutton_script, "_stop_server") as mock_stop:
                pushbutton_script.main()
                mock_stop.assert_called_once()
        finally:
            pushbutton_script._state.server = None
