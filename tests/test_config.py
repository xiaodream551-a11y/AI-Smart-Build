# -*- coding: utf-8 -*-

import json
from pathlib import Path

from conftest import reload_module


def _write_user_config(home_dir, data):
    config_dir = Path(home_dir) / ".ai-smart-build"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    config_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config_path


def test_config_reads_user_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("AI_SMART_BUILD_DEEPSEEK_API_KEY", raising=False)

    config_path = _write_user_config(tmp_path, {
        "DEEPSEEK_API_KEY": "file-key",
        "DEEPSEEK_MODEL": "file-model",
    })

    config = reload_module("config")

    assert config.USER_CONFIG_PATH == str(config_path)
    assert config.DEEPSEEK_API_KEY == "file-key"
    assert config.DEEPSEEK_MODEL == "file-model"
    assert config.API_TIMEOUT_MS == 30000
    assert config.FRAME_API_TIMEOUT_MS == 60000
    assert config.API_RETRY_COUNT == 2
    assert config.API_RETRY_BACKOFF == 1.5
    assert config.MAX_CONVERSATION_TURNS == 20


def test_env_overrides_user_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
    monkeypatch.setenv("AI_SMART_BUILD_DEEPSEEK_MODEL", "env-model")
    monkeypatch.setenv("API_TIMEOUT_MS", "45000")
    monkeypatch.setenv("AI_SMART_BUILD_MAX_CONVERSATION_TURNS", "12")

    _write_user_config(tmp_path, {
        "DEEPSEEK_API_KEY": "file-key",
        "DEEPSEEK_MODEL": "file-model",
    })

    config = reload_module("config")

    assert config.DEEPSEEK_API_KEY == "env-key"
    assert config.DEEPSEEK_MODEL == "env-model"
    assert config.API_TIMEOUT_MS == 45000
    assert config.MAX_CONVERSATION_TURNS == 12


def test_config_falls_back_to_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("AI_SMART_BUILD_DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("AI_SMART_BUILD_DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_URL", raising=False)
    monkeypatch.delenv("AI_SMART_BUILD_DEEPSEEK_API_URL", raising=False)

    config = reload_module("config")

    assert config.DEEPSEEK_API_KEY == ""
    assert config.DEEPSEEK_MODEL == "deepseek-chat"
    assert config.DEEPSEEK_API_URL == "https://api.deepseek.com/v1/chat/completions"
    assert config.VERSION == "0.1.0"
    assert config.API_TIMEOUT_MS == 30000
    assert config.FRAME_API_TIMEOUT_MS == 60000
    assert config.API_RETRY_COUNT == 2
    assert config.API_RETRY_BACKOFF == 1.5
    assert config.MAX_CONVERSATION_TURNS == 20


def test_timeout_config_reads_user_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("API_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("AI_SMART_BUILD_API_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("FRAME_API_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("AI_SMART_BUILD_FRAME_API_TIMEOUT_MS", raising=False)

    _write_user_config(tmp_path, {
        "API_TIMEOUT_MS": 42000,
        "FRAME_API_TIMEOUT_MS": 88000,
    })

    config = reload_module("config")

    assert config.API_TIMEOUT_MS == 42000
    assert config.FRAME_API_TIMEOUT_MS == 88000


def test_retry_config_reads_user_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("API_RETRY_COUNT", raising=False)
    monkeypatch.delenv("AI_SMART_BUILD_API_RETRY_COUNT", raising=False)
    monkeypatch.delenv("API_RETRY_BACKOFF", raising=False)
    monkeypatch.delenv("AI_SMART_BUILD_API_RETRY_BACKOFF", raising=False)

    _write_user_config(tmp_path, {
        "API_RETRY_COUNT": 4,
        "API_RETRY_BACKOFF": 2.25,
    })

    config = reload_module("config")

    assert config.API_RETRY_COUNT == 4
    assert config.API_RETRY_BACKOFF == 2.25
