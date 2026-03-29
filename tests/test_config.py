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


# ----------------------------------------------------------------
# Generic LLM_* alias tests
# ----------------------------------------------------------------


def _clear_all_llm_env(monkeypatch):
    """Remove all LLM-related env vars so config falls back to file/default."""
    for key in [
        "DEEPSEEK_API_KEY", "AI_SMART_BUILD_DEEPSEEK_API_KEY", "LLM_API_KEY",
        "DEEPSEEK_API_URL", "AI_SMART_BUILD_DEEPSEEK_API_URL", "LLM_API_URL",
        "DEEPSEEK_MODEL", "AI_SMART_BUILD_DEEPSEEK_MODEL", "LLM_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_llm_alias_env_var(monkeypatch, tmp_path):
    """LLM_* env vars should work when DEEPSEEK_* are not set."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    monkeypatch.setenv("LLM_API_KEY", "llm-env-key")
    monkeypatch.setenv("LLM_API_URL", "https://api.other.com/v1/chat")
    monkeypatch.setenv("LLM_MODEL", "other-model")

    config = reload_module("config")

    assert config.DEEPSEEK_API_KEY == "llm-env-key"
    assert config.DEEPSEEK_API_URL == "https://api.other.com/v1/chat"
    assert config.DEEPSEEK_MODEL == "other-model"


def test_llm_alias_config_file(monkeypatch, tmp_path):
    """LLM_* keys in config file should work as fallback."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    _write_user_config(tmp_path, {
        "LLM_API_KEY": "llm-file-key",
        "LLM_API_URL": "https://api.zhipu.com/v1/chat",
        "LLM_MODEL": "glm-4",
    })

    config = reload_module("config")

    assert config.DEEPSEEK_API_KEY == "llm-file-key"
    assert config.DEEPSEEK_API_URL == "https://api.zhipu.com/v1/chat"
    assert config.DEEPSEEK_MODEL == "glm-4"


def test_deepseek_takes_precedence_over_llm_in_file(monkeypatch, tmp_path):
    """DEEPSEEK_* in config file should take precedence over LLM_*."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    _write_user_config(tmp_path, {
        "DEEPSEEK_API_KEY": "ds-key",
        "LLM_API_KEY": "llm-key",
        "DEEPSEEK_MODEL": "deepseek-chat",
        "LLM_MODEL": "glm-4",
    })

    config = reload_module("config")

    assert config.DEEPSEEK_API_KEY == "ds-key"
    assert config.DEEPSEEK_MODEL == "deepseek-chat"


def test_deepseek_env_takes_precedence_over_llm_env(monkeypatch, tmp_path):
    """DEEPSEEK_* env vars should take precedence over LLM_* env vars."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-env-key")
    monkeypatch.setenv("LLM_API_KEY", "llm-env-key")

    config = reload_module("config")

    assert config.DEEPSEEK_API_KEY == "ds-env-key"


# ----------------------------------------------------------------
# validate_config() tests
# ----------------------------------------------------------------


def test_validate_config_all_good(monkeypatch, tmp_path):
    """No warnings when config is properly set."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-real-key-123")
    monkeypatch.setenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")

    config = reload_module("config")
    warnings = config.validate_config()

    assert warnings == []


def test_validate_config_empty_key(monkeypatch, tmp_path):
    """Warning when API key is empty."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    config = reload_module("config")
    warnings = config.validate_config()

    assert len(warnings) >= 1
    assert any("API key" in w for w in warnings)


def test_validate_config_placeholder_key(monkeypatch, tmp_path):
    """Warning when API key is still the placeholder value."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "your-deepseek-api-key")

    config = reload_module("config")
    warnings = config.validate_config()

    assert any(u"占位符" in w for w in warnings)


def test_validate_config_bad_url(monkeypatch, tmp_path):
    """Warning when API URL does not start with http:// or https://."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-real-key")
    monkeypatch.setenv("DEEPSEEK_API_URL", "ftp://bad-url.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")

    config = reload_module("config")
    warnings = config.validate_config()

    assert len(warnings) == 1
    assert "URL" in warnings[0]


def test_validate_config_empty_model(monkeypatch, tmp_path):
    """Warning when model name is empty.

    Note: _read_config treats empty env var as unset and falls back to default.
    To get a truly empty model, we monkeypatch the module attribute directly.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-real-key")

    config = reload_module("config")
    monkeypatch.setattr(config, "DEEPSEEK_MODEL", "")
    warnings = config.validate_config()

    assert any(u"模型" in w for w in warnings)


def test_validate_config_multiple_issues(monkeypatch, tmp_path):
    """Multiple warnings when several things are wrong."""
    monkeypatch.setenv("HOME", str(tmp_path))
    _clear_all_llm_env(monkeypatch)

    monkeypatch.setenv("DEEPSEEK_API_URL", "not-a-url")

    config = reload_module("config")
    monkeypatch.setattr(config, "DEEPSEEK_MODEL", "")
    warnings = config.validate_config()

    # Should have warnings for: empty key, bad URL, empty model
    assert len(warnings) == 3
