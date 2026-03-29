# -*- coding: utf-8 -*-
"""AI 智建 — 全局配置"""

import io
import json
import os


def _load_user_config():
    """读取用户级配置文件"""
    path = os.path.expanduser("~/.ai-smart-build/config.json")
    if not os.path.exists(path):
        return path, {}

    try:
        with io.open(path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
        if isinstance(data, dict):
            return path, data
    except Exception:
        pass

    return path, {}


def _read_config(key, default_value="", aliases=None):
    aliases = aliases or []
    for env_key in [key] + aliases:
        env_value = os.environ.get(env_key)
        if env_value:
            return env_value

    value = USER_CONFIG.get(key)
    if value not in (None, ""):
        return value

    for alias in aliases:
        value = USER_CONFIG.get(alias)
        if value not in (None, ""):
            return value

    return default_value


def _read_int_config(key, default_value, aliases=None):
    aliases = aliases or []
    value = _read_config(key, default_value, aliases=aliases)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default_value)


def _read_float_config(key, default_value, aliases=None):
    aliases = aliases or []
    value = _read_config(key, default_value, aliases=aliases)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default_value)


USER_CONFIG_PATH, USER_CONFIG = _load_user_config()

# ============================================================
# DeepSeek API 配置
# 优先级：环境变量 > ~/.ai-smart-build/config.json > 默认值
# ============================================================
VERSION = "0.1.0"
DEEPSEEK_API_URL = _read_config(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/v1/chat/completions",
    aliases=["AI_SMART_BUILD_DEEPSEEK_API_URL"]
)
DEEPSEEK_API_KEY = _read_config(
    "DEEPSEEK_API_KEY",
    "",
    aliases=["AI_SMART_BUILD_DEEPSEEK_API_KEY"]
)
DEEPSEEK_MODEL = _read_config(
    "DEEPSEEK_MODEL",
    "deepseek-chat",
    aliases=["AI_SMART_BUILD_DEEPSEEK_MODEL"]
)
API_TIMEOUT_MS = _read_int_config(
    "API_TIMEOUT_MS",
    30000,
    aliases=["AI_SMART_BUILD_API_TIMEOUT_MS"]
)
FRAME_API_TIMEOUT_MS = _read_int_config(
    "FRAME_API_TIMEOUT_MS",
    60000,
    aliases=["AI_SMART_BUILD_FRAME_API_TIMEOUT_MS"]
)
API_RETRY_COUNT = _read_int_config(
    "API_RETRY_COUNT",
    2,
    aliases=["AI_SMART_BUILD_API_RETRY_COUNT"]
)
API_RETRY_BACKOFF = _read_float_config(
    "API_RETRY_BACKOFF",
    1.5,
    aliases=["AI_SMART_BUILD_API_RETRY_BACKOFF"]
)
MAX_CONVERSATION_TURNS = _read_int_config(
    "MAX_CONVERSATION_TURNS",
    20,
    aliases=["AI_SMART_BUILD_MAX_CONVERSATION_TURNS"]
)

# ============================================================
# Revit 默认参数
# ============================================================
# 族名称（中文 Revit 2024 模板）
COLUMN_FAMILY_NAME = "混凝土-矩形-柱"
BEAM_FAMILY_NAME = "混凝土-矩形梁"
FLOOR_TYPE_NAME = "常规 - 150mm"

# 族名称备选（英文模板）
COLUMN_FAMILY_NAME_EN = "Concrete-Rectangular-Column"
BEAM_FAMILY_NAME_EN = "Concrete-Rectangular Beam"
FLOOR_TYPE_NAME_EN = "Generic - 150mm"

# 默认截面尺寸 (mm)
DEFAULT_COLUMN_SECTION = "500x500"
DEFAULT_BEAM_SECTION = "300x600"
DEFAULT_SLAB_THICKNESS = 120

# 默认结构参数
DEFAULT_FLOOR_COUNT = 5
DEFAULT_FLOOR_HEIGHT = 3600      # mm
DEFAULT_FIRST_FLOOR_HEIGHT = 4200  # mm（首层层高可不同）

# 轴网编号
GRID_LABELS_X = [str(i) for i in range(1, 20)]           # 1, 2, 3, ...
GRID_LABELS_Y = [chr(i) for i in range(65, 91)]          # A, B, C, ...

# 轴网超出柱中心的延伸长度 (mm)
GRID_EXTENSION = 1500
