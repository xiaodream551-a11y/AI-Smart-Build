# -*- coding: utf-8 -*-

import json
import types

import pytest

import ai.client as client_module
from ai.client import DeepSeekClient, call_deepseek


def test_chat_rolls_back_user_message_on_invalid_json(monkeypatch):
    client = DeepSeekClient(api_key="test-key")

    monkeypatch.setattr(client, "_http_post", lambda payload: "not-json")

    try:
        client.chat("你好")
        raise AssertionError("预期应抛出异常")
    except Exception as err:
        assert "合法 JSON" in str(err)

    assert len(client.conversation) == 1
    assert client.conversation[0]["role"] == "system"


def test_chat_rolls_back_user_message_on_error_payload(monkeypatch):
    client = DeepSeekClient(api_key="test-key")

    monkeypatch.setattr(
        client,
        "_http_post",
        lambda payload: json.dumps({"error": {"message": "bad key"}})
    )

    try:
        client.chat("查询模型")
        raise AssertionError("预期应抛出异常")
    except Exception as err:
        assert "bad key" in str(err)

    assert len(client.conversation) == 1
    assert client.conversation[0]["role"] == "system"


def test_chat_appends_assistant_message_on_success(monkeypatch):
    client = DeepSeekClient(api_key="test-key")

    monkeypatch.setattr(
        client,
        "_http_post",
        lambda payload: json.dumps({
            "choices": [
                {"message": {"content": "{\"action\":\"query_count\",\"params\":{\"element_type\":\"column\"}}"}}
            ]
        })
    )

    reply = client.chat("有多少柱子")

    assert "\"query_count\"" in reply
    assert [item["role"] for item in client.conversation] == [
        "system",
        "user",
        "assistant",
    ]


def test_extract_web_exception_message_with_response_text():
    client = DeepSeekClient(api_key="test-key")

    class FakeWebException(Exception):
        def __init__(self):
            self.response_text = json.dumps({
                "error": {"message": "rate limit"}
            })

        def __str__(self):
            return "429 Too Many Requests"

    message = client._extract_web_exception_message(FakeWebException())

    assert "429 Too Many Requests" in message
    assert "rate limit" in message


def test_chat_passes_custom_timeout(monkeypatch):
    client = DeepSeekClient(api_key="test-key")
    records = {}

    def fake_http_post(payload, timeout_ms=None):
        records["timeout_ms"] = timeout_ms
        return json.dumps({
            "choices": [
                {"message": {"content": "{\"action\":\"query_count\",\"params\":{\"element_type\":\"column\"}}"}}
            ]
        })

    monkeypatch.setattr(client, "_http_post", fake_http_post)

    client.chat("统计柱子", timeout_ms=45678)

    assert records["timeout_ms"] == 45678


def test_call_deepseek_uses_timeout(monkeypatch):
    records = {}

    def fake_http_post(self, payload, timeout_ms=None):
        records["timeout_ms"] = timeout_ms
        return "ok"

    monkeypatch.setattr(DeepSeekClient, "_http_post", fake_http_post)

    result = call_deepseek(
        [{"role": "user", "content": "你好"}],
        api_key="test-key",
        timeout_ms=34567,
    )

    assert result == "ok"
    assert records["timeout_ms"] == 34567


def test_http_post_retries_on_server_error(monkeypatch):
    client = DeepSeekClient(api_key="test-key")
    attempts = {"count": 0}
    wait_calls = []

    class FakeWebException(client_module.WebException):
        def __init__(self, status_code):
            super(FakeWebException, self).__init__("{}".format(status_code))
            self.response = types.SimpleNamespace(status_code=status_code)

    def fake_http_post_once(payload, timeout_ms):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise FakeWebException(500)
        return "ok"

    monkeypatch.setattr(client_module, "HttpWebRequest", object())
    monkeypatch.setattr(client_module, "Encoding", object())
    monkeypatch.setattr(client_module, "API_RETRY_COUNT", 2)
    monkeypatch.setattr(client, "_http_post_once", fake_http_post_once)
    monkeypatch.setattr(client, "_wait_before_retry", lambda retry_number: wait_calls.append(retry_number))

    result = client._http_post("{}", timeout_ms=1200)

    assert result == "ok"
    assert attempts["count"] == 3
    assert wait_calls == [1, 2]


def test_http_post_does_not_retry_on_client_error(monkeypatch):
    client = DeepSeekClient(api_key="test-key")
    attempts = {"count": 0}
    wait_calls = []

    class FakeWebException(client_module.WebException):
        def __init__(self, status_code):
            super(FakeWebException, self).__init__("{}".format(status_code))
            self.response = types.SimpleNamespace(status_code=status_code)

    def fake_http_post_once(payload, timeout_ms):
        attempts["count"] += 1
        raise FakeWebException(400)

    monkeypatch.setattr(client_module, "HttpWebRequest", object())
    monkeypatch.setattr(client_module, "Encoding", object())
    monkeypatch.setattr(client_module, "API_RETRY_COUNT", 2)
    monkeypatch.setattr(client, "_http_post_once", fake_http_post_once)
    monkeypatch.setattr(client, "_wait_before_retry", lambda retry_number: wait_calls.append(retry_number))

    with pytest.raises(FakeWebException):
        client._http_post("{}", timeout_ms=1200)

    assert attempts["count"] == 1
    assert wait_calls == []


def test_http_post_retries_on_network_error(monkeypatch):
    client = DeepSeekClient(api_key="test-key")
    attempts = {"count": 0}
    wait_calls = []

    def fake_http_post_once(payload, timeout_ms):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise OSError("connection timed out")
        return "ok"

    monkeypatch.setattr(client_module, "HttpWebRequest", object())
    monkeypatch.setattr(client_module, "Encoding", object())
    monkeypatch.setattr(client_module, "API_RETRY_COUNT", 2)
    monkeypatch.setattr(client, "_http_post_once", fake_http_post_once)
    monkeypatch.setattr(client, "_wait_before_retry", lambda retry_number: wait_calls.append(retry_number))

    result = client._http_post("{}", timeout_ms=1200)

    assert result == "ok"
    assert attempts["count"] == 2
    assert wait_calls == [1]


def test_wait_before_retry_prints_and_sleeps(monkeypatch, capsys):
    client = DeepSeekClient(api_key="test-key")
    sleep_calls = []

    monkeypatch.setattr(client_module, "API_RETRY_BACKOFF", 2.0)
    monkeypatch.setattr(client_module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    client._wait_before_retry(2)

    captured = capsys.readouterr()
    assert "正在重试第 2 次..." in captured.out
    assert sleep_calls == [4.0]


def test_chat_trims_conversation_history_when_exceeding_limit(monkeypatch):
    monkeypatch.setattr(client_module, "MAX_CONVERSATION_TURNS", 2)
    client = DeepSeekClient(api_key="test-key")
    replies = {"count": 0}

    def fake_http_post(payload, timeout_ms=None):
        replies["count"] += 1
        return json.dumps({
            "choices": [
                {"message": {"content": "{\"action\":\"query_count\",\"params\":{\"element_type\":\"column\"}}"}}
            ]
        })

    monkeypatch.setattr(client, "_http_post", fake_http_post)

    for index in range(5):
        client.chat("消息{}".format(index + 1))

    assert replies["count"] == 5
    assert client.conversation[0]["role"] == "system"
    assert client.conversation[0]["content"] == client_module.SYSTEM_PROMPT
    assert len(client.conversation) == 5
    assert [item["content"] for item in client.conversation[1:]] == [
        "消息4",
        "{\"action\":\"query_count\",\"params\":{\"element_type\":\"column\"}}",
        "消息5",
        "{\"action\":\"query_count\",\"params\":{\"element_type\":\"column\"}}",
    ]


def test_chat_keeps_system_prompt_first_after_trim(monkeypatch):
    monkeypatch.setattr(client_module, "MAX_CONVERSATION_TURNS", 1)
    client = DeepSeekClient(api_key="test-key")

    monkeypatch.setattr(
        client,
        "_http_post",
        lambda payload, timeout_ms=None: json.dumps({
            "choices": [
                {"message": {"content": "{\"action\":\"query_count\",\"params\":{\"element_type\":\"beam\"}}"}}
            ]
        })
    )

    client.chat("第一轮")
    client.chat("第二轮")
    client.chat("第三轮")

    assert client.conversation[0]["role"] == "system"
    assert client.conversation[1]["role"] == "user"
    assert client.conversation[1]["content"] == "第三轮"


def test_build_payload_includes_response_format():
    client = DeepSeekClient(api_key="test-key")
    messages = [{"role": "user", "content": "hello"}]
    payload = json.loads(client._build_payload(messages))

    assert "response_format" in payload
    assert payload["response_format"] == {"type": "json_object"}


def test_chat_does_not_trim_when_not_exceeding_limit(monkeypatch):
    monkeypatch.setattr(client_module, "MAX_CONVERSATION_TURNS", 3)
    client = DeepSeekClient(api_key="test-key")

    monkeypatch.setattr(
        client,
        "_http_post",
        lambda payload, timeout_ms=None: json.dumps({
            "choices": [
                {"message": {"content": "{\"action\":\"query_count\",\"params\":{\"element_type\":\"slab\"}}"}}
            ]
        })
    )

    client.chat("一次")
    client.chat("两次")

    assert len(client.conversation) == 5
    assert [item["role"] for item in client.conversation] == [
        "system",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
