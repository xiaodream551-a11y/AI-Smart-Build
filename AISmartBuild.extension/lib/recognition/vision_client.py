# -*- coding: utf-8 -*-
"""Vision API client for multimodal LLM calls with image input."""

import base64
import json
import os

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen  # IronPython / Python 2

from config import VISION_API_KEY, VISION_API_URL, VISION_MODEL, VISION_TIMEOUT_MS


_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def _encode_image(image_path):
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _guess_media_type(image_path):
    """Guess MIME type from file extension."""
    ext = os.path.splitext(image_path)[1].lower()
    return _MEDIA_TYPES.get(ext, "image/png")


def _strip_markdown_fence(text):
    """Remove ```json ... ``` wrappers if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def call_vision_api(image_path, prompt, api_key=None, api_url=None,
                    model=None, timeout_ms=None):
    """Call a multimodal LLM with an image and text prompt.

    Args:
        image_path: Path to the image file.
        prompt: Text prompt for the LLM.
        api_key: API key (default from config).
        api_url: API endpoint (default from config).
        model: Model name (default from config).
        timeout_ms: Timeout in milliseconds.

    Returns:
        dict: Parsed JSON response from the LLM.

    Raises:
        ValueError: If API key is missing or JSON cannot be parsed.
        Exception: If the HTTP request fails.
    """
    api_key = api_key or VISION_API_KEY
    api_url = api_url or VISION_API_URL
    model = model or VISION_MODEL
    timeout_s = (timeout_ms or VISION_TIMEOUT_MS) / 1000.0

    if not api_key:
        raise ValueError(u"未配置视觉 API 密钥 (VISION_API_KEY)")

    if not os.path.isfile(image_path):
        raise ValueError(u"图片文件不存在: {}".format(image_path))

    image_b64 = _encode_image(image_path)
    media_type = _guess_media_type(image_path)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:{};base64,{}".format(media_type, image_b64),
                        },
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    data = json.dumps(payload).encode("utf-8")
    req = Request(
        api_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(api_key),
        },
    )

    try:
        resp = urlopen(req, timeout=timeout_s)
        body = json.loads(resp.read().decode("utf-8"))
    except Exception as err:
        raise Exception(u"视觉 API 请求失败: {}".format(str(err)))

    content = body["choices"][0]["message"]["content"]
    text = _strip_markdown_fence(content)

    try:
        return json.loads(text)
    except (ValueError, KeyError) as err:
        raise ValueError(
            u"视觉 API 返回的 JSON 无法解析: {}\n原文: {}".format(str(err), text[:500])
        )
