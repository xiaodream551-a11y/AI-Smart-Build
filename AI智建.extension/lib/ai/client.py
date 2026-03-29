# -*- coding: utf-8 -*-
"""DeepSeek API 客户端 — 适配 pyRevit IronPython 环境"""

import json

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
    API_TIMEOUT_MS,
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
)
from ai.prompt import SYSTEM_PROMPT


def call_deepseek(messages, api_key=None, model=None, api_url=None, timeout_ms=None):
    """直接调用 DeepSeek 聊天接口并返回原始响应文本。"""
    client = DeepSeekClient(
        api_key=api_key,
        model=model,
        api_url=api_url,
    )
    payload = client._build_payload(messages)
    return client._http_post(payload, timeout_ms=timeout_ms)


class DeepSeekClient(object):
    """DeepSeek API 客户端"""

    def __init__(self, api_key=None, model=None, api_url=None):
        self.api_url = api_url or DEEPSEEK_API_URL
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def chat(self, user_message, timeout_ms=None):
        """
        发送消息并获取回复。
        Args:
            user_message: 用户输入的中文文本
            timeout_ms: 可选请求超时，单位毫秒；为空时使用全局默认值
        Returns:
            大模型回复的文本（应为 JSON 字符串）
        """
        self.conversation.append({"role": "user", "content": user_message})

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
        except Exception:
            self._rollback_last_user_message(user_message)
            raise

    def reset(self):
        """重置对话历史。"""
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
        """通过 .NET HttpWebRequest 发送 POST 请求。"""
        if HttpWebRequest is None or Encoding is None:
            raise RuntimeError("当前环境不支持 .NET HTTP 请求")

        request = HttpWebRequest.Create(self.api_url)
        request.Method = "POST"
        request.ContentType = "application/json"
        request.Headers.Add("Authorization", "Bearer " + self.api_key)
        request.Timeout = self._normalize_timeout_ms(timeout_ms)

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
