# -*- coding: utf-8 -*-
"""Shared execution and output helpers for the AI chat workflow."""

import json

from pyrevit import revit

from ai.parser import dispatch_command
from utils import get_sorted_levels


TRANSACTIONAL_ACTIONS = set([
    "batch",
    "create_column",
    "create_beam",
    "create_slab",
    "generate_frame",
    "modify_section",
    "delete_element",
])


def get_all_levels(doc):
    """Retrieve all levels in the current document, sorted by elevation."""
    return get_sorted_levels(doc)


def shorten_text(text, limit=200):
    content = text or ""
    if len(content) <= limit:
        return content
    return content[:limit] + "..."


def format_command_text(command):
    return json.dumps(command, ensure_ascii=False, indent=2)


def _should_use_transaction(action):
    return action in TRANSACTIONAL_ACTIONS


def execute_command(doc, command, levels):
    action = command.get("action", "unknown")

    if _should_use_transaction(action):
        with revit.Transaction("AI智建：" + action):
            result = dispatch_command(doc, command, levels)
        return result, get_all_levels(doc)

    result = dispatch_command(doc, command, levels)
    return result, levels


def print_system_message(output, message):
    if output is None:
        return
    output.print_md("**系统：** " + message)
    output.print_md("---")
