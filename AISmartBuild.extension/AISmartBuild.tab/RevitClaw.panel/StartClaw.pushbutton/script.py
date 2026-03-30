# -*- coding: utf-8 -*-
"""RevitClaw pushbutton -- start/stop the remote control server."""

from pyrevit import revit, DB, script

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from revitclaw.llm_client import RevitClawLLMClient
from revitclaw.handler import RevitClawHandler
from revitclaw.http_server import RevitClawServer

output = script.get_output()

_server = None
_handler = None
_idling_subscribed = False

REVITCLAW_PORT = 8080


def _start_server():
    global _server, _handler, _idling_subscribed

    doc = revit.doc
    if doc is None:
        output.print_md(u"**错误：** 请先打开一个 Revit 项目")
        return

    llm = RevitClawLLMClient(
        api_url=DEEPSEEK_API_URL,
        api_key=DEEPSEEK_API_KEY,
        model=DEEPSEEK_MODEL,
    )

    _handler = RevitClawHandler(doc=doc, DB=DB, screenshot_dir=None)

    _server = RevitClawServer(
        handler=_handler,
        llm=llm,
        port=REVITCLAW_PORT,
    )
    _server.start()

    # Subscribe to Idling event
    if not _idling_subscribed:
        revit.doc.Application.Idling += _on_idling
        _idling_subscribed = True

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
    global _server, _handler, _idling_subscribed

    if _server:
        _server.stop()
        _server = None

    if _idling_subscribed:
        try:
            revit.doc.Application.Idling -= _on_idling
        except Exception:
            pass
        _idling_subscribed = False

    _handler = None
    output.print_md(u"## RevitClaw 已停止")


def _on_idling(sender, args):
    """Revit Idling event callback -- process queued commands."""
    if _handler and _handler.has_pending():
        try:
            with revit.Transaction(u"AI智建：RevitClaw 远程命令"):
                _handler.process_next()
        except Exception:
            pass


def main():
    if _server and _server.is_running():
        _stop_server()
    else:
        _start_server()


if __name__ == "__main__":
    main()
