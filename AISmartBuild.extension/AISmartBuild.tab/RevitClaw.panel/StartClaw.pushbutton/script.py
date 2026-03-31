# -*- coding: utf-8 -*-
"""RevitClaw pushbutton -- start/stop the remote control server.

Uses ExternalEvent (not Idling) to execute commands on the Revit main thread.
State is stored in sys.modules to persist across pyRevit button clicks.
"""

import sys
import types

from pyrevit import revit, DB, script

try:
    import clr
    clr.AddReference("RevitAPIUI")
    from Autodesk.Revit.UI import ExternalEvent, IExternalEventHandler
    _HAS_REVIT_UI = True
except (ImportError, Exception):
    _HAS_REVIT_UI = False
    ExternalEvent = None
    IExternalEventHandler = object  # fallback base class for offline

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
    _st.ext_event = None
    _st.event_handler = None
    sys.modules[_STATE_KEY] = _st

_state = sys.modules[_STATE_KEY]


# ── ExternalEvent handler (runs on Revit main thread) ──

class ClawEventHandler(IExternalEventHandler):
    """Processes queued RevitClaw commands on the Revit main thread."""

    def Execute(self, uiapp):
        handler = _state.handler
        if not handler or not handler.has_pending():
            return
        try:
            doc = uiapp.ActiveUIDocument.Document
            action = ""
            # Peek at the action to decide if we need a transaction
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
                    raise
            else:
                handler.process_next()
        except Exception as err:
            # Ensure the event is signaled even on failure
            import threading
            if handler._queue:
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

    def GetName(self):
        return "RevitClaw Event Handler"


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

    # Create ExternalEvent for main-thread execution
    if _HAS_REVIT_UI:
        _state.event_handler = ClawEventHandler()
        _state.ext_event = ExternalEvent.Create(_state.event_handler)
        _state.handler.set_notify(lambda: _state.ext_event.Raise())

    _state.server = RevitClawServer(
        handler=_state.handler,
        llm=llm,
        port=REVITCLAW_PORT,
    )
    _state.server.start()

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
    if _state.server:
        _state.server.stop()
        _state.server = None

    if _state.ext_event:
        try:
            _state.ext_event.Dispose()
        except Exception:
            pass
        _state.ext_event = None
        _state.event_handler = None

    _state.handler = None
    output.print_md(u"## RevitClaw 已停止")


def main():
    if _state.server and _state.server.is_running():
        _stop_server()
    else:
        _start_server()


if __name__ == "__main__":
    main()
