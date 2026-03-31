# -*- coding: utf-8 -*-
"""RevitClaw pushbutton -- start/stop the remote control server."""

import sys
import types

from pyrevit import revit, DB, script

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from revitclaw.llm_client import RevitClawLLMClient
from revitclaw.handler import RevitClawHandler
from revitclaw.http_server import RevitClawServer

output = script.get_output()

REVITCLAW_PORT = 8080

# ── Persistent state (survives pyRevit re-execution) ──
_STATE_KEY = "__revitclaw_state__"
if _STATE_KEY not in sys.modules:
    _st = types.ModuleType(_STATE_KEY)
    _st.server = None
    _st.handler = None
    _st.idling_bound = False
    sys.modules[_STATE_KEY] = _st

_state = sys.modules[_STATE_KEY]

# Clean up residual from old DispatcherTimer version
if hasattr(_state, "timer"):
    try:
        _state.timer.Stop()
    except Exception:
        pass
    del _state.timer


WRITE_ACTIONS = frozenset([
    "create_column", "create_beam", "create_slab",
    "generate_frame", "delete_element", "modify_section", "batch",
])


def _on_idling(sender, args):
    """Revit Idling callback -- runs on main thread."""
    handler = _state.handler
    if not handler or not handler.has_pending():
        return
    try:
        doc = sender.ActiveUIDocument.Document

        # Peek at action to decide if we need a transaction
        action = ""
        with handler._lock:
            if handler._queue:
                action = handler._queue[0][0].get("action", "")

        if action in WRITE_ACTIONS:
            t = DB.Transaction(doc, u"AI智建：RevitClaw")
            t.Start()
            try:
                handler.process_next()
                t.Commit()
            except Exception:
                if t.HasStarted():
                    t.RollBack()
        else:
            handler.process_next()
    except Exception:
        # Dequeue and signal so nothing hangs
        try:
            with handler._lock:
                if handler._queue:
                    cmd, evt = handler._queue.pop(0)
                    handler._results.append({
                        "success": False,
                        "message": u"执行异常",
                        "action": cmd.get("action", ""),
                        "screenshot": "",
                    })
                    evt.set()
        except Exception:
            pass


def _start_server():
    doc = revit.doc
    if doc is None:
        output.print_md(u"**错误：** 请先打开一个 Revit 项目")
        return

    llm = RevitClawLLMClient(
        api_url=DEEPSEEK_API_URL,
        api_key=DEEPSEEK_API_KEY,
        model=DEEPSEEK_MODEL,
    )

    _state.handler = RevitClawHandler(doc=doc, DB=DB, screenshot_dir=None)

    _state.server = RevitClawServer(
        handler=_state.handler,
        llm=llm,
        port=REVITCLAW_PORT,
    )
    _state.server.start()

    # Register Idling event for command execution
    if not _state.idling_bound:
        __revit__.Idling += _on_idling
        _state.idling_bound = True

    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "127.0.0.1"

    output.print_md(u"## RevitClaw 已启动")
    output.print_md(u"- 本机: http://127.0.0.1:{}".format(REVITCLAW_PORT))
    output.print_md(u"- 局域网: http://{}:{}".format(local_ip, REVITCLAW_PORT))


def _stop_server():
    if _state.server:
        _state.server.stop()
        _state.server = None

    if _state.idling_bound:
        try:
            __revit__.Idling -= _on_idling
        except Exception:
            pass
        _state.idling_bound = False

    _state.handler = None
    output.print_md(u"## RevitClaw 已停止")


def main():
    if _state.server and _state.server.is_running():
        _stop_server()
    else:
        _start_server()


if __name__ == "__main__":
    main()
