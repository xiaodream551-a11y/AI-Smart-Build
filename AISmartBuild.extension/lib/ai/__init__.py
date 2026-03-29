# -*- coding: utf-8 -*-
"""AI 智建 — AI 对话模块"""

__all__ = []

try:
    from ai.client import DeepSeekClient, call_deepseek
    from ai.parser import parse_command, dispatch_command, normalize_command
    from ai.prompt import SYSTEM_PROMPT
except Exception:
    pass
else:
    __all__ = [
        "DeepSeekClient", "call_deepseek",
        "parse_command", "dispatch_command", "normalize_command",
        "SYSTEM_PROMPT",
    ]
