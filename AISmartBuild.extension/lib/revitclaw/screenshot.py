# -*- coding: utf-8 -*-
"""Revit screenshot capture for RevitClaw.

DB is passed in as parameter -- never imported directly.
"""

import os
import time


def get_screenshot_dir(base_dir=None):
    """Ensure screenshot directory exists and return its path."""
    if base_dir is None:
        base_dir = os.path.join(os.environ.get("TEMP", "/tmp"), "revitclaw_screenshots")
    if not os.path.isdir(base_dir):
        os.makedirs(base_dir)
    return base_dir


def capture_screenshot(doc, DB, output_dir):
    """Capture current Revit active view as a PNG.

    Args:
        doc: Revit Document
        DB: Revit DB namespace (passed in, not imported)
        output_dir: Directory to save the screenshot

    Returns:
        str: File path of the saved screenshot, or None on failure.
    """
    try:
        view = doc.ActiveView
        if view is None:
            return None

        output_dir = get_screenshot_dir(output_dir)
        filename = "revitclaw_{}".format(int(time.time() * 1000))

        options = DB.ImageExportOptions()
        options.FilePath = os.path.join(output_dir, filename)
        options.ExportRange = DB.ExportRange.CurrentView
        options.HLRandWFViewsFileType = DB.ImageFileType.PNG
        options.ShadowViewsFileType = DB.ImageFileType.PNG
        options.ImageResolution = DB.ImageResolution.DPI_150
        options.ZoomType = DB.ZoomFitType.FitToPage
        options.PixelSize = 1920

        doc.ExportImage(options)

        # Revit appends the file extension; check for .png
        result_path = options.FilePath + ".png"
        if os.path.isfile(result_path):
            return result_path

        # In some Revit versions, the path is used as-is
        return options.FilePath
    except Exception:
        return None
