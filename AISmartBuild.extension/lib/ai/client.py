# -*- coding: utf-8 -*-
"""DeepSeek API client -- compatible with the pyRevit IronPython environment."""

import json
import re
import time

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)

try:
    import clr
    clr.AddReference("System")
    clr.AddReference("System.Net")

    from System.Net import HttpWebRequest, WebException
    from System.IO import StreamReader
    from System.Text import Encoding
except ImportError:
    clr = None
    HttpWebRequest = None
    StreamReader = None
    Encoding = None

    class WebException(Exception):
        pass

from config import (
    API_RETRY_BACKOFF,
    API_RETRY_COUNT,
    API_TIMEOUT_MS,
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    MAX_CONVERSATION_TURNS as CONFIG_MAX_CONVERSATION_TURNS,
)
from ai.prompt import SYSTEM_PROMPT


MAX_CONVERSATION_TURNS = CONFIG_MAX_CONVERSATION_TURNS


def call_deepseek(messages, api_key=None, model=None, api_url=None, timeout_ms=None):
    """Call the DeepSeek chat API directly and return the raw response text."""
    client = DeepSeekClient(
        api_key=api_key,
        model=model,
        api_url=api_url,
    )
    payload = client._build_payload(messages)
    return client._http_post(payload, timeout_ms=timeout_ms)


class DeepSeekClient(object):
    """DeepSeek API client."""

    MAX_CONVERSATION_TURNS = MAX_CONVERSATION_TURNS

    def __init__(self, api_key=None, model=None, api_url=None):
        self.api_url = api_url or DEEPSEEK_API_URL
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.max_conversation_turns = self._normalize_max_conversation_turns(
            MAX_CONVERSATION_TURNS
        )
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def chat(self, user_message, timeout_ms=None):
        """
        Send a message and receive a reply.

        Args:
            user_message: User input text (Chinese natural language).
            timeout_ms: Optional request timeout in milliseconds; uses the
                global default when not provided.

        Returns:
            The LLM reply text (expected to be a JSON string).
        """
        self.conversation.append({"role": "user", "content": user_message})
        self._trim_conversation_history(preserve_pending_user=True)

        try:
            payload = self._build_payload(self.conversation)
            if timeout_ms in (None, ""):
                response_text = self._http_post(payload)
            else:
                response_text = self._http_post(payload, timeout_ms=timeout_ms)
            result = json.loads(response_text)
            error_message = self._extract_error_message(result)
            if error_message:
                raise Exception(error_message)
            reply = result["choices"][0]["message"]["content"]

            self.conversation.append({"role": "assistant", "content": reply})
            self._trim_conversation_history()
            return reply

        except WebException as err:
            self._rollback_last_user_message(user_message)
            raise Exception("API 请求失败: {}".format(
                self._extract_web_exception_message(err)
            ))
        except ValueError:
            self._rollback_last_user_message(user_message)
            raise Exception("API 返回不是合法 JSON")
        except (KeyError, IndexError):
            self._rollback_last_user_message(user_message)
            raise Exception("API 返回格式异常")
        except Exception as err:
            if self._is_request_exception(err):
                self._rollback_last_user_message(user_message)
                raise Exception("API 请求失败: {}".format(
                    self._extract_web_exception_message(err)
                ))
            self._rollback_last_user_message(user_message)
            raise

    def reset(self):
        """Reset the conversation history."""
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def _build_payload(self, messages):
        return json.dumps({
            "model": self.model,
            "messages": list(messages or []),
            "temperature": 0.1,
        })

    def _http_post(self, payload, timeout_ms=None):
        """Send a POST request via .NET HttpWebRequest with automatic retry on retryable errors."""
        if HttpWebRequest is None or Encoding is None:
            raise RuntimeError("当前环境不支持 .NET HTTP 请求")

        normalized_retry_count = self._normalize_retry_count(API_RETRY_COUNT)
        normalized_timeout_ms = self._normalize_timeout_ms(timeout_ms)

        for retry_index in range(normalized_retry_count + 1):
            try:
                return self._http_post_once(payload, normalized_timeout_ms)
            except Exception as err:
                if retry_index >= normalized_retry_count:
                    raise
                if not self._should_retry_request_error(err):
                    raise

                self._wait_before_retry(retry_index + 1)

    def _http_post_once(self, payload, timeout_ms):
        """Execute a single HTTP POST request."""
        request = HttpWebRequest.Create(self.api_url)
        request.Method = "POST"
        request.ContentType = "application/json"
        request.Headers.Add("Authorization", "Bearer " + self.api_key)
        request.Timeout = timeout_ms

        data = Encoding.UTF8.GetBytes(payload)
        request.ContentLength = data.Length
        stream = request.GetRequestStream()
        stream.Write(data, 0, data.Length)
        stream.Close()

        response = request.GetResponse()
        reader = StreamReader(response.GetResponseStream(), Encoding.UTF8)
        result = reader.ReadToEnd()
        reader.Close()
        response.Close()

        return result

    def _normalize_retry_count(self, retry_count):
        try:
            normalized = int(retry_count)
        except (TypeError, ValueError):
            return 0
        if normalized < 0:
            return 0
        return normalized

    def _normalize_max_conversation_turns(self, turn_count):
        try:
            normalized = int(turn_count)
        except (TypeError, ValueError):
            return 20
        if normalized <= 0:
            return 20
        return normalized

    def _normalize_retry_backoff(self, retry_backoff):
        try:
            normalized = float(retry_backoff)
        except (TypeError, ValueError):
            return 1.5
        if normalized <= 0:
            return 1.5
        return normalized

    def _wait_before_retry(self, retry_number):
        retry_backoff = self._normalize_retry_backoff(API_RETRY_BACKOFF)
        print("正在重试第 {} 次...".format(retry_number))
        time.sleep(retry_backoff ** retry_number)

    def _should_retry_request_error(self, error):
        status_code = self._extract_response_status_code(error)
        if status_code is not None:
            return 500 <= status_code < 600
        return self._looks_like_network_error(error)

    def _is_request_exception(self, error):
        return (
            isinstance(error, WebException) or
            self._extract_response_status_code(error) is not None or
            self._looks_like_network_error(error)
        )

    def _extract_response_status_code(self, error):
        candidates = [
            getattr(error, "Response", None),
            getattr(error, "response", None),
            error,
        ]
        for candidate in candidates:
            if candidate is None:
                continue

            for attr_name in ("StatusCode", "status_code", "status"):
                status_value = getattr(candidate, attr_name, None)
                if status_value in (None, ""):
                    continue

                normalized = self._coerce_status_code(status_value)
                if normalized is not None:
                    return normalized
        return None

    def _coerce_status_code(self, status_value):
        try:
            return int(status_value)
        except (TypeError, ValueError):
            pass

        raw_value = getattr(status_value, "value__", None)
        if raw_value is not None:
            try:
                return int(raw_value)
            except (TypeError, ValueError):
                pass

        match = re.search(r"(\d{3})", "{}".format(status_value))
        if not match:
            return None

        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None

    def _looks_like_network_error(self, error):
        if isinstance(error, (OSError, TimeoutError)):
            return True

        error_text = "{}".format(error or "").lower()
        status_text = "{}".format(
            getattr(error, "Status", getattr(error, "status", ""))
        ).lower()
        combined_text = "{} {}".format(error_text, status_text)

        network_keywords = (
            "timeout",
            "timed out",
            "dns",
            "name resolution",
            "name or service not known",
            "remote name could not be resolved",
            "no such host",
            "connection refused",
            "connection reset",
            "connection aborted",
            "network",
            "temporarily unavailable",
            "unreachable",
            "closed",
        )
        for keyword in network_keywords:
            if keyword in combined_text:
                return True
        return False

    def _normalize_timeout_ms(self, timeout_ms):
        if timeout_ms in (None, ""):
            return API_TIMEOUT_MS
        try:
            normalized = int(timeout_ms)
        except (TypeError, ValueError):
            return API_TIMEOUT_MS
        if normalized <= 0:
            return API_TIMEOUT_MS
        return normalized

    def _rollback_last_user_message(self, user_message):
        if not self.conversation:
            return

        last_message = self.conversation[-1]
        if last_message.get("role") != "user":
            return
        if last_message.get("content") != user_message:
            return

        self.conversation.pop()

    def _trim_conversation_history(self, preserve_pending_user=False):
        if len(self.conversation) <= 1:
            return

        system_message = self.conversation[0]
        history = list(self.conversation[1:])
        pending_user = []

        if preserve_pending_user and history and history[-1].get("role") == "user":
            pending_user = [history.pop()]

        max_history_messages = self.max_conversation_turns * 2
        if len(history) <= max_history_messages:
            self.conversation = [system_message] + history + pending_user
            return

        history = history[-max_history_messages:]
        if history and history[0].get("role") == "assistant":
            history = history[1:]

        self.conversation = [system_message] + history + pending_user

    def _extract_error_message(self, response_data):
        if not isinstance(response_data, dict):
            return None

        error = response_data.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return "API 返回错误: {}".format(message)
        return None

    def _extract_web_exception_message(self, error):
        detail = self._try_read_web_exception_response(error)
        if detail:
            return "{} | {}".format(error, detail)
        return "{}".format(error)

    def _try_read_web_exception_response(self, error):
        response = getattr(error, "Response", None)
        if not response:
            response = getattr(error, "response", None)
        if not response:
            response = getattr(error, "response_text", None)
            if response:
                return self._normalize_response_error_text(response)
            return None

        if isinstance(response, string_types):
            return self._normalize_response_error_text(response)

        stream_getter = getattr(response, "GetResponseStream", None)
        if not stream_getter or StreamReader is None or Encoding is None:
            return None

        reader = None
        try:
            reader = StreamReader(stream_getter(), Encoding.UTF8)
            return self._normalize_response_error_text(reader.ReadToEnd())
        except Exception:
            return None
        finally:
            if reader is not None:
                try:
                    reader.Close()
                except Exception:
                    pass
            try:
                response.Close()
            except Exception:
                pass

    def _normalize_response_error_text(self, text):
        content = "{}".format(text or "").strip()
        if not content:
            return None

        try:
            payload = json.loads(content)
        except Exception:
            return content

        message = self._extract_error_message(payload)
        if message:
            return message
        return content
