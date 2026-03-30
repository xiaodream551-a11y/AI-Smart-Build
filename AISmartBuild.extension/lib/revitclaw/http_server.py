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

    def _run_listener(self):
        """Main loop using .NET HttpListener (IronPython only).

        Gracefully exits on CPython where System.Net is unavailable.
        """
        try:
            import clr  # noqa: F401
            clr.AddReference("System")
            from System.Net import HttpListener
        except (ImportError, Exception):
            self._running = False
            return

        listener = HttpListener()
        listener.Prefixes.Add("http://+:{}/".format(self.port))

        try:
            listener.Start()
        except Exception:
            self._running = False
            return

        try:
            while self._running:
                try:
                    context = listener.GetContext()
                except Exception:
                    break

                request = context.Request
                response = context.Response

                try:
                    method = request.HttpMethod
                    path = request.Url.AbsolutePath

                    # Read request body
                    body = None
                    if request.HasEntityBody:
                        reader = __import__("System.IO", fromlist=["StreamReader"])
                        sr = reader.StreamReader(request.InputStream, request.ContentEncoding)
                        body = sr.ReadToEnd()
                        sr.Close()

                    # Serve chat.html for root path
                    if method == "GET" and path in ("/", "/index.html"):
                        self._serve_html(response)
                        continue

                    status, resp_body = _route_request(
                        method, path, body,
                        self.handler, self.llm, self.screenshot_dir,
                    )

                    # Handle file responses
                    if resp_body.startswith("__FILE__:"):
                        filepath = resp_body[len("__FILE__:"):]
                        self._serve_file(response, filepath)
                        continue

                    # Send JSON response
                    response.StatusCode = status
                    response.ContentType = "application/json; charset=utf-8"
                    buf = resp_body.encode("utf-8")
                    response.ContentLength64 = len(buf)
                    response.OutputStream.Write(buf, 0, len(buf))

                except Exception:
                    response.StatusCode = 500
                finally:
                    try:
                        response.OutputStream.Close()
                    except Exception:
                        pass
        finally:
            try:
                listener.Stop()
                listener.Close()
            except Exception:
                pass
            self._running = False

    def _serve_html(self, response):
        """Serve the chat.html file from the web directory."""
        try:
            html_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "revitclaw", "web",
            )
            html_path = os.path.join(html_dir, "chat.html")
            if os.path.isfile(html_path):
                with open(html_path, "rb") as f:
                    content = f.read()
                response.StatusCode = 200
                response.ContentType = "text/html; charset=utf-8"
                response.ContentLength64 = len(content)
                response.OutputStream.Write(content, 0, len(content))
            else:
                response.StatusCode = 404
        except Exception:
            response.StatusCode = 500

    def _serve_file(self, response, filepath):
        """Serve a binary file (screenshot)."""
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            response.StatusCode = 200
            response.ContentType = "image/png"
            response.ContentLength64 = len(content)
            response.OutputStream.Write(content, 0, len(content))
        except Exception:
            response.StatusCode = 500
