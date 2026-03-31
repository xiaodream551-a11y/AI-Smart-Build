# -*- coding: utf-8 -*-
"""RevitClaw pushbutton -- watch pending.json and auto-execute commands.

Flow:
1. User runs Flask server separately (PowerShell)
2. Click this button to start/stop file watching
3. Idling event checks pending.json every tick
4. Commands are executed automatically on the Revit main thread
"""

import io
import json
import os
import sys
import types

from pyrevit import revit, DB, script

from ai.parser import dispatch_command
from utils import get_sorted_levels

output = script.get_output()

# pending.json path (project_root/revitclaw/pending.json)
# __file__ is at project_root/AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/script.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)))
_PENDING_FILE = os.path.join(_PROJECT_ROOT, "revitclaw", "pending.json")

WRITE_ACTIONS = frozenset([
    "create_column", "create_beam", "create_slab",
    "generate_frame", "delete_element", "modify_section", "batch",
])

# ── Persistent state ──
_STATE_KEY = "__revitclaw_watcher__"
if _STATE_KEY not in sys.modules:
    _st = types.ModuleType(_STATE_KEY)
    _st.active = False
    _st.levels = None
    sys.modules[_STATE_KEY] = _st

_state = sys.modules[_STATE_KEY]


def _read_and_clear_pending():
    """Read pending commands and clear the file. Returns list or empty."""
    if not os.path.isfile(_PENDING_FILE):
        return []
    try:
        with io.open(_PENDING_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content or content == "[]":
            return []
        commands = json.loads(content)
        # Clear immediately
        with io.open(_PENDING_FILE, "w", encoding="utf-8") as f:
            f.write(u"[]")
        return commands if isinstance(commands, list) else []
    except Exception:
        return []


def _on_idling(sender, args):
    """Check pending.json and execute commands."""
    if not _state.active:
        return

    commands = _read_and_clear_pending()
    if not commands:
        return

    try:
        doc = sender.ActiveUIDocument.Document

        if _state.levels is None:
            _state.levels = get_sorted_levels(doc)

        for command in commands:
            action = command.get("action", "")
            needs_tx = action in WRITE_ACTIONS

            if needs_tx:
                t = DB.Transaction(doc, u"AI智建：远程-" + action)
                t.Start()
                try:
                    dispatch_command(doc, command, _state.levels)
                    t.Commit()
                    _state.levels = get_sorted_levels(doc)
                except Exception:
                    if t.HasStarted():
                        t.RollBack()
            else:
                dispatch_command(doc, command, _state.levels)
    except Exception:
        pass


def main():
    if _state.active:
        # Stop watching
        _state.active = False
        try:
            __revit__.Idling -= _on_idling
        except Exception:
            pass
        output.print_md(u"## RevitClaw 文件监听已停止")
    else:
        # Start watching
        _state.active = True
        _state.levels = None
        __revit__.Idling += _on_idling
        output.print_md(u"## RevitClaw 文件监听已启动")
        output.print_md(u"Revit 将自动执行远程命令")
        output.print_md(u"\n**使用方法：**")
        output.print_md(u"1. PowerShell 运行: `python revitclaw/server.py --port 8080 --revit`")
        output.print_md(u"2. 浏览器打开 http://127.0.0.1:8080")
        output.print_md(u"3. 发送命令，Revit 自动执行")
        output.print_md(u"\n监听文件: {}".format(_PENDING_FILE))


if __name__ == "__main__":
    main()
