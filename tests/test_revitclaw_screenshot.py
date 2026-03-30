# -*- coding: utf-8 -*-
"""Tests for RevitClaw screenshot module."""

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import offline_runtime
offline_runtime.bootstrap()

from revitclaw.screenshot import capture_screenshot, get_screenshot_dir


class TestGetScreenshotDir:
    def test_returns_path(self, tmp_path):
        result = get_screenshot_dir(str(tmp_path))
        assert Path(result).is_dir()

    def test_creates_dir_if_missing(self, tmp_path):
        target = tmp_path / "screenshots"
        result = get_screenshot_dir(str(target))
        assert Path(result).is_dir()


class TestCaptureScreenshot:
    def test_calls_export_image(self, tmp_path):
        mock_doc = MagicMock()
        mock_doc.ActiveView = MagicMock()
        mock_doc.ActiveView.Id = MagicMock()
        mock_doc.ActiveView.Id.IntegerValue = 42

        mock_options = MagicMock()
        mock_db = MagicMock()
        mock_db.ImageExportOptions = MagicMock(return_value=mock_options)
        mock_db.ImageFileType = MagicMock()
        mock_db.ImageFileType.PNG = "PNG"
        mock_db.ImageResolution = MagicMock()
        mock_db.ImageResolution.DPI_150 = 150

        filepath = capture_screenshot(mock_doc, mock_db, str(tmp_path))

        assert filepath is not None
        mock_doc.ExportImage.assert_called_once()

    def test_returns_none_on_error(self, tmp_path):
        mock_doc = MagicMock()
        mock_doc.ActiveView = None
        mock_db = MagicMock()

        filepath = capture_screenshot(mock_doc, mock_db, str(tmp_path))
        assert filepath is None
