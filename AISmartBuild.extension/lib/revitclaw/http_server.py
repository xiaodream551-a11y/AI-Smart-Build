# -*- coding: utf-8 -*-
"""RevitClaw HTTP server with routing and HttpListener backend.

The routing logic (_route_request) is pure Python and testable offline.
The HttpListener backend (_run_listener) requires IronPython/.NET and
only runs inside Revit.
"""

import json
import os
import threading


# ---------------------------------------------------------------------------
# Routing (pure Python, fully testable)
# ---------------------------------------------------------------------------

_HELP_TEXT = (
    u"RevitClaw 指令帮助:\n"
    u"/reset - 清空对话历史\n"
    u"/help  - 显示此帮助\n"
    u"/status - 查看服务器状态"
)


def _json_response(status, obj):
    """Return (status_code, json_string) tuple."""
    return status, json.dumps(obj, ensure_ascii=False)


def _handle_chat(body, handler, llm, screenshot_dir):
    """Process a chat request. Returns (status_code, response_json)."""
    try:
        payload = json.loads(body) if body else {}
    except (ValueError, TypeError):
        return _json_response(400, {"success": False, "error": u"无效的JSON"})

    message = payload.get("message", "").strip()
    if not message:
        return _json_response(400, {"success": False, "error": u"消息不能为空"})

    # Special commands
    if message == "/reset":
        llm.reset()
        return _json_response(200, {
            "success": True, "action": "reset",
            "reply": u"对话已重置", "screenshot_url": "",
        })

    if message == "/help":
        return _json_response(200, {
            "success": True, "action": "help",
            "reply": _HELP_TEXT, "screenshot_url": "",
        })

    if message == "/status":
        pending = handler.has_pending()
        status_text = u"队列中有待处理命令" if pending else u"服务器空闲"
        return _json_response(200, {
            "success": True, "action": "status",
            "reply": status_text, "screenshot_url": "",
        })

    # Normal chat: call LLM
    try:
        reply_text, command = llm.chat(message)
    except Exception as err:
        return _json_response(500, {
            "success": False, "error": str(err),
        })

    # If no actionable command, return LLM reply directly
    if command is None:
        return _json_response(200, {
            "success": True, "reply": reply_text,
            "action": "chat", "screenshot_url": "",
        })

    # Enqueue command to Revit handler and wait for result
    event = handler.enqueue_command(command)
    completed = event.wait(30)

    if not completed:
        return _json_response(504, {
            "success": False, "error": u"Revit 执行超时（30秒）",
        })

    result = handler.get_result()
    if result is None:
        return _json_response(500, {
            "success": False, "error": u"未获取到执行结果",
        })

    screenshot_url = ""
    if result.get("screenshot"):
        screenshot_url = "/api/screenshot/{}".format(result["screenshot"])

    return _json_response(200, {
        "success": result.get("success", False),
        "reply": result.get("message", reply_text),
        "action": result.get("action", command.get("action", "")),
        "screenshot_url": screenshot_url,
    })


def _handle_screenshot(name, screenshot_dir):
    """Serve a screenshot file by name. Returns (status, body).

    For file responses, returns a special marker ``__FILE__:<path>``
    so the listener layer can send the file bytes.
    """
    if not name or ".." in name or "/" in name or "\\" in name:
        return _json_response(404, {"error": "not found"})

    filepath = os.path.join(screenshot_dir, name)
    if not os.path.isfile(filepath):
        return _json_response(404, {"error": "not found"})

    return 200, "__FILE__:{}".format(filepath)


def _route_request(method, path, body, handler, llm, screenshot_dir):
    """Route an HTTP request to the appropriate handler.

    Parameters
    ----------
    method : str
        HTTP method (GET, POST, etc.)
    path : str
        Request path (e.g. "/api/health")
    body : str or None
        Request body (for POST requests)
    handler : RevitClawHandler
        Command queue handler
    llm : RevitClawLLMClient
        LLM conversation client
    screenshot_dir : str
        Directory where screenshots are stored

    Returns
    -------
    (int, str)
        (status_code, response_body_json)
    """
    if method == "GET" and path == "/api/health":
        return _json_response(200, {"status": "ok", "revit": True})

    if method == "POST" and path == "/api/chat":
        return _handle_chat(body, handler, llm, screenshot_dir)

    if method == "GET" and path.startswith("/api/screenshot/"):
        name = path[len("/api/screenshot/"):]
        return _handle_screenshot(name, screenshot_dir)

    return _json_response(404, {"error": "not found"})


# ---------------------------------------------------------------------------
# Server class (HttpListener backend for IronPython)
# ---------------------------------------------------------------------------

class RevitClawServer(object):
    """HTTP server wrapper for RevitClaw.

    On IronPython (inside Revit), uses .NET HttpListener.
    On CPython (Mac dev), start() is a no-op.
    """

    def __init__(self, handler, llm, port=8080, screenshot_dir=""):
        self.handler = handler
        self.llm = llm
        self.port = port
        self.screenshot_dir = screenshot_dir
        self._running = False
        self._thread = None

    def start(self):
        """Launch the HTTP listener in a background daemon thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_listener)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        """Signal the listener to stop."""
        self._running = False

    def is_running(self):
        """Check whether the server is running."""
        return self._running

    def _get_chat_html_path(self):
        """Locate chat.html relative to project root."""
        # __file__ is at project_root/AISmartBuild.extension/lib/revitclaw/http_server.py
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )))
        return os.path.join(project_root, "revitclaw", "chat.html")

    def _run_listener(self):
        """Main HTTP server loop.

        Uses Python BaseHTTPServer (works in both CPython and IronPython,
        no admin privileges required).
        """
        server_ref = self

        try:
            # Python 2 (IronPython)
            from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
        except ImportError:
            # Python 3
            from http.server import HTTPServer, BaseHTTPRequestHandler

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # suppress console logs

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def _handle(self, method):
                path = self.path.split("?")[0]

                # Serve chat.html
                if method == "GET" and path in ("/", "/index.html"):
                    self._serve_file_response(
                        server_ref._get_chat_html_path(),
                        "text/html; charset=utf-8",
                    )
                    return

                # Read POST body
                body = None
                if method == "POST":
                    length = int(self.headers.get("Content-Length", 0))
                    if length > 0:
                        body = self.rfile.read(length)
                        if isinstance(body, bytes):
                            body = body.decode("utf-8")

                status, resp_body = _route_request(
                    method, path, body,
                    server_ref.handler, server_ref.llm,
                    server_ref.screenshot_dir,
                )

                # File response (screenshot)
                if resp_body.startswith("__FILE__:"):
                    filepath = resp_body[len("__FILE__:"):]
                    self._serve_file_response(filepath, "image/png")
                    return

                # JSON response
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(resp_body.encode("utf-8"))

            def _serve_file_response(self, filepath, content_type):
                try:
                    with open(filepath, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                except Exception:
                    self.send_response(404)
                    self.end_headers()

        try:
            httpd = HTTPServer(("0.0.0.0", self.port), Handler)
            httpd.timeout = 1
            while self._running:
                httpd.handle_request()
            httpd.server_close()
        except Exception:
            pass
        finally:
            self._running = False
