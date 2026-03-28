# -*- coding: utf-8 -*-
"""DeepSeek API 客户端 — 适配 pyRevit IronPython 环境"""

import json

# IronPython 环境使用 .NET HTTP 类
import clr
clr.AddReference("System")
clr.AddReference("System.Net")

from System.Net import HttpWebRequest, WebException
from System.IO import StreamReader
from System.Text import Encoding

from config import DEEPSEEK_API_URL, DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from ai.prompt import SYSTEM_PROMPT


class DeepSeekClient(object):
    """DeepSeek API 客户端"""

    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def chat(self, user_message):
        """
        发送消息并获取回复
        Args:
            user_message: 用户输入的中文文本
        Returns:
            大模型回复的文本（应为 JSON 字符串）
        """
        self.conversation.append({"role": "user", "content": user_message})

        payload = json.dumps({
            "model": self.model,
            "messages": self.conversation,
            "temperature": 0.1,  # 低温度保证输出稳定
        })

        try:
            response_text = self._http_post(payload)
            result = json.loads(response_text)
            reply = result["choices"][0]["message"]["content"]

            # 保存到对话历史
            self.conversation.append({"role": "assistant", "content": reply})
            return reply

        except WebException as e:
            raise Exception("API 请求失败: {}".format(str(e)))
        except (KeyError, IndexError):
            raise Exception("API 返回格式异常")

    def reset(self):
        """重置对话历史"""
        self.conversation = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def _http_post(self, payload):
        """通过 .NET HttpWebRequest 发送 POST 请求"""
        request = HttpWebRequest.Create(DEEPSEEK_API_URL)
        request.Method = "POST"
        request.ContentType = "application/json"
        request.Headers.Add("Authorization", "Bearer " + self.api_key)
        request.Timeout = 30000  # 30 秒超时

        # 写入请求体
        data = Encoding.UTF8.GetBytes(payload)
        request.ContentLength = data.Length
        stream = request.GetRequestStream()
        stream.Write(data, 0, data.Length)
        stream.Close()

        # 读取响应
        response = request.GetResponse()
        reader = StreamReader(response.GetResponseStream(), Encoding.UTF8)
        result = reader.ReadToEnd()
        reader.Close()
        response.Close()

        return result
