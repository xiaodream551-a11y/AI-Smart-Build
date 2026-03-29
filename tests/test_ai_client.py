# -*- coding: utf-8 -*-

import json

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
