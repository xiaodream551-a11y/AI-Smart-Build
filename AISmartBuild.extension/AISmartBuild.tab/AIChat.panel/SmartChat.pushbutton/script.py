#! python3
# -*- coding: utf-8 -*-
"""AI chat-based intelligent modeling."""

__doc__ = "用中文对话控制 Revit 建模 — 输入指令，AI 自动执行"
__title__ = "智能\n对话"
__author__ = "AI智建"

from pyrevit import forms, revit, script

from config import DEEPSEEK_API_KEY, USER_CONFIG_PATH
from ai.chat_common import get_all_levels
from ai.chat_controller import build_chat_state, handle_local_command, run_ai_turn
from ai.client import DeepSeekClient
from engine.logger import ConversationLog, OperationLog, export_conversation_log, export_operation_log


def main():
    doc = revit.doc
    output = script.get_output()
    operation_log = OperationLog()
    conversation_log = ConversationLog()

    if not DEEPSEEK_API_KEY:
        forms.alert(
            "请先配置 DeepSeek API Key\n\n"
            "可用方式：\n"
            "1. 环境变量 DEEPSEEK_API_KEY 或 AI_SMART_BUILD_DEEPSEEK_API_KEY\n"
            "2. 用户配置文件：{}\n\n"
            "申请地址: https://platform.deepseek.com".format(USER_CONFIG_PATH),
            title="AI 智建 — 配置缺失"
        )
        script.exit()

    output.print_md("## AI 智建 — 智能对话建模")
    output.print_md("输入中文建模指令，如：")
    output.print_md('- "在坐标(6000,0)处创建一根500x500的柱子"')
    output.print_md('- "生成一个3跨x2跨、5层的框架"')
    output.print_md('- "查询模型中有多少根柱子"')
    output.print_md('- "输入 /help 查看更多示例，输入 /reset /retry /replay /replaylog /replayfail 使用快捷命令"')
    output.print_md("---")

    client = DeepSeekClient()
    levels = get_all_levels(doc)
    chat_state = build_chat_state()

    while True:
        user_input = forms.ask_for_string(
            prompt="请输入建模指令（输入 q 退出）：",
            title="AI 智建 — 对话"
        )

        if not user_input or user_input.strip().lower() == "q":
            break

        handled, levels = handle_local_command(
            user_input,
            output,
            client,
            doc=doc,
            levels=levels,
            operation_log=operation_log,
            conversation_log=conversation_log,
            chat_state=chat_state,
        )
        if handled:
            continue

        levels = run_ai_turn(
            doc,
            output,
            client,
            levels,
            user_input,
            operation_log,
            conversation_log,
            chat_state,
        )

    output.print_md("对话结束。")
    conversation_path = export_conversation_log(conversation_log, u"AI对话会话")
    if operation_log.logs:
        log_path = export_operation_log(operation_log, u"AI对话")
        output.print_md("### " + operation_log.get_summary())
        if log_path:
            output.print_md("- 日志已导出：`{}`".format(log_path))
    if conversation_path:
        output.print_md("- 会话记录已导出：`{}`".format(conversation_path))


if __name__ == "__main__":
    main()
