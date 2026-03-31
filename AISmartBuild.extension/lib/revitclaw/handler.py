# -*- coding: utf-8 -*-
"""RevitClaw command handler.

Manages a command queue consumed by Revit's Idling event.
DB is passed in -- never imported directly.
"""

import os
import threading

from ai.parser import dispatch_command
from revitclaw.screenshot import capture_screenshot
from utils import get_sorted_levels


class RevitClawHandler(object):
    """Processes commands from the HTTP server on the Revit main thread."""

    def __init__(self, doc, DB, screenshot_dir):
        self.doc = doc
        self.DB = DB
        self.screenshot_dir = screenshot_dir
        self._levels = None
        self._queue = []       # list of (command_dict, threading.Event)
        self._results = []     # list of result dicts
        self._lock = threading.Lock()
        self._notify_func = None  # called after enqueue to trigger main thread

    def set_notify(self, func):
        """Set a callback invoked after a command is enqueued.

        Used to call ExternalEvent.Raise() from the pushbutton script.
        """
        self._notify_func = func

    def enqueue_command(self, command):
        """Add a command to the queue. Returns a threading.Event that signals completion."""
        event = threading.Event()
        with self._lock:
            self._queue.append((command, event))
        if self._notify_func:
            try:
                self._notify_func()
            except Exception:
                pass
        return event

    def has_pending(self):
        with self._lock:
            return len(self._queue) > 0

    def get_result(self):
        """Pop the oldest result."""
        with self._lock:
            if self._results:
                return self._results.pop(0)
        return None

    def process_next(self):
        """Process the next queued command. Call this from Revit Idling event."""
        with self._lock:
            if not self._queue:
                return
            command, event = self._queue.pop(0)

        try:
            if self._levels is None:
                self._levels = get_sorted_levels(self.doc)

            result_text = dispatch_command(self.doc, command, self._levels)

            # Refresh levels after modifying commands
            action = command.get("action", "")
            if action in ("create_column", "create_beam", "create_slab",
                          "generate_frame", "delete_element", "batch"):
                self._levels = get_sorted_levels(self.doc)

            # Capture screenshot
            screenshot_path = capture_screenshot(
                self.doc, self.DB, self.screenshot_dir
            )
            screenshot_name = ""
            if screenshot_path:
                screenshot_name = os.path.basename(screenshot_path)

            result = {
                "success": True,
                "message": result_text,
                "action": action,
                "screenshot": screenshot_name,
            }
        except Exception as err:
            result = {
                "success": False,
                "message": str(err),
                "action": command.get("action", "unknown"),
                "screenshot": "",
            }

        with self._lock:
            self._results.append(result)
        event.set()
