# RevitClaw Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable remote Revit modeling from a phone browser, with LLM-parsed commands executed in Revit and screenshot feedback returned.

**Architecture:** Two HTTP server implementations (Flask for Mac offline dev, .NET HttpListener for Revit IronPython) sharing identical API routes. Revit side uses Idling event to execute commands on the main thread. Screenshots captured after each command.

**Tech Stack:** Flask (Mac), .NET HttpListener + WebClient (Revit/IronPython), existing AI SmartBuild engine for command execution.

---

### Task 1: Update chat.html — screenshot display + loading animation

**Files:**

- Modify: `revitclaw/chat.html`

- [ ] **Step 1: Write test plan (manual verification)**

chat.html is a single-file frontend; we'll verify via the running Flask server. Test cases:

1. Send a message -> "执行中..." spinner appears while waiting
2. Response with `screenshot_url` -> image shown in chat bubble, clickable to enlarge
3. Response without `screenshot_url` -> text-only bubble (existing behavior)
4. Connection status shows "已连接(离线)" or "已连接(Revit)"

- [ ] **Step 2: Add loading animation and screenshot support**

Replace the `<script>` section in `revitclaw/chat.html`. Key changes:

Add CSS for loading spinner and image lightbox after existing styles:

```css
.msg.loading {
  align-self: flex-start;
  background: #fff;
  color: #999;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.msg.loading .dots::after {
  content: "";
  animation: dots 1.5s steps(4, end) infinite;
}

@keyframes dots {
  0% {
    content: "";
  }
  25% {
    content: ".";
  }
  50% {
    content: "..";
  }
  75% {
    content: "...";
  }
}

.msg img {
  max-width: 100%;
  border-radius: 8px;
  margin-top: 8px;
  cursor: pointer;
}

.lightbox {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 100;
  justify-content: center;
  align-items: center;
}

.lightbox.active {
  display: flex;
}

.lightbox img {
  max-width: 95%;
  max-height: 95%;
  border-radius: 8px;
}
```

Add lightbox div before closing `</body>`:

```html
<div class="lightbox" id="lightbox" onclick="this.classList.remove('active')">
  <img id="lightboxImg" src="" />
</div>
```

Update the `addMessage` function to handle screenshots:

```javascript
function addMessage(text, type, meta, screenshotUrl) {
  const div = document.createElement("div");
  div.className = "msg " + type;
  div.textContent = text;
  if (screenshotUrl) {
    const img = document.createElement("img");
    img.src = screenshotUrl;
    img.onclick = function () {
      document.getElementById("lightboxImg").src = screenshotUrl;
      document.getElementById("lightbox").classList.add("active");
    };
    div.appendChild(img);
  }
  if (meta) {
    const metaEl = document.createElement("div");
    metaEl.className = "meta";
    metaEl.textContent = meta;
    div.appendChild(metaEl);
  }
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}
```

Update the `send` function to show loading and handle screenshots:

```javascript
async function send() {
  const text = inputEl.value.trim();
  if (!text) return;

  addMessage(text, "user");
  inputEl.value = "";
  sendBtn.disabled = true;

  const loadingDiv = addMessage("执行中", "loading");
  const dotsSpan = document.createElement("span");
  dotsSpan.className = "dots";
  loadingDiv.appendChild(dotsSpan);

  try {
    const resp = await fetch(API_BASE + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    const data = await resp.json();
    loadingDiv.remove();

    if (data.success) {
      addMessage(
        data.reply,
        "bot",
        data.action || "",
        data.screenshot_url || null,
      );
    } else {
      addMessage(data.error || "请求失败", "error");
    }
  } catch (err) {
    loadingDiv.remove();
    addMessage("无法连接服务器: " + err.message, "error");
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}
```

Update `checkConnection` to show mode detail:

```javascript
async function checkConnection() {
  try {
    const resp = await fetch(API_BASE + "/api/health", {
      signal: AbortSignal.timeout(3000),
    });
    const data = await resp.json();
    statusEl.textContent = data.revit ? "已连接(Revit)" : "已连接(离线)";
    statusEl.classList.add("connected");
  } catch {
    statusEl.textContent = "未连接";
    statusEl.classList.remove("connected");
  }
}
```

- [ ] **Step 3: Verify in browser**

Run: open `http://127.0.0.1:8080` in browser, send a message, confirm loading animation appears and disappears when response arrives. Status should show "已连接(离线)".

- [ ] **Step 4: Commit**

```bash
git add revitclaw/chat.html
git commit -m "feat(revitclaw): add screenshot display and loading animation to chat UI"
```

---

### Task 2: Add screenshot route to Flask server

**Files:**

- Modify: `revitclaw/server.py`
- Modify: `tests/test_revitclaw_server.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_revitclaw_server.py`:

```python
class TestScreenshotEndpoint:
    def test_screenshot_not_found(self, client):
        resp = client.get("/api/screenshot/nonexistent.png")
        assert resp.status_code == 404

    def test_screenshot_serves_file(self, client, tmp_path):
        # Create a temp screenshot
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG fake image data")
        with _lock:
            _state["screenshot_dir"] = str(tmp_path)
        resp = client.get("/api/screenshot/test.png")
        assert resp.status_code == 200
        assert b"PNG" in resp.data

    def test_screenshot_blocks_path_traversal(self, client, tmp_path):
        with _lock:
            _state["screenshot_dir"] = str(tmp_path)
        resp = client.get("/api/screenshot/../../../etc/passwd")
        assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_revitclaw_server.py::TestScreenshotEndpoint -v`
Expected: FAIL — route doesn't exist yet, `screenshot_dir` not in `_state`

- [ ] **Step 3: Implement screenshot route**

In `revitclaw/server.py`, add `screenshot_dir` to `_state`:

```python
_state = {
    "revit_mode": False,
    "command_queue": [],
    "result_queue": [],
    "conversation": [
        {"role": "system", "content": SYSTEM_PROMPT},
    ],
    "max_turns": 20,
    "screenshot_dir": str(Path(__file__).parent / "screenshots"),
}
```

Add the route after the existing `/api/result` route:

```python
@app.route("/api/screenshot/<name>")
def screenshot(name):
    """Serve a screenshot image file."""
    safe_name = Path(name).name  # strip path traversal
    filepath = Path(_state["screenshot_dir"]) / safe_name
    if not filepath.is_file():
        return jsonify({"error": "not found"}), 404
    return send_file(str(filepath))
```

Also update the chat response to include `screenshot_url` when a result has a screenshot. In the `chat()` function, after the LLM call block, before the return:

```python
    screenshot_url = ""
    if command and _state["revit_mode"]:
        with _lock:
            _state["command_queue"].append(command)
        action_name = command.get("action", "")
    elif command:
        action_name = command.get("action", "") + " (离线模式，未执行)"

    return jsonify({
        "success": True,
        "reply": reply_text,
        "action": action_name,
        "command": command,
        "screenshot_url": screenshot_url if screenshot_url else None,
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_revitclaw_server.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add revitclaw/server.py tests/test_revitclaw_server.py
git commit -m "feat(revitclaw): add screenshot serving endpoint to Flask server"
```

---

### Task 3: Create Revit-side LLM client (IronPython/.NET WebClient)

**Files:**

- Create: `AISmartBuild.extension/lib/revitclaw/__init__.py`
- Create: `AISmartBuild.extension/lib/revitclaw/llm_client.py`
- Create: `tests/test_revitclaw_llm_client.py`

- [ ] **Step 1: Create package init**

Create `AISmartBuild.extension/lib/revitclaw/__init__.py`:

```python
# -*- coding: utf-8 -*-
"""RevitClaw -- remote Revit control from mobile browser."""
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_revitclaw_llm_client.py`:

````python
# -*- coding: utf-8 -*-
"""Tests for RevitClaw IronPython LLM client."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "AISmartBuild.extension" / "lib"))

from revitclaw.llm_client import RevitClawLLMClient, parse_command_from_reply


class TestParseCommandFromReply:
    def test_pure_json(self):
        text = '{"action": "create_column", "params": {"x": 0}}'
        cmd = parse_command_from_reply(text)
        assert cmd["action"] == "create_column"

    def test_markdown_fenced(self):
        text = '```json\n{"action": "create_beam", "params": {}}\n```'
        cmd = parse_command_from_reply(text)
        assert cmd["action"] == "create_beam"

    def test_mixed_text_with_json(self):
        text = u'好的，我来创建。\n{"action": "create_column", "params": {"x": 0}}'
        cmd = parse_command_from_reply(text)
        assert cmd["action"] == "create_column"

    def test_plain_text_returns_none(self):
        assert parse_command_from_reply(u"没有JSON内容") is None

    def test_batch_array(self):
        text = '[{"action": "create_column"}, {"action": "create_beam"}]'
        cmd = parse_command_from_reply(text)
        assert cmd["action"] == "batch"
        assert len(cmd["params"]["commands"]) == 2


class TestRevitClawLLMClient:
    def test_init_loads_config(self):
        client = RevitClawLLMClient(
            api_url="https://example.com/v1/chat/completions",
            api_key="test-key",
            model="glm-4-flash",
        )
        assert client.api_url == "https://example.com/v1/chat/completions"
        assert client.model == "glm-4-flash"

    def test_build_payload(self):
        client = RevitClawLLMClient(
            api_url="https://example.com/v1/chat/completions",
            api_key="test-key",
            model="glm-4-flash",
        )
        client.conversation = [
            {"role": "system", "content": "prompt"},
            {"role": "user", "content": "test"},
        ]
        payload = client._build_payload()
        assert payload["model"] == "glm-4-flash"
        assert len(payload["messages"]) == 2

    def test_conversation_trimming(self):
        client = RevitClawLLMClient(
            api_url="https://example.com/v1/chat/completions",
            api_key="test-key",
            model="glm-4-flash",
            max_turns=2,
        )
        client.conversation = [{"role": "system", "content": "prompt"}]
        # Add 5 turn pairs (10 messages)
        for i in range(5):
            client.conversation.append({"role": "user", "content": "q{}".format(i)})
            client.conversation.append({"role": "assistant", "content": "a{}".format(i)})
        client._trim_conversation()
        # system + max_turns*2 = 1 + 4 = 5
        assert len(client.conversation) == 5
        assert client.conversation[0]["role"] == "system"

    def test_reset_clears_conversation(self):
        client = RevitClawLLMClient(
            api_url="https://example.com/v1/chat/completions",
            api_key="test-key",
            model="glm-4-flash",
        )
        client.conversation.append({"role": "user", "content": "test"})
        client.reset()
        assert len(client.conversation) == 1
        assert client.conversation[0]["role"] == "system"
````

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_revitclaw_llm_client.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 4: Implement llm_client.py**

Create `AISmartBuild.extension/lib/revitclaw/llm_client.py`:

````python
# -*- coding: utf-8 -*-
"""LLM client for RevitClaw.

Designed for both CPython (Mac offline) and IronPython (Revit).
Uses urllib on CPython, can be monkey-patched for .NET WebClient on IronPython.
"""

import json
import ssl

from ai.prompt import SYSTEM_PROMPT


def parse_command_from_reply(text):
    """Extract a JSON command dict from LLM reply text.

    Returns dict with 'action' key, or None if no command found.
    """
    text = text.strip()

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # Try full text as JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "action" in obj:
            return obj
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            return {"action": "batch", "params": {"commands": obj}}
    except (ValueError, KeyError):
        pass

    # Scan for embedded JSON object
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


class RevitClawLLMClient(object):
    """LLM client that manages conversation state."""

    def __init__(self, api_url, api_key, model, max_turns=20, timeout_s=30):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.max_turns = max_turns
        self.timeout_s = timeout_s
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    def reset(self):
        """Clear conversation history."""
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    def chat(self, user_message):
        """Send a message and get LLM reply + parsed command.

        Returns:
            (reply_text, command_dict_or_None)
        """
        self.conversation.append({"role": "user", "content": user_message})
        self._trim_conversation()

        try:
            reply = self._call_api()
        except Exception:
            self.conversation.pop()
            raise

        self.conversation.append({"role": "assistant", "content": reply})
        command = parse_command_from_reply(reply)
        return reply, command

    def _build_payload(self):
        return {
            "model": self.model,
            "messages": list(self.conversation),
            "temperature": 0.1,
        }

    def _trim_conversation(self):
        max_messages = self.max_turns * 2 + 1
        if len(self.conversation) > max_messages:
            self.conversation = (
                self.conversation[:1] +
                self.conversation[-(max_messages - 1):]
            )

    def _call_api(self):
        """Call LLM API via urllib. Override for IronPython .NET WebClient."""
        import urllib.request

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        payload = self._build_payload()
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.api_key),
            },
        )

        resp = urllib.request.urlopen(req, timeout=self.timeout_s, context=ssl_ctx)
        body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
````

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_revitclaw_llm_client.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add AISmartBuild.extension/lib/revitclaw/__init__.py \
        AISmartBuild.extension/lib/revitclaw/llm_client.py \
        tests/test_revitclaw_llm_client.py
git commit -m "feat(revitclaw): add LLM client with conversation management"
```

---

### Task 4: Create Revit screenshot module

**Files:**

- Create: `AISmartBuild.extension/lib/revitclaw/screenshot.py`
- Create: `tests/test_revitclaw_screenshot.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_revitclaw_screenshot.py`:

```python
# -*- coding: utf-8 -*-
"""Tests for RevitClaw screenshot module."""

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "AISmartBuild.extension" / "lib"))

from revitclaw.screenshot import capture_screenshot, get_screenshot_dir


class TestGetScreenshotDir:
    def test_returns_path(self, tmp_path):
        result = get_screenshot_dir(str(tmp_path))
        assert Path(result).is_dir()

    def test_creates_dir_if_missing(self, tmp_path):
        target = tmp_path / "screenshots"
        result = get_screenshot_dir(str(target))
        assert Path(result).is_dir()


class TestCaptureScreenshot:
    def test_calls_export_image(self, tmp_path):
        mock_doc = MagicMock()
        mock_doc.ActiveView = MagicMock()
        mock_doc.ActiveView.Id = MagicMock()
        mock_doc.ActiveView.Id.IntegerValue = 42

        mock_options = MagicMock()
        mock_db = MagicMock()
        mock_db.ImageExportOptions = MagicMock(return_value=mock_options)
        mock_db.ImageFileType = MagicMock()
        mock_db.ImageFileType.PNG = "PNG"
        mock_db.ImageResolution = MagicMock()
        mock_db.ImageResolution.DPI_150 = 150

        filepath = capture_screenshot(mock_doc, mock_db, str(tmp_path))

        assert filepath is not None
        mock_doc.ExportImage.assert_called_once()

    def test_returns_none_on_error(self, tmp_path):
        mock_doc = MagicMock()
        mock_doc.ActiveView = None
        mock_db = MagicMock()

        filepath = capture_screenshot(mock_doc, mock_db, str(tmp_path))
        assert filepath is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_revitclaw_screenshot.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement screenshot.py**

Create `AISmartBuild.extension/lib/revitclaw/screenshot.py`:

```python
# -*- coding: utf-8 -*-
"""Revit screenshot capture for RevitClaw.

DB is passed in as parameter -- never imported directly.
"""

import os
import time


def get_screenshot_dir(base_dir=None):
    """Ensure screenshot directory exists and return its path."""
    if base_dir is None:
        base_dir = os.path.join(os.environ.get("TEMP", "/tmp"), "revitclaw_screenshots")
    if not os.path.isdir(base_dir):
        os.makedirs(base_dir)
    return base_dir


def capture_screenshot(doc, DB, output_dir):
    """Capture current Revit active view as a PNG.

    Args:
        doc: Revit Document
        DB: Revit DB namespace (passed in, not imported)
        output_dir: Directory to save the screenshot

    Returns:
        str: File path of the saved screenshot, or None on failure.
    """
    try:
        view = doc.ActiveView
        if view is None:
            return None

        output_dir = get_screenshot_dir(output_dir)
        filename = "revitclaw_{}".format(int(time.time() * 1000))

        options = DB.ImageExportOptions()
        options.FilePath = os.path.join(output_dir, filename)
        options.ExportRange = DB.ExportRange.CurrentView
        options.HLRandWFViewsFileType = DB.ImageFileType.PNG
        options.ShadowViewsFileType = DB.ImageFileType.PNG
        options.ImageResolution = DB.ImageResolution.DPI_150
        options.ZoomType = DB.ZoomFitType.FitToPage
        options.PixelSize = 1920

        doc.ExportImage(options)

        result_path = options.FilePath + ".png"
        if os.path.isfile(result_path):
            return result_path

        return None
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_revitclaw_screenshot.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add AISmartBuild.extension/lib/revitclaw/screenshot.py \
        tests/test_revitclaw_screenshot.py
git commit -m "feat(revitclaw): add Revit screenshot capture module"
```

---

### Task 5: Create Revit command handler (Idling event + command execution)

**Files:**

- Create: `AISmartBuild.extension/lib/revitclaw/handler.py`
- Create: `tests/test_revitclaw_handler.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_revitclaw_handler.py`:

```python
# -*- coding: utf-8 -*-
"""Tests for RevitClaw command handler."""

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Bootstrap offline runtime
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import offline_runtime
offline_runtime.bootstrap()

from revitclaw.handler import RevitClawHandler


class TestRevitClawHandler:
    def _make_handler(self, tmp_path):
        mock_doc = MagicMock()
        mock_db = MagicMock()
        return RevitClawHandler(
            doc=mock_doc,
            DB=mock_db,
            screenshot_dir=str(tmp_path),
        )

    def test_enqueue_and_dequeue(self, tmp_path):
        handler = self._make_handler(tmp_path)
        cmd = {"action": "create_column", "params": {"x": 0, "y": 0}}
        event = handler.enqueue_command(cmd)
        assert not event.is_set()
        assert handler.has_pending()

    def test_process_command_calls_dispatch(self, tmp_path):
        handler = self._make_handler(tmp_path)
        cmd = {"action": "query_summary", "params": {}}
        event = handler.enqueue_command(cmd)

        with patch("revitclaw.handler.dispatch_command", return_value=u"模型概况") as mock_dispatch:
            with patch("revitclaw.handler.capture_screenshot", return_value=None):
                handler.process_next()

        assert event.is_set()
        result = handler.get_result()
        assert result["success"] is True
        assert result["message"] == u"模型概况"

    def test_process_command_with_screenshot(self, tmp_path):
        handler = self._make_handler(tmp_path)
        cmd = {"action": "create_column", "params": {"x": 0}}
        handler.enqueue_command(cmd)

        fake_path = str(tmp_path / "shot.png")
        with patch("revitclaw.handler.dispatch_command", return_value=u"已创建"):
            with patch("revitclaw.handler.capture_screenshot", return_value=fake_path):
                with patch("revitclaw.handler.get_sorted_levels", return_value=[]):
                    handler.process_next()

        result = handler.get_result()
        assert result["screenshot"] == "shot.png"

    def test_process_command_handles_exception(self, tmp_path):
        handler = self._make_handler(tmp_path)
        cmd = {"action": "create_column", "params": {}}
        handler.enqueue_command(cmd)

        with patch("revitclaw.handler.dispatch_command", side_effect=Exception("boom")):
            with patch("revitclaw.handler.get_sorted_levels", return_value=[]):
                handler.process_next()

        result = handler.get_result()
        assert result["success"] is False
        assert "boom" in result["message"]

    def test_no_pending_does_nothing(self, tmp_path):
        handler = self._make_handler(tmp_path)
        assert not handler.has_pending()
        handler.process_next()  # should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_revitclaw_handler.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement handler.py**

Create `AISmartBuild.extension/lib/revitclaw/handler.py`:

```python
# -*- coding: utf-8 -*-
"""RevitClaw command handler.

Manages a command queue consumed by Revit's Idling event.
DB is passed in -- never imported directly.
"""

import os
import threading

from ai.parser import dispatch_command
from revitclaw.screenshot import capture_screenshot
from utils import get_sorted_levels


class RevitClawHandler(object):
    """Processes commands from the HTTP server on the Revit main thread."""

    def __init__(self, doc, DB, screenshot_dir):
        self.doc = doc
        self.DB = DB
        self.screenshot_dir = screenshot_dir
        self._levels = None
        self._queue = []       # list of (command_dict, threading.Event)
        self._results = []     # list of result dicts
        self._lock = threading.Lock()

    def enqueue_command(self, command):
        """Add a command to the queue. Returns a threading.Event that signals completion."""
        event = threading.Event()
        with self._lock:
            self._queue.append((command, event))
        return event

    def has_pending(self):
        with self._lock:
            return len(self._queue) > 0

    def get_result(self):
        """Pop the oldest result."""
        with self._lock:
            if self._results:
                return self._results.pop(0)
        return None

    def process_next(self):
        """Process the next queued command. Call this from Revit Idling event."""
        with self._lock:
            if not self._queue:
                return
            command, event = self._queue.pop(0)

        try:
            if self._levels is None:
                self._levels = get_sorted_levels(self.doc)

            result_text = dispatch_command(self.doc, command, self._levels)

            # Refresh levels after modifying commands
            action = command.get("action", "")
            if action in ("create_column", "create_beam", "create_slab",
                          "generate_frame", "delete_element", "batch"):
                self._levels = get_sorted_levels(self.doc)

            # Capture screenshot
            screenshot_path = capture_screenshot(
                self.doc, self.DB, self.screenshot_dir
            )
            screenshot_name = ""
            if screenshot_path:
                screenshot_name = os.path.basename(screenshot_path)

            result = {
                "success": True,
                "message": result_text,
                "action": action,
                "screenshot": screenshot_name,
            }
        except Exception as err:
            result = {
                "success": False,
                "message": str(err),
                "action": command.get("action", "unknown"),
                "screenshot": "",
            }

        with self._lock:
            self._results.append(result)
        event.set()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_revitclaw_handler.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add AISmartBuild.extension/lib/revitclaw/handler.py \
        tests/test_revitclaw_handler.py
git commit -m "feat(revitclaw): add Revit command handler with Idling queue"
```

---

### Task 6: Create Revit-side HTTP server (HttpListener)

**Files:**

- Create: `AISmartBuild.extension/lib/revitclaw/http_server.py`
- Create: `tests/test_revitclaw_http_server.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_revitclaw_http_server.py`:

```python
# -*- coding: utf-8 -*-
"""Tests for RevitClaw HTTP server (portable layer, no .NET dependency)."""

import json
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import offline_runtime
offline_runtime.bootstrap()

from revitclaw.http_server import RevitClawServer, _route_request


class TestRouteRequest:
    def _make_deps(self):
        handler = MagicMock()
        handler.has_pending.return_value = False
        llm = MagicMock()
        return handler, llm

    def test_health(self):
        handler, llm = self._make_deps()
        status, body = _route_request("GET", "/api/health", None, handler, llm, "/tmp")
        assert status == 200
        data = json.loads(body)
        assert data["status"] == "ok"
        assert data["revit"] is True

    def test_chat_empty_message(self):
        handler, llm = self._make_deps()
        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": ""}),
            handler, llm, "/tmp",
        )
        assert status == 400

    def test_chat_reset(self):
        handler, llm = self._make_deps()
        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": "/reset"}),
            handler, llm, "/tmp",
        )
        data = json.loads(body)
        assert data["action"] == "reset"
        llm.reset.assert_called_once()

    def test_chat_calls_llm_and_queues(self):
        handler, llm = self._make_deps()
        llm.chat.return_value = (u"已创建柱子", {"action": "create_column", "params": {}})

        mock_event = MagicMock()
        mock_event.wait.return_value = True
        handler.enqueue_command.return_value = mock_event
        handler.get_result.return_value = {
            "success": True,
            "message": u"已创建柱子",
            "action": "create_column",
            "screenshot": "shot.png",
        }

        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": u"创建柱子"}),
            handler, llm, "/tmp",
        )
        data = json.loads(body)
        assert data["success"] is True
        assert data["screenshot_url"] == "/api/screenshot/shot.png"

    def test_chat_llm_error(self):
        handler, llm = self._make_deps()
        llm.chat.side_effect = Exception("API failed")

        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": "test"}),
            handler, llm, "/tmp",
        )
        assert status == 500

    def test_chat_query_action_no_queue(self):
        """Query actions should not be queued to Revit handler."""
        handler, llm = self._make_deps()
        llm.chat.return_value = (u"共有10根柱", {"action": "query_count", "params": {}})

        mock_event = MagicMock()
        mock_event.wait.return_value = True
        handler.enqueue_command.return_value = mock_event
        handler.get_result.return_value = {
            "success": True, "message": u"共有10根柱",
            "action": "query_count", "screenshot": "",
        }

        status, body = _route_request(
            "POST", "/api/chat", json.dumps({"message": u"查询柱数"}),
            handler, llm, "/tmp",
        )
        data = json.loads(body)
        assert data["success"] is True


class TestRevitClawServer:
    def test_init(self):
        handler = MagicMock()
        llm = MagicMock()
        server = RevitClawServer(handler, llm, port=8888, screenshot_dir="/tmp")
        assert server.port == 8888
        assert not server.is_running()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_revitclaw_http_server.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement http_server.py**

Create `AISmartBuild.extension/lib/revitclaw/http_server.py`:

```python
# -*- coding: utf-8 -*-
"""RevitClaw HTTP server.

Portable routing layer + platform-specific server backends.
On Revit/IronPython: uses System.Net.HttpListener.
On CPython (tests): routing logic is tested directly via _route_request.
"""

import json
import os
import threading


def _route_request(method, path, body, handler, llm, screenshot_dir):
    """Route an HTTP request and return (status_code, response_body_json).

    Args:
        method: "GET" or "POST"
        path: URL path, e.g. "/api/health"
        body: Request body string (for POST), or None
        handler: RevitClawHandler instance
        llm: RevitClawLLMClient instance
        screenshot_dir: Path to screenshot directory

    Returns:
        (int, str): HTTP status code and JSON response body
    """
    if path == "/api/health" and method == "GET":
        data = {
            "status": "ok",
            "revit": True,
            "queue_size": 1 if handler.has_pending() else 0,
        }
        return 200, json.dumps(data, ensure_ascii=False)

    if path == "/api/chat" and method == "POST":
        return _handle_chat(body, handler, llm, screenshot_dir)

    if path.startswith("/api/screenshot/") and method == "GET":
        name = path.split("/api/screenshot/", 1)[1]
        return _handle_screenshot(name, screenshot_dir)

    return 404, json.dumps({"error": "not found"})


def _handle_chat(body, handler, llm, screenshot_dir):
    """Handle POST /api/chat."""
    try:
        data = json.loads(body) if body else {}
    except (ValueError, TypeError):
        data = {}

    message = (data.get("message") or "").strip()
    if not message:
        return 400, json.dumps({"success": False, "error": u"消息不能为空"}, ensure_ascii=False)

    # Special commands
    if message == "/reset":
        llm.reset()
        return 200, json.dumps({
            "success": True, "reply": u"对话已重置", "action": "reset",
        }, ensure_ascii=False)

    if message == "/help":
        return 200, json.dumps({
            "success": True,
            "reply": (
                u"RevitClaw 命令帮助:\n"
                u"- 输入中文建模指令，AI 会解析并执行\n"
                u"- /reset  重置对话\n"
                u"- /status 查看系统状态\n\n"
                u"示例:\n"
                u'- "在1-A位置创建一根柱子"\n'
                u'- "生成3x2跨5层框架"\n'
                u'- "查询模型概况"'
            ),
            "action": "help",
        }, ensure_ascii=False)

    if message == "/status":
        return 200, json.dumps({
            "success": True,
            "reply": u"模式: Revit\n队列: {} 条待执行".format(
                1 if handler.has_pending() else 0,
            ),
            "action": "status",
        }, ensure_ascii=False)

    # Call LLM
    try:
        reply_text, command = llm.chat(message)
    except Exception as err:
        return 500, json.dumps({
            "success": False, "error": str(err),
        }, ensure_ascii=False)

    # Queue command for Revit execution
    screenshot_url = None
    action_name = ""
    if command:
        event = handler.enqueue_command(command)
        # Block until Revit processes it (timeout 30s)
        event.wait(timeout=30)
        result = handler.get_result()
        if result:
            action_name = result.get("action", "")
            if result.get("screenshot"):
                screenshot_url = "/api/screenshot/{}".format(result["screenshot"])
            if not result.get("success"):
                reply_text += u"\n\n执行失败: " + result.get("message", "")
        else:
            action_name = command.get("action", "") + u" (超时)"

    return 200, json.dumps({
        "success": True,
        "reply": reply_text,
        "action": action_name,
        "command": command,
        "screenshot_url": screenshot_url,
    }, ensure_ascii=False)


def _handle_screenshot(name, screenshot_dir):
    """Handle GET /api/screenshot/<name>. Returns file path or 404."""
    safe_name = os.path.basename(name)
    filepath = os.path.join(screenshot_dir, safe_name)
    if os.path.isfile(filepath):
        # Return special marker for the server backend to send the file
        return 200, "__FILE__:" + filepath
    return 404, json.dumps({"error": "not found"})


class RevitClawServer(object):
    """HTTP server wrapper. Start/stop from a Revit pushbutton."""

    def __init__(self, handler, llm, port=8080, screenshot_dir=None):
        self.handler = handler
        self.llm = llm
        self.port = port
        self.screenshot_dir = screenshot_dir or os.path.join(
            os.environ.get("TEMP", "/tmp"), "revitclaw_screenshots"
        )
        self._thread = None
        self._running = False
        self._chat_html = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)
            ))),
            "revitclaw", "chat.html"
        )

    def is_running(self):
        return self._running

    def start(self):
        """Start the HTTP server in a background thread.

        On IronPython, uses System.Net.HttpListener.
        """
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_listener)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        """Stop the HTTP server."""
        self._running = False

    def _run_listener(self):
        """Main server loop using .NET HttpListener (IronPython only)."""
        try:
            import clr
            clr.AddReference("System")
            from System.Net import HttpListener
            from System.IO import StreamReader, StreamWriter
            from System.Text import Encoding
        except ImportError:
            return

        listener = HttpListener()
        listener.Prefixes.Add("http://+:{}/".format(self.port))

        try:
            listener.Start()
        except Exception:
            self._running = False
            return

        while self._running:
            try:
                context = listener.GetContext()
                request = context.Request
                response = context.Response

                method = request.HttpMethod
                path = request.Url.AbsolutePath

                # Read body
                body = None
                if method == "POST":
                    reader = StreamReader(request.InputStream, request.ContentEncoding)
                    body = reader.ReadToEnd()

                # Serve chat.html for root
                if path == "/" and method == "GET":
                    with open(self._chat_html, "rb") as f:
                        html_bytes = f.read()
                    response.ContentType = "text/html; charset=utf-8"
                    response.ContentLength64 = len(html_bytes)
                    response.OutputStream.Write(html_bytes, 0, len(html_bytes))
                    response.OutputStream.Close()
                    continue

                # Route API requests
                status, resp_body = _route_request(
                    method, path, body,
                    self.handler, self.llm, self.screenshot_dir,
                )

                # Handle file responses
                if resp_body.startswith("__FILE__:"):
                    filepath = resp_body[9:]
                    with open(filepath, "rb") as f:
                        file_bytes = f.read()
                    response.ContentType = "image/png"
                    response.ContentLength64 = len(file_bytes)
                    response.OutputStream.Write(file_bytes, 0, len(file_bytes))
                    response.OutputStream.Close()
                    continue

                response.StatusCode = status
                response.ContentType = "application/json; charset=utf-8"
                resp_bytes = Encoding.UTF8.GetBytes(resp_body)
                response.ContentLength64 = resp_bytes.Length
                response.OutputStream.Write(resp_bytes, 0, resp_bytes.Length)
                response.OutputStream.Close()

            except Exception:
                if not self._running:
                    break

        try:
            listener.Stop()
        except Exception:
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_revitclaw_http_server.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add AISmartBuild.extension/lib/revitclaw/http_server.py \
        tests/test_revitclaw_http_server.py
git commit -m "feat(revitclaw): add HTTP server with routing and HttpListener backend"
```

---

### Task 7: Create pyRevit pushbutton (start/stop RevitClaw)

**Files:**

- Create: `AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/bundle.yaml`
- Create: `AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/script.py`
- Create: `tests/test_revitclaw_pushbutton.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_revitclaw_pushbutton.py`:

```python
# -*- coding: utf-8 -*-
"""Tests for RevitClaw pushbutton script."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import offline_runtime
offline_runtime.bootstrap()

# Load the pushbutton script as a module
pushbutton_script = offline_runtime.load_module_from_path(
    "revitclaw_pushbutton",
    "AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/script.py",
)


class TestRevitClawPushbutton:
    def test_module_loads(self):
        assert hasattr(pushbutton_script, "main")

    def test_toggle_start(self):
        """main() should start the server when not running."""
        with patch.object(pushbutton_script, "_server", None):
            with patch.object(pushbutton_script, "_start_server") as mock_start:
                pushbutton_script.main()
                mock_start.assert_called_once()

    def test_toggle_stop(self):
        """main() should stop the server when already running."""
        mock_server = MagicMock()
        mock_server.is_running.return_value = True
        with patch.object(pushbutton_script, "_server", mock_server):
            with patch.object(pushbutton_script, "_stop_server") as mock_stop:
                pushbutton_script.main()
                mock_stop.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_revitclaw_pushbutton.py -v`
Expected: FAIL — files don't exist

- [ ] **Step 3: Create bundle.yaml**

Create `AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/bundle.yaml`:

```yaml
title: "远程\n控制"
tooltip: 启动/停止 RevitClaw 远程控制服务
author: AI智建
```

- [ ] **Step 4: Create script.py**

Create `AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/script.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_revitclaw_pushbutton.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add "AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/bundle.yaml" \
        "AISmartBuild.extension/AISmartBuild.tab/RevitClaw.panel/StartClaw.pushbutton/script.py" \
        tests/test_revitclaw_pushbutton.py
git commit -m "feat(revitclaw): add pyRevit pushbutton for starting/stopping server"
```

---

### Task 8: Integration — run all tests, verify full offline chain

**Files:**

- No new files

- [ ] **Step 1: Run full test suite**

Run: `python3 -m pytest tests/ -v --tb=short`
Expected: ALL tests pass (existing 406 + new RevitClaw tests)

- [ ] **Step 2: Manual smoke test on Mac**

Start the Flask server and verify end-to-end:

```bash
python3 revitclaw/server.py --port 8080
```

Open `http://127.0.0.1:8080` in browser:

1. Status shows "已连接(离线)"
2. Send "在1-A创建柱子" -> loading animation -> response with JSON command
3. Send "/reset" -> "对话已重置"
4. Send "/help" -> help text
5. Send "/status" -> shows offline mode

- [ ] **Step 3: Commit any fixes**

If any tests needed fixes:

```bash
git add -u
git commit -m "fix(revitclaw): integration test fixes"
```

- [ ] **Step 4: Final commit with all tests passing**

Run: `python3 -m pytest tests/ --tb=no -q`
Verify count of passing tests, then:

```bash
git add docs/superpowers/
git commit -m "docs: add RevitClaw design spec and implementation plan"
```
