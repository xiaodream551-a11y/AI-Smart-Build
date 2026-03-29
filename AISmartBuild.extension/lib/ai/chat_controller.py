# -*- coding: utf-8 -*-
"""AI 对话流程控制。"""

import time

from ai.chat_common import (
    execute_command,
    format_command_text,
    print_system_message,
    shorten_text,
    get_all_levels,
)
from ai.parser import parse_command, resolve_ai_timeout_ms
from ai.recovery import (
    format_user_error,
    is_execution_failure_result,
    log_failed_turn,
)
from ai.replay import (
    replay_last_command,
    replay_last_command_from_log,
    replay_pick_failed_command_from_log,
)


HELP_EXAMPLES = [
    u"在坐标(6000,0)处创建一根500x500的柱子",
    u"在第2层从0,0到6000,0创建一根300x600的梁",
    u"统计一下三层有多少块板",
]


def print_help(output):
    output.print_md("### 可用快捷命令")
    output.print_md("- 输入 `q` 退出对话")
    output.print_md("- 输入 `/reset` 重置当前对话上下文")
    output.print_md("- 输入 `/retry` 重试上一条自然语言输入")
    output.print_md("- 输入 `/replay` 直接重放上一条归一化指令")
    output.print_md("- 输入 `/replaylog` 从最近一次会话文件重放上一条归一化指令")
    output.print_md("- 输入 `/replayfail` 从最近一次会话文件筛选失败记录并重放，支持来源筛选、动作筛选和上一条/下一条导航")
    output.print_md("- 输入 `/help` 查看示例指令")
    output.print_md("### 示例")
    for example in HELP_EXAMPLES:
        output.print_md("- `{}`".format(example))
    output.print_md("---")


def build_chat_state():
    return {
        "last_user_input": None,
        "last_reply": None,
        "last_command": None,
        "last_result": None,
        "last_action": None,
        "last_failed_filter": None,
        "last_failed_selected_round_index": None,
    }


def reset_chat_state(chat_state):
    if not isinstance(chat_state, dict):
        return build_chat_state()

    chat_state["last_user_input"] = None
    chat_state["last_reply"] = None
    chat_state["last_command"] = None
    chat_state["last_result"] = None
    chat_state["last_action"] = None
    chat_state["last_failed_filter"] = None
    chat_state["last_failed_selected_round_index"] = None
    return chat_state


def split_command_text_and_args(user_input):
    text = (user_input or "").strip()
    if not text:
        return "", ""

    parts = text.split(None, 1)
    command_text = parts[0].lower()
    command_args = parts[1].strip() if len(parts) > 1 else ""
    return command_text, command_args


def handle_local_command(
    user_input,
    output,
    client,
    doc=None,
    levels=None,
    operation_log=None,
    conversation_log=None,
    chat_state=None
):
    text = (user_input or "").strip().lower()
    command_text, command_args = split_command_text_and_args(user_input)
    if text in ("/help", "help", "?"):
        print_help(output)
        return True, levels

    if text in ("/reset", "reset", "清空对话", "重置对话"):
        client.reset()
        reset_chat_state(chat_state)
        print_system_message(output, u"已重置对话上下文。")
        return True, levels

    if text in ("/retry", "retry", "重试上一条"):
        return True, retry_last_input(
            doc,
            output,
            client,
            levels,
            operation_log,
            conversation_log,
            chat_state,
        )

    if text in ("/replay", "replay", "重放上一条"):
        return True, replay_last_command(
            doc,
            output,
            levels,
            operation_log,
            conversation_log,
            chat_state,
        )

    if text in ("/replaylog", "replaylog", "重放最近会话"):
        return True, replay_last_command_from_log(
            doc,
            output,
            levels,
            operation_log,
            conversation_log,
            chat_state,
        )

    if command_text in ("/replayfail", "replayfail", "重放失败记录"):
        return True, replay_pick_failed_command_from_log(
            doc,
            output,
            levels,
            operation_log,
            conversation_log,
            chat_state,
            filter_keyword=command_args,
            replay_user_input="/replayfail",
        )

    return False, levels


def run_ai_turn(
    doc,
    output,
    client,
    levels,
    user_input,
    operation_log,
    conversation_log,
    chat_state,
    display_input=None,
    conversation_user_input=None
):
    display_text = display_input or user_input
    log_user_input = conversation_user_input or user_input

    output.print_md("**你：** " + display_text)
    reply = None
    command = None
    request_duration_ms = None
    chat_state["last_user_input"] = user_input

    try:
        started_at = time.time()
        timeout_ms = resolve_ai_timeout_ms(user_input)
        reply = client.chat(user_input, timeout_ms=timeout_ms)
        request_duration_ms = int(round((time.time() - started_at) * 1000))
        output.print_md("**AI 解析：** `{}`".format(
            shorten_text(reply)
        ))

        command = parse_command(reply)
        action = command.get("action", "unknown")
        output.print_md("```json\n{}\n```".format(format_command_text(command)))

        result, levels = execute_command(doc, command, levels)
        if is_execution_failure_result(result):
            log_failed_turn(
                output,
                conversation_log,
                log_user_input,
                result,
                command=command,
                reply=reply,
                action=action,
                request_duration_ms=request_duration_ms,
                source_kind=_infer_source_kind(log_user_input),
            )
            chat_state["last_reply"] = reply
            chat_state["last_command"] = command
            chat_state["last_action"] = action
            return levels

        operation_log.log(action, result)
        conversation_log.log_turn(
            log_user_input,
            reply=reply,
            command=command,
            result=result,
            action=action,
            request_duration_ms=request_duration_ms,
            source_kind=_infer_source_kind(log_user_input),
        )

        output.print_md("**执行结果：** " + result)
        output.print_md("---")

        chat_state["last_reply"] = reply
        chat_state["last_command"] = command
        chat_state["last_result"] = result
        chat_state["last_action"] = action
        return levels

    except Exception as err:
        error_text = format_user_error(err)
        action = (command or {}).get("action", "")
        log_failed_turn(
            output,
            conversation_log,
            log_user_input,
            error_text,
            command=command,
            reply=reply,
            action=action,
            request_duration_ms=request_duration_ms,
            source_kind=_infer_source_kind(log_user_input),
        )

        if reply is not None:
            chat_state["last_reply"] = reply
        if command is not None:
            chat_state["last_command"] = command
            chat_state["last_action"] = command.get("action", "")
        return levels


def retry_last_input(
    doc,
    output,
    client,
    levels,
    operation_log,
    conversation_log,
    chat_state
):
    last_user_input = (chat_state or {}).get("last_user_input")
    if not last_user_input:
        print_system_message(output, u"当前没有可重试的上一条输入。")
        return levels

    print_system_message(output, u"正在重试上一条自然语言输入。")
    return run_ai_turn(
        doc,
        output,
        client,
        levels,
        last_user_input,
        operation_log,
        conversation_log,
        chat_state,
        display_input=last_user_input,
        conversation_user_input="/retry -> " + last_user_input,
    )


def _infer_source_kind(user_input):
    text = (user_input or "").strip().lower()
    if text.startswith("/retry"):
        return "retry"
    if text.startswith("/replayfail"):
        return "replay_log"
    if text.startswith("/replaylog"):
        return "replay_log"
    if text.startswith("/replay"):
        return "replay"
    return "user"
