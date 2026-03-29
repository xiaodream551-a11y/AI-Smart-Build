# -*- coding: utf-8 -*-
"""AI 对话错误恢复与提示。"""

from ai.chat_common import TRANSACTIONAL_ACTIONS


ACTION_REQUIRED_PARAMS = {
    "create_column": [
        ("x", u"坐标 X"),
        ("y", u"坐标 Y"),
        ("base_floor", u"起始边界楼层"),
        ("top_floor", u"结束边界楼层"),
        ("section", u"柱截面"),
    ],
    "create_beam": [
        ("start_x", u"起点 X"),
        ("start_y", u"起点 Y"),
        ("end_x", u"终点 X"),
        ("end_y", u"终点 Y"),
        ("floor", u"故事层编号"),
        ("section", u"梁截面"),
    ],
    "create_slab": [
        ("boundary", u"楼板边界"),
        ("floor", u"故事层编号"),
    ],
    "generate_frame": [
        ("x_spans", u"X 向跨距"),
        ("y_spans", u"Y 向跨距"),
        ("num_floors", u"楼层数"),
        ("floor_height", u"标准层层高"),
    ],
    "modify_section": [
        ("element_type", u"构件类别"),
        ("floor", u"故事层编号"),
        ("old_section", u"旧截面"),
        ("new_section", u"新截面"),
    ],
    "delete_element": [
        ("element_type", u"构件类别"),
    ],
    "query_count": [
        ("element_type", u"构件类别"),
    ],
}

ACTION_LABELS = {
    "create_column": u"创建柱",
    "create_beam": u"创建梁",
    "create_slab": u"创建楼板",
    "generate_frame": u"生成框架",
    "modify_section": u"修改截面",
    "delete_element": u"删除构件",
    "query_count": u"查询数量",
    "unknown": u"未知动作",
}

EXECUTION_FAILURE_PREFIXES = (
    u"标高不足",
    u"柱的楼层范围无效",
    u"楼层超出范围",
    u"楼层参数无效",
    u"楼板边界点不足",
    u"缺少",
    u"不支持的操作类型",
    u"不支持查询的构件类型",
    u"不支持的构件类别",
    u"未提供可修改内容",
    u"未找到",
    u"未成功",
    u"批量修改失败",
    u"批量删除失败",
    u"修改失败",
    u"删除失败",
    u"无法理解",
)


def format_action_label(action):
    text = (action or "").strip() or "unknown"
    label = ACTION_LABELS.get(text)
    if not label:
        return text
    return u"{}({})".format(label, text)


def normalize_status_label(label):
    text = (label or "").strip()
    if text == u"失败":
        return "failed"
    if text == u"成功":
        return "success"
    return ""


def format_status_label(status):
    if status == "failed":
        return u"失败"
    if status == "success":
        return u"成功"
    return u"未知"


def summarize_error_text(error_text):
    text = (error_text or "").strip()
    if not text:
        return ""
    return text.splitlines()[0].strip()


def summarize_recovery_text(recovery_text):
    text = (recovery_text or "").strip()
    if not text:
        return ""
    return text.splitlines()[0].strip()


def format_user_error(err):
    message = "{}".format(err or "").strip()

    if not message:
        return u"发生未知错误，请重试。"

    if message.startswith("API 请求失败"):
        return u"AI 服务请求失败：{}\n建议检查网络连接、API Key 或稍后重试；也可以使用 /retry 重试上一条输入。".format(message)

    if message.startswith("API 返回错误"):
        return u"AI 服务返回错误：{}\n建议检查 API Key、模型名和接口配置；必要时使用 /retry 重试。".format(message)

    if message in ("API 返回格式异常", "API 返回不是合法 JSON"):
        return u"AI 服务返回内容异常：{}\n建议重试一次；如果持续出现，请检查模型输出或接口兼容性，并可使用 /retry 重试。".format(message)

    if message.startswith("无法从回复中提取 JSON 指令"):
        return u"AI 回复无法解析为建模指令。\n建议换更明确的说法后重试，例如直接说明构件类型、楼层和尺寸；如果只是想重复执行上一条成功指令，可用 /replay。"

    if message.startswith("不支持的操作类型") or message.startswith("不支持查询的构件类型"):
        return u"AI 生成了当前版本暂不支持的指令：{}\n建议重试，或把需求改写得更直接；也可以使用 /replaylog 或 /replayfail 回放历史可执行指令。".format(message)

    return u"执行失败：{}".format(message)


def is_execution_failure_result(result):
    text = (result or "").strip()
    if not text:
        return False
    for prefix in EXECUTION_FAILURE_PREFIXES:
        if text.startswith(prefix):
            return True
    return False


def build_recovery_suggestion(error_text, action="", user_input="", command=None):
    text = (error_text or "").strip()
    if not text:
        return u"请检查输入后重试。"

    if text.startswith(u"AI 服务请求失败："):
        return u"先检查网络连接和 API Key，再用 /retry 重试；如果只是验证执行链路，可改用 /replay 或 /replayfail。"

    if text.startswith(u"AI 服务返回错误："):
        return u"先检查模型名、接口地址和账号配额；确认配置后用 /retry 重试。"

    if text.startswith(u"AI 服务返回内容异常："):
        return u"建议先 /retry 一次；如果连续失败，保留会话 Markdown/JSON 并检查模型返回是否符合 JSON 指令格式。"

    if text.startswith(u"AI 回复无法解析为建模指令。"):
        return u"把需求拆成更直接的一句话，明确构件类型、楼层和尺寸，例如“在第2层创建一根300x600梁”，然后再试。"

    if text.startswith(u"AI 生成了当前版本暂不支持的指令："):
        return u"先把需求改写成当前已支持的创建、查询、修改或删除动作；也可以用 /replaylog 或 /replayfail 回放历史可执行指令。"

    missing_labels = find_missing_required_params(action, command)
    if text.startswith(u"缺少") and missing_labels:
        return u"当前指令还缺少：{}。请把这些字段补全后重试；如果是自然语言输入，建议直接把构件类型、楼层和尺寸一次说全，修正后也可用 /replayfail 复现。".format(
            u"、".join(missing_labels)
        )

    if text.startswith(u"楼板边界点不足"):
        return u"楼板边界至少要提供 3 个点，且按顺序围合成闭合区域；可以直接描述成“在第2层创建 6000x6000 楼板”。"

    if text.startswith(u"楼层参数无效") or text.startswith(u"楼层超出范围"):
        return _build_floor_recovery_suggestion(action)

    if text.startswith(u"柱的楼层范围无效"):
        return u"柱的 `base_floor/top_floor` 用边界编号，不是故事层号；例如首层柱应写成 `1 -> 2`，二层柱应写成 `2 -> 3`。"

    if text.startswith(u"标高不足"):
        return u"当前模型标高不够，建议先生成框架或先创建标高后再试；如果只是验证解析链路，可以先做查询或回放历史指令。"

    if text.startswith(u"不支持查询的构件类型"):
        return u"查询当前只支持 `column`、`beam`、`slab`，中文可写成“柱”“梁”“板”；请改写后重试。"

    if text.startswith(u"不支持的操作类型") or text.startswith(u"不支持的构件类别"):
        return u"请把需求改写成当前已支持的柱、梁、板创建，框架生成，截面修改，构件删除或数量查询。"

    if text.startswith(u"未找到") and action in ("modify_section", "delete_element"):
        return u"当前筛选条件没有匹配到构件，建议检查楼层、构件类别和截面条件；必要时先用查询命令确认目标是否存在。"

    if action in TRANSACTIONAL_ACTIONS:
        action_hint = _build_action_param_hint(action, command)
        if action_hint:
            return action_hint
        return u"先核对楼层编号、坐标和截面参数是否完整；修正后可用 /replayfail 直接重放失败指令。"

    if (user_input or "").strip().startswith("/replay"):
        return u"这次失败来自历史指令回放，建议先检查当前模型状态是否仍满足原指令的执行前提。"

    return u"请检查输入参数和当前模型状态后重试；必要时用 /retry、/replay 或 /replayfail 复现问题。"


def _build_floor_recovery_suggestion(action):
    if action == "create_column":
        return u"柱的 `base_floor/top_floor` 使用边界编号：首层柱是 `1 -> 2`，二层柱是 `2 -> 3`；请先确认输入没有把故事层号直接当成 `top_floor`。"

    if action in ("create_beam", "create_slab", "modify_section", "delete_element", "query_count"):
        return u"`floor` 在梁、板、修改、删除、统计里都表示故事层编号，从 1 开始；请按当前模型实际楼层范围重试。"

    return u"请按当前模型实际楼层范围重试，并确认柱使用边界编号，其它按楼层筛选的动作使用故事层编号。"


def _build_action_param_hint(action, command):
    params = (command or {}).get("params") or {}
    missing_labels = find_missing_required_params(action, command)
    if missing_labels:
        return u"当前指令缺少：{}。请补全这些参数后再试；修正后可用 /replayfail 直接复现。".format(
            u"、".join(missing_labels)
        )

    if action == "create_column":
        return u"请核对柱的坐标、截面，以及 `base_floor/top_floor` 是否按边界编号填写；修正后可用 /replayfail 直接重放。"

    if action == "create_beam":
        return u"请核对梁的起终点坐标、故事层编号和截面；如果梁端点方向写反也可以直接改成“从 A 到 B 创建梁”。"

    if action == "create_slab":
        boundary = params.get("boundary") or []
        if boundary:
            return u"请核对楼板边界点顺序是否围合、点数是否不少于 3 个，以及故事层编号是否有效。"
        return u"请补充楼板边界和故事层编号；边界建议直接给 3 个以上按顺序围合的点。"

    if action == "generate_frame":
        return u"请核对跨数、楼层数和层高参数；例如可以直接说“生成 3 跨 x 2 跨、5 层框架，层高 3600”。"

    if action == "modify_section":
        return u"请核对构件类别、故事层编号、旧截面和新截面；建议先用查询确认目标楼层确实存在该截面。"

    if action == "delete_element":
        return u"请核对构件类别和楼层筛选条件；如果想删某层全部梁/柱/板，直接明确“删除第 N 层梁/柱/板”。"

    return ""


def find_missing_required_params(action, command):
    params = (command or {}).get("params") or {}
    missing = []
    for key, label in ACTION_REQUIRED_PARAMS.get(action, []):
        value = params.get(key)
        if value in (None, "", []):
            missing.append(label)
            continue
        if key == "boundary" and (not isinstance(value, (list, tuple)) or len(value) < 3):
            missing.append(label)
    return missing


def log_failed_turn(
    output,
    conversation_log,
    user_input,
    error_text,
    command=None,
    reply=None,
    action="",
    request_duration_ms=None,
    source_kind="user",
    failed_filter=None,
    failed_selected_round_index=None
):
    recovery_suggestion = build_recovery_suggestion(
        error_text,
        action=action,
        user_input=user_input,
        command=command,
    )
    conversation_log.log_turn(
        user_input,
        reply=reply,
        command=command,
        error=error_text,
        recovery_suggestion=recovery_suggestion,
        action=action,
        request_duration_ms=request_duration_ms,
        source_kind=source_kind,
        failed_filter=failed_filter,
        failed_selected_round_index=failed_selected_round_index,
    )
    output.print_md("**错误：** {}".format(error_text))
    if recovery_suggestion:
        output.print_md("**建议：** {}".format(recovery_suggestion))
    output.print_md("---")
