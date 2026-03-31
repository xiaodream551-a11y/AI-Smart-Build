# -*- coding: utf-8 -*-
"""RevitClaw pushbutton -- start/stop the remote control server.

Uses Revit Idling event to poll command queue on the main thread.
State is stored in sys.modules to persist across pyRevit button clicks.
"""

import sys
import types

from pyrevit import revit, DB, script

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from revitclaw.llm_client import RevitClawLLMClient
from revitclaw.handler import RevitClawHandler
from revitclaw.http_server import RevitClawServer

output = script.get_output()

REVITCLAW_PORT = 8080

# ── Persistent state across button clicks ──
_STATE_KEY = "__revitclaw_state__"
if _STATE_KEY not in sys.modules:
    _st = types.ModuleType(_STATE_KEY)
    _st.server = None
    _st.handler = None
    _st.uiapp = None
    _st.idling_bound = False
    sys.modules[_STATE_KEY] = _st

_state = sys.modules[_STATE_KEY]


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

        # Peek at action
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

    except Exception as err:
        # Dequeue and signal error
        try:
            with handler._lock:
                if handler._queue:
                    cmd, evt = handler._queue.pop(0)
                    handler._results.append({
                        "success": False,
                        "message": str(err),
                        "action": cmd.get("action", "unknown"),
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

    _state.uiapp = __revit__

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

    # Subscribe Idling event (only once)
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
    output.print_md(u"\n用手机浏览器打开上面的地址即可远程控制")
    output.print_md(u"\n**提示：** 关闭此窗口后，Revit 才会开始处理远程命令")


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
    _state.uiapp = None
    output.print_md(u"## RevitClaw 已停止")


def main():
    if _state.server and _state.server.is_running():
        _stop_server()
    else:
        _start_server()


if __name__ == "__main__":
    main()
