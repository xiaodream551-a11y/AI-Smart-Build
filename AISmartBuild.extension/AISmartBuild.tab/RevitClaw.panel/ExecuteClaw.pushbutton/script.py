# -*- coding: utf-8 -*-
"""Execute pending RevitClaw commands from the queue file."""

import io
import json
import os

from pyrevit import revit, DB, script, forms

from ai.parser import dispatch_command
from utils import get_sorted_levels

output = script.get_output()

# pending.json sits next to server.py in revitclaw/
_PENDING_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))),
    "revitclaw", "pending.json",
)

WRITE_ACTIONS = frozenset([
    "create_column", "create_beam", "create_slab",
    "generate_frame", "delete_element", "modify_section", "batch",
])


def _read_pending():
    """Read and clear the pending commands file."""
    if not os.path.isfile(_PENDING_FILE):
        return []
    try:
        with io.open(_PENDING_FILE, "r", encoding="utf-8") as f:
            commands = json.load(f)
        # Clear the file
        with io.open(_PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return commands if isinstance(commands, list) else []
    except Exception:
        return []


def main():
    doc = revit.doc
    if doc is None:
        output.print_md(u"**错误：** 请先打开一个 Revit 项目")
        return

    commands = _read_pending()
    if not commands:
        output.print_md(u"**没有待执行的远程命令**")
        return

    output.print_md(u"## 执行 {} 条远程命令".format(len(commands)))

    levels = get_sorted_levels(doc)
    success_count = 0
    fail_count = 0

    for i, command in enumerate(commands):
        action = command.get("action", "unknown")
        needs_tx = action in WRITE_ACTIONS

        try:
            if needs_tx:
                with revit.Transaction(u"AI智建：远程-{}".format(action)):
                    result = dispatch_command(doc, command, levels)
            else:
                result = dispatch_command(doc, command, levels)

            # Refresh levels after write commands
            if needs_tx:
                levels = get_sorted_levels(doc)

            output.print_md(u"**{}. {} →** {}".format(i + 1, action, result))
            success_count += 1
        except Exception as err:
            output.print_md(u"**{}. {} →** 失败: {}".format(i + 1, action, str(err)))
            fail_count += 1

    output.print_md(u"\n---")
    output.print_md(u"**完成：** {} 成功，{} 失败".format(success_count, fail_count))


if __name__ == "__main__":
    main()
