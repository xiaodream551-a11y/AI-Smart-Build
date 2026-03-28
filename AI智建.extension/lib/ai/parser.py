# -*- coding: utf-8 -*-
"""指令解析器 — 从大模型回复中提取 JSON 并分发到建模函数"""

import json
import re


def parse_command(reply_text):
    """
    从大模型回复中提取 JSON 指令
    Args:
        reply_text: 大模型原始回复文本
    Returns:
        dict: {"action": "...", "params": {...}}
    Raises:
        ValueError: 解析失败
    """
    text = reply_text.strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass

    # 尝试从 markdown 代码块中提取
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (ValueError, TypeError):
            pass

    # 尝试提取第一个 {...}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (ValueError, TypeError):
            pass

    raise ValueError("无法从回复中提取 JSON 指令：{}".format(
        text[:100] + "..." if len(text) > 100 else text
    ))


def dispatch_command(doc, command, levels=None):
    """
    根据 action 分发到对应的建模函数
    Args:
        doc: Revit Document
        command: parse_command 的返回值
        levels: 标高列表（按楼层索引），用于定位楼层
    Returns:
        str: 执行结果描述
    """
    action = command.get("action", "")
    params = command.get("params", {})

    if action == "create_column":
        return _exec_create_column(doc, params, levels)
    elif action == "create_beam":
        return _exec_create_beam(doc, params, levels)
    elif action == "create_slab":
        return _exec_create_slab(doc, params, levels)
    elif action == "generate_frame":
        return _exec_generate_frame(doc, params)
    elif action == "query_count":
        return _exec_query_count(doc, params)
    elif action == "modify_section":
        return _exec_modify_section(doc, params, levels)
    elif action == "delete_element":
        return _exec_delete_element(doc, params, levels)
    elif action == "unknown":
        return params.get("message", "无法理解你的指令，请换个说法试试")
    else:
        return "不支持的操作类型: {}".format(action)


# ============================================================
# 各 action 的执行函数
# ============================================================

def _exec_create_column(doc, params, levels):
    from engine.column import create_column
    x = params.get("x", 0)
    y = params.get("y", 0)
    section = params.get("section", "500x500")
    base_floor = params.get("base_floor", 1)
    top_floor = params.get("top_floor", base_floor + 1)

    if not levels or len(levels) < top_floor + 1:
        return "标高不足，请先生成框架或创建标高"

    base_level = levels[base_floor - 1]
    top_level = levels[top_floor - 1]
    create_column(doc, x, y, base_level, top_level, section)
    return "已在 ({},{}) 创建 {} 柱，{} 层到 {} 层".format(
        x, y, section, base_floor, top_floor
    )


def _exec_create_beam(doc, params, levels):
    from engine.beam import create_beam
    sx = params.get("start_x", 0)
    sy = params.get("start_y", 0)
    ex = params.get("end_x", 0)
    ey = params.get("end_y", 0)
    floor = params.get("floor", 1)
    section = params.get("section", "300x600")

    if not levels or len(levels) < floor + 1:
        return "标高不足"

    level = levels[floor]
    create_beam(doc, sx, sy, ex, ey, level, section)
    return "已创建 {} 梁，从 ({},{}) 到 ({},{})，第 {} 层".format(
        section, sx, sy, ex, ey, floor
    )


def _exec_create_slab(doc, params, levels):
    from engine.floor import create_floor
    boundary = params.get("boundary", [])
    floor = params.get("floor", 1)

    if not boundary or len(boundary) < 3:
        return "楼板边界点不足（至少 3 个点）"
    if not levels or len(levels) < floor + 1:
        return "标高不足"

    points = [(p[0], p[1]) for p in boundary]
    level = levels[floor]
    create_floor(doc, points, level)
    return "已在第 {} 层创建楼板".format(floor)


def _exec_generate_frame(doc, params):
    from engine.frame_generator import generate_frame, format_stats
    stats = generate_frame(doc, params)
    return format_stats(stats)


def _exec_modify_section(doc, params, levels):
    from engine.modify import batch_modify_by_filter

    category = params.get("element_type", "")
    floor = params.get("floor")
    old_section = params.get("old_section", "")
    new_section = params.get("new_section", "")

    if floor is None:
        return "缺少楼层参数"
    if not old_section:
        return "缺少旧截面参数"
    if not new_section:
        return "缺少新截面参数"
    if not levels:
        return "标高不足"

    try:
        floor_index = int(floor)
    except (ValueError, TypeError):
        return "楼层参数无效: {}".format(floor)

    if floor_index < 0 or floor_index >= len(levels):
        return "楼层超出范围: {}".format(floor)

    level = levels[floor_index]
    return batch_modify_by_filter(
        doc, category, level, old_section, new_section
    )


def _exec_delete_element(doc, params, levels):
    from engine.modify import batch_delete_by_filter

    category = params.get("element_type", "")
    floor = params.get("floor")

    if floor is None:
        return batch_delete_by_filter(doc, category, None)

    if not levels:
        return "标高不足"

    try:
        floor_index = int(floor)
    except (ValueError, TypeError):
        return "楼层参数无效: {}".format(floor)

    if floor_index < 0 or floor_index >= len(levels):
        return "楼层超出范围: {}".format(floor)

    level = levels[floor_index]
    return batch_delete_by_filter(doc, category, level)


def _exec_query_count(doc, params):
    from pyrevit import DB
    element_type = params.get("element_type", "")

    type_map = {
        "column": DB.BuiltInCategory.OST_StructuralColumns,
        "beam": DB.BuiltInCategory.OST_StructuralFraming,
        "slab": DB.BuiltInCategory.OST_Floors,
        "floor": DB.BuiltInCategory.OST_Floors,
    }

    cat = type_map.get(element_type)
    if not cat:
        return "不支持查询的构件类型: {}".format(element_type)

    collector = DB.FilteredElementCollector(doc) \
        .OfCategory(cat) \
        .WhereElementIsNotElementType()

    count = collector.GetElementCount()

    name_map = {"column": "柱", "beam": "梁", "slab": "板", "floor": "板"}
    return "当前模型中共有 {} 个{}构件".format(count, name_map.get(element_type, ""))
