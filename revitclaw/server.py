# -*- coding: utf-8 -*-
"""RevitClaw relay server.

Modes:
  - Offline (Mac):  Calls DeepSeek API, returns LLM reply (no Revit execution)
  - Revit (Windows): Calls DeepSeek API + dispatches commands to Revit

Usage:
  python revitclaw/server.py                    # offline mode, port 5000
  python revitclaw/server.py --port 8080        # custom port
  python revitclaw/server.py --revit            # Revit mode (Windows only)
"""

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

from flask import Flask, request, jsonify, send_file

# Add lib to path for AI modules
LIB_DIR = Path(__file__).resolve().parents[1] / "AISmartBuild.extension" / "lib"
sys.path.insert(0, str(LIB_DIR))

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL, API_TIMEOUT_MS
from ai.prompt import SYSTEM_PROMPT

app = Flask(__name__)

# ── State ──
_state = {
    "revit_mode": False,
    "command_queue": [],       # commands waiting for Revit to pick up
    "result_queue": [],        # results from Revit execution
    "conversation": [
        {"role": "system", "content": SYSTEM_PROMPT},
    ],
    "max_turns": 20,
    "screenshot_dir": str(Path(__file__).parent / "screenshots"),
}
_lock = threading.Lock()


# ── Routes ──

@app.route("/")
def index():
    """Serve the chat page."""
    chat_html = Path(__file__).parent / "chat.html"
    return send_file(str(chat_html))


@app.route("/api/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "revit": _state["revit_mode"],
        "queue_size": len(_state["command_queue"]),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle a chat message from the mobile client.

    Request body: {"message": "用户输入"}
    Response: {"success": true, "reply": "...", "action": "...", "command": {...}}
    """
    data = request.get_json(force=True)
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "error": "消息不能为空"}), 400

    # Special commands
    if message == "/reset":
        with _lock:
            _state["conversation"] = [
                {"role": "system", "content": SYSTEM_PROMPT},
            ]
        return jsonify({"success": True, "reply": "对话已重置", "action": "reset"})

    if message == "/help":
        return jsonify({
            "success": True,
            "reply": (
                "RevitClaw 命令帮助:\n"
                "- 输入中文建模指令，AI 会解析并执行\n"
                "- /reset  重置对话\n"
                "- /status 查看系统状态\n"
                "- /queue  查看待执行队列\n\n"
                "示例:\n"
                '- "在1-A位置创建一根柱子"\n'
                '- "生成3x2跨5层框架"\n'
                '- "查询模型概况"'
            ),
            "action": "help",
        })

    if message == "/status":
        return jsonify({
            "success": True,
            "reply": "模式: {}\n队列: {} 条待执行\n对话轮次: {}".format(
                "Revit" if _state["revit_mode"] else "离线",
                len(_state["command_queue"]),
                (len(_state["conversation"]) - 1) // 2,
            ),
            "action": "status",
        })

    if message == "/queue":
        with _lock:
            queue = list(_state["command_queue"])
        if not queue:
            return jsonify({"success": True, "reply": "队列为空", "action": "queue"})
        lines = ["待执行命令 ({} 条):".format(len(queue))]
        for i, cmd in enumerate(queue):
            lines.append("  {}. {}".format(i + 1, cmd.get("action", "unknown")))
        return jsonify({"success": True, "reply": "\n".join(lines), "action": "queue"})

    # Call LLM
    try:
        reply_text, command = _call_llm(message)
    except Exception as err:
        return jsonify({"success": False, "error": str(err)}), 500

    # If Revit mode and we got a valid command, queue it
    action_name = ""
    if command and _state["revit_mode"]:
        with _lock:
            _state["command_queue"].append(command)
        # Write to pending file for Revit pushbutton to pick up
        _write_pending_command(command)
        action_name = command.get("action", "") + u" (已排队，在 Revit 点击执行)"

    elif command:
        action_name = command.get("action", "") + u" (离线模式，未执行)"

    return jsonify({
        "success": True,
        "reply": reply_text,
        "action": action_name,
        "command": command,
        "screenshot_url": None,
    })


@app.route("/api/poll", methods=["GET"])
def poll_command():
    """Revit agent polls this endpoint to get the next command.

    Returns:
        {"has_command": true, "command": {...}} or {"has_command": false}
    """
    with _lock:
        if _state["command_queue"]:
            cmd = _state["command_queue"].pop(0)
            return jsonify({"has_command": True, "command": cmd})
    return jsonify({"has_command": False})


@app.route("/api/result", methods=["POST"])
def post_result():
    """Revit agent posts execution results back.

    Request body: {"action": "...", "success": true, "message": "..."}
    """
    data = request.get_json(force=True)
    with _lock:
        _state["result_queue"].append(data)
    return jsonify({"status": "ok"})


@app.route("/api/screenshot/<name>")
def screenshot(name):
    """Serve a screenshot image file."""
    safe_name = Path(name).name  # strip path traversal
    filepath = Path(_state["screenshot_dir"]) / safe_name
    if not filepath.is_file():
        return jsonify({"error": "not found"}), 404
    return send_file(str(filepath))


# ── Pending command file ──

PENDING_FILE = str(Path(__file__).parent / "pending.json")


def _write_pending_command(command):
    """Append a command to the pending file for Revit to execute."""
    try:
        if os.path.isfile(PENDING_FILE):
            with open(PENDING_FILE, "r") as f:
                commands = json.load(f)
        else:
            commands = []
        commands.append(command)
        with open(PENDING_FILE, "w") as f:
            json.dump(commands, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── LLM call ──

def _call_llm(user_message):
    """Call the LLM API and extract command JSON.

    Returns:
        (reply_text, command_dict_or_None)
    """
    import ssl
    import urllib.request

    # macOS dev workaround for self-signed cert issues
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    with _lock:
        _state["conversation"].append({"role": "user", "content": user_message})
        # Trim conversation
        max_messages = _state["max_turns"] * 2 + 1
        if len(_state["conversation"]) > max_messages:
            _state["conversation"] = (
                _state["conversation"][:1] +
                _state["conversation"][-(max_messages - 1):]
            )
        messages = list(_state["conversation"])

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.1,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(DEEPSEEK_API_KEY),
        },
    )

    timeout_s = API_TIMEOUT_MS / 1000.0
    try:
        resp = urllib.request.urlopen(req, timeout=timeout_s, context=ssl_ctx)
        body = json.loads(resp.read().decode("utf-8"))
    except Exception as err:
        with _lock:
            _state["conversation"].pop()
        raise Exception("API 请求失败: {}".format(str(err)))

    reply = body["choices"][0]["message"]["content"]

    with _lock:
        _state["conversation"].append({"role": "assistant", "content": reply})

    # Try to parse JSON command from reply
    command = _try_parse_command(reply)

    return reply, command


def _try_parse_command(text):
    """Try to extract a JSON command from LLM reply text."""
    text = text.strip()

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "action" in obj:
            return obj
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            return {"action": "batch", "params": {"commands": obj}}
    except (ValueError, KeyError):
        pass

    # Try to find JSON by scanning for balanced braces
    for i, ch in enumerate(text):
        if ch == '{':
            depth = 0
            for j in range(i, len(text)):
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                if depth == 0:
                    candidate = text[i:j + 1]
                    try:
                        obj = json.loads(candidate)
                        if isinstance(obj, dict) and "action" in obj:
                            return obj
                    except (ValueError, KeyError):
                        pass
                    break

    return None


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="RevitClaw relay server")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--revit", action="store_true", help="Enable Revit execution mode")
    args = parser.parse_args()

    _state["revit_mode"] = args.revit

    # Show startup info
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "127.0.0.1"

    print("=" * 50)
    print("  RevitClaw Server")
    print("  Mode: {}".format("Revit" if args.revit else "Offline"))
    print("")
    print("  Local:   http://127.0.0.1:{}".format(args.port))
    print("  Network: http://{}:{}".format(local_ip, args.port))
    print("")
    print("  Scan the URL above on your phone")
    print("=" * 50)

    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
