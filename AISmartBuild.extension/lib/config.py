# -*- coding: utf-8 -*-
"""AI SmartBuild -- Global configuration."""

import io
import json
import os


def _load_user_config():
    """Load user-level configuration file."""
    path = os.path.expanduser("~/.ai-smart-build/config.json")
    if not os.path.exists(path):
        return path, {}

    try:
        with io.open(path, "r", encoding="utf-8-sig") as config_file:
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
# DeepSeek API configuration
# Priority: environment variable > ~/.ai-smart-build/config.json > default value
# ============================================================
VERSION = "0.1.0"
DEEPSEEK_API_URL = _read_config(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/v1/chat/completions",
    aliases=["AI_SMART_BUILD_DEEPSEEK_API_URL", "LLM_API_URL"],
)
DEEPSEEK_API_KEY = _read_config(
    "DEEPSEEK_API_KEY",
    "",
    aliases=["AI_SMART_BUILD_DEEPSEEK_API_KEY", "LLM_API_KEY"],
)
DEEPSEEK_MODEL = _read_config(
    "DEEPSEEK_MODEL",
    "deepseek-chat",
    aliases=["AI_SMART_BUILD_DEEPSEEK_MODEL", "LLM_MODEL"],
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
# Startup config validation
# ============================================================

def validate_config():
    """Validate critical configuration values.

    Returns a list of warning strings. An empty list means all checks passed.
    This function never raises exceptions or blocks execution.
    """
    warnings = []

    # 1. API key must be non-empty and not the placeholder
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY.strip() == "":
        warnings.append(u"API key 未设置，请在配置文件或环境变量中设置 DEEPSEEK_API_KEY 或 LLM_API_KEY")
    elif DEEPSEEK_API_KEY == "your-deepseek-api-key":
        warnings.append(u"API key 仍为占位符，请替换为实际的 API 密钥")

    # 2. API URL must look like a valid HTTP(S) URL
    url = DEEPSEEK_API_URL.strip() if DEEPSEEK_API_URL else ""
    if not url.startswith("http://") and not url.startswith("https://"):
        warnings.append(u"API URL 无效，必须以 http:// 或 https:// 开头")

    # 3. Model name must not be empty
    if not DEEPSEEK_MODEL or DEEPSEEK_MODEL.strip() == "":
        warnings.append(u"模型名称未设置，请在配置文件或环境变量中设置 DEEPSEEK_MODEL 或 LLM_MODEL")

    return warnings


# ============================================================
# Revit default parameters
# ============================================================
# Family names (Chinese Revit 2024 template)
COLUMN_FAMILY_NAME = u"混凝土-矩形-柱"
BEAM_FAMILY_NAME = u"混凝土-矩形梁"
FLOOR_TYPE_NAME = u"常规 - 150mm"

# Alternative family names (English template)
COLUMN_FAMILY_NAME_EN = "Concrete-Rectangular-Column"
BEAM_FAMILY_NAME_EN = "Concrete-Rectangular Beam"
FLOOR_TYPE_NAME_EN = "Generic - 150mm"

# Default cross-section dimensions (mm)
DEFAULT_COLUMN_SECTION = "500x500"
DEFAULT_BEAM_SECTION = "300x600"
DEFAULT_SLAB_THICKNESS = 120

# Default structural parameters
DEFAULT_FLOOR_COUNT = 5
DEFAULT_FLOOR_HEIGHT = 3600      # mm
DEFAULT_FIRST_FLOOR_HEIGHT = 4200  # mm (first floor height can differ)

# Grid labels
GRID_LABELS_X = [str(i) for i in range(1, 20)]           # 1, 2, 3, ...
GRID_LABELS_Y = [chr(i) for i in range(65, 91)]          # A, B, C, ...

# Grid extension beyond column center (mm)
GRID_EXTENSION = 1500
