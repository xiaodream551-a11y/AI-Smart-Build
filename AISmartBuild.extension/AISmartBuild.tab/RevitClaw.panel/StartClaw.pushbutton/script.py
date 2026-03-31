# -*- coding: utf-8 -*-
"""RevitClaw pushbutton -- start/stop the remote control server.

Uses WPF DispatcherTimer to poll command queue on the Revit main thread.
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
    _st.timer = None
    _st.uiapp = None
    sys.modules[_STATE_KEY] = _st

_state = sys.modules[_STATE_KEY]


# ── Timer callback (runs on Revit main thread) ──

def _on_timer_tick(sender, args):
    """Process pending commands from the queue."""
    handler = _state.handler
    if not handler or not handler.has_pending():
        return

    try:
        uiapp = _state.uiapp
        doc = uiapp.ActiveUIDocument.Document

        # Peek at action to decide if transaction is needed
        action = ""
        with handler._lock:
            if handler._queue:
                action = handler._queue[0][0].get("action", "")

        needs_transaction = action in (
            "create_column", "create_beam", "create_slab",
            "generate_frame", "delete_element", "modify_section", "batch",
        )

        if needs_transaction:
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
        # On failure, dequeue and signal error so HTTP thread doesn't hang
        try:
            import threading
            with handler._lock:
                if handler._queue:
                    cmd, evt = handler._queue.pop(0)
                    handler._results.append({
                        "success": False,
                        "message": u"Revit 执行异常",
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

    # Store UIApplication reference for timer callback
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

    # Start DispatcherTimer to poll command queue on main thread
    if _state.timer is None:
        try:
            from System.Windows.Threading import DispatcherTimer
            from System import TimeSpan, EventHandler

            _state.timer = DispatcherTimer()
            _state.timer.Interval = TimeSpan.FromMilliseconds(500)
            _state.timer.Tick += EventHandler(_on_timer_tick)
            _state.timer.Start()
        except Exception:
            pass

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


def _stop_server():
    if _state.timer:
        try:
            _state.timer.Stop()
        except Exception:
            pass
        _state.timer = None

    if _state.server:
        _state.server.stop()
        _state.server = None

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
