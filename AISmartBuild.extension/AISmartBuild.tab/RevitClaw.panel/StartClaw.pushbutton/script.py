# -*- coding: utf-8 -*-
"""RevitClaw pushbutton -- start/stop the remote control server.

State is stored in sys.modules so it persists across pyRevit button clicks
(pyRevit re-executes the script each time, resetting module-level variables).
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
    _st.idling_subscribed = False
    _st.on_idling_func = None
    sys.modules[_STATE_KEY] = _st

_state = sys.modules[_STATE_KEY]


def _on_idling(sender, args):
    """Revit Idling event callback -- process queued commands."""
    handler = _state.handler
    if handler and handler.has_pending():
        try:
            with revit.Transaction(u"AI智建：RevitClaw 远程命令"):
                handler.process_next()
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

    # Subscribe to Idling event on UIApplication
    if not _state.idling_subscribed:
        _state.on_idling_func = _on_idling
        uiapp = __revit__
        uiapp.Idling += _state.on_idling_func
        _state.idling_subscribed = True

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

    if _state.idling_subscribed and _state.on_idling_func:
        try:
            uiapp = __revit__
            uiapp.Idling -= _state.on_idling_func
        except Exception:
            pass
        _state.idling_subscribed = False
        _state.on_idling_func = None

    _state.handler = None
    output.print_md(u"## RevitClaw 已停止")


def main():
    if _state.server and _state.server.is_running():
        _stop_server()
    else:
        _start_server()


if __name__ == "__main__":
    main()
