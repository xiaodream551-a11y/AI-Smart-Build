# -*- coding: utf-8 -*-
"""指令解析器 — 从大模型回复中提取 JSON 并分发到建模函数"""

import json
import re

from config import API_TIMEOUT_MS, FRAME_API_TIMEOUT_MS
from utils import (
    get_story_count,
    normalize_floor_number,
    resolve_story_level_by_category,
    resolve_floor_boundary_level,
    resolve_story_framing_level,
)


_ACTION_ALIASES = {
    "create_column": "create_column",
    "add_column": "create_column",
    "column_create": "create_column",
    "创建柱": "create_column",
    "创建柱子": "create_column",
    "create_beam": "create_beam",
    "add_beam": "create_beam",
    "beam_create": "create_beam",
    "创建梁": "create_beam",
    "create_slab": "create_slab",
    "create_floor": "create_slab",
    "add_slab": "create_slab",
    "add_floor": "create_slab",
    "创建板": "create_slab",
    "创建楼板": "create_slab",
    "modify_section": "modify_section",
    "modify_element": "modify_section",
    "update_section": "modify_section",
    "edit_section": "modify_section",
    "修改截面": "modify_section",
    "delete_element": "delete_element",
    "delete_elements": "delete_element",
    "remove_element": "delete_element",
    "remove_elements": "delete_element",
    "删除构件": "delete_element",
    "generate_frame": "generate_frame",
    "create_frame": "generate_frame",
    "build_frame": "generate_frame",
    "生成框架": "generate_frame",
    "query_count": "query_count",
    "count": "query_count",
    "count_element": "query_count",
    "count_elements": "query_count",
    "query_elements": "query_count",
    "统计数量": "query_count",
    "查询数量": "query_count",
    "unknown": "unknown",
}

_ELEMENT_TYPE_ALIASES = {
    "column": "column",
    "columns": "column",
    "col": "column",
    "柱": "column",
    "柱子": "column",
    "结构柱": "column",
    "beam": "beam",
    "beams": "beam",
    "girder": "beam",
    "梁": "beam",
    "梁构件": "beam",
    "结构梁": "beam",
    "slab": "slab",
    "slabs": "slab",
    "floor": "slab",
    "floors": "slab",
    "板": "slab",
    "楼板": "slab",
    "楼面": "slab",
}


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
        return normalize_command(json.loads(text))
    except (ValueError, TypeError):
        pass

    # 尝试从 markdown 代码块中提取
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return normalize_command(json.loads(match.group(1).strip()))
        except (ValueError, TypeError):
            pass

    # 尝试提取第一个 {...}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return normalize_command(json.loads(match.group(0)))
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
    normalized_command = normalize_command(command)
    if not isinstance(normalized_command, dict):
        raise ValueError("命令必须为 JSON 对象")
    action = normalized_command.get("action", "")
    params = normalized_command.get("params", {})

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


def normalize_command(command):
    """将模型输出的命令规范化为项目内部格式。"""
    if not isinstance(command, dict):
        raise ValueError("命令必须为 JSON 对象")

    action = _normalize_action(command.get("action", ""))
    params = command.get("params", {})
    if not isinstance(params, dict):
        params = {}
    else:
        params = dict(params)

    params = _normalize_common_params(params)
    params = _normalize_params_by_action(action, params)

    return {
        "action": action,
        "params": params,
    }


def resolve_ai_timeout_ms(user_input):
    """根据用户输入推断本轮 AI 请求超时配置。"""
    text = _to_text(user_input)
    if _looks_like_generate_frame_request(text):
        return FRAME_API_TIMEOUT_MS
    return API_TIMEOUT_MS


def _normalize_action(action):
    text = _to_text(action)
    if not text:
        return ""
    return _ACTION_ALIASES.get(text.lower(), _ACTION_ALIASES.get(text, text))


def _normalize_common_params(params):
    normalized = dict(params)

    element_type = _first_present(
        normalized,
        ["element_type", "type", "category", "target_type", "component_type"]
    )
    if element_type is not None:
        normalized["element_type"] = _normalize_element_type(element_type)

    return normalized


def _normalize_params_by_action(action, params):
    normalized = dict(params)

    if action == "create_column":
        base_floor = _first_present(
            normalized,
            ["base_floor", "start_floor", "from_floor", "floor", "level"]
        )
        top_floor = _first_present(
            normalized,
            ["top_floor", "end_floor", "to_floor", "upper_floor"]
        )
        if base_floor is not None:
            normalized["base_floor"] = base_floor
        if top_floor is not None:
            normalized["top_floor"] = top_floor
        elif base_floor is not None:
            base_floor_number = normalize_floor_number(base_floor)
            if base_floor_number is not None:
                normalized["top_floor"] = base_floor_number + 1
        return normalized

    if action in ("create_beam", "create_slab", "modify_section", "delete_element", "query_count"):
        floor = _first_present(normalized, ["floor", "level", "story"])
        if floor is not None:
            normalized["floor"] = floor

    if action == "create_slab" and "boundary" not in normalized:
        boundary = _first_present(
            normalized,
            ["points", "vertices", "polygon", "boundary_points"]
        )
        if boundary is not None:
            normalized["boundary"] = boundary

    if action == "modify_section":
        old_section = _first_present(
            normalized,
            ["old_section", "from_section", "source_section"]
        )
        new_section = _first_present(
            normalized,
            ["new_section", "to_section", "target_section"]
        )
        if old_section is not None:
            normalized["old_section"] = old_section
        if new_section is not None:
            normalized["new_section"] = new_section

    if action == "generate_frame":
        num_floors = _first_present(
            normalized,
            ["num_floors", "floors", "floor_count", "story_count", "stories"]
        )
        floor_height = _first_present(
            normalized,
            ["floor_height", "story_height", "height", "standard_floor_height"]
        )
        first_floor_height = _first_present(
            normalized,
            ["first_floor_height", "first_height", "ground_floor_height"]
        )
        beam_section = _first_present(
            normalized,
            ["beam_section", "beam_size", "beam_section_default"]
        )
        beam_section_x = _first_present(
            normalized,
            ["beam_section_x", "beam_x_section"]
        )
        beam_section_y = _first_present(
            normalized,
            ["beam_section_y", "beam_y_section"]
        )

        if num_floors is not None:
            normalized["num_floors"] = num_floors
        if floor_height is not None:
            normalized["floor_height"] = floor_height
        if first_floor_height is not None:
            normalized["first_floor_height"] = first_floor_height
        if beam_section_x is None and beam_section is not None:
            beam_section_x = beam_section
        if beam_section_y is None:
            beam_section_y = beam_section_x or beam_section
        if beam_section_x is not None:
            normalized["beam_section_x"] = beam_section_x
        if beam_section_y is not None:
            normalized["beam_section_y"] = beam_section_y

    return normalized


def _normalize_element_type(element_type):
    text = _to_text(element_type)
    if not text:
        return ""
    return _ELEMENT_TYPE_ALIASES.get(text.lower(), _ELEMENT_TYPE_ALIASES.get(text, text))


def _first_present(data, keys):
    for key in keys:
        if key in data and data.get(key) not in (None, ""):
            return data.get(key)
    return None


def _to_text(value):
    if value is None:
        return ""
    return "{}".format(value).strip()


def _looks_like_generate_frame_request(text):
    normalized_text = _to_text(text).lower()
    if not normalized_text:
        return False

    if "generate_frame" in normalized_text:
        return True
    if u"框架" in normalized_text:
        return True
    if u"生成" in normalized_text and (u"跨" in normalized_text or u"层" in normalized_text):
        return True
    if re.search(r"\d+\s*跨", normalized_text):
        return True
    return False


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

    if not levels or len(levels) < 2:
        return "标高不足，请先生成框架或创建标高"

    base_level = resolve_floor_boundary_level(levels, base_floor)
    top_level = resolve_floor_boundary_level(levels, top_floor)
    if not base_level or not top_level:
        return "柱的楼层范围无效，可用边界编号为 1 到 {}".format(len(levels))

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

    if not levels or len(levels) < 2:
        return "标高不足"

    level = resolve_story_framing_level(levels, floor)
    if not level:
        return "楼层超出范围，可用楼层为 1 到 {}".format(get_story_count(levels))

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
    if not levels or len(levels) < 2:
        return "标高不足"

    points = [(p[0], p[1]) for p in boundary]
    level = resolve_story_framing_level(levels, floor)
    if not level:
        return "楼层超出范围，可用楼层为 1 到 {}".format(get_story_count(levels))

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

    floor_index = normalize_floor_number(floor)
    if floor_index is None:
        return "楼层参数无效: {}".format(floor)

    level = resolve_story_level_by_category(levels, category, floor_index)
    if not level:
        return "楼层超出范围，可用楼层为 1 到 {}".format(get_story_count(levels))

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

    floor_index = normalize_floor_number(floor)
    if floor_index is None:
        return "楼层参数无效: {}".format(floor)

    level = resolve_story_level_by_category(levels, category, floor_index)
    if not level:
        return "楼层超出范围，可用楼层为 1 到 {}".format(get_story_count(levels))

    return batch_delete_by_filter(doc, category, level)


def _exec_query_count(doc, params):
    from pyrevit import DB
    from utils import get_sorted_levels

    element_type = params.get("element_type", "")
    floor = params.get("floor")

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

    if floor is not None:
        levels = get_sorted_levels(doc)
        if not levels:
            return "标高不足"

        floor_index = normalize_floor_number(floor)
        if floor_index is None:
            return "楼层参数无效: {}".format(floor)

        level = resolve_story_level_by_category(levels, cat, floor_index)
        if not level:
            return "楼层超出范围，可用楼层为 1 到 {}".format(get_story_count(levels))

        level_id = level.Id
        filtered_collector = _apply_collector_level_filter(DB, collector, level_id, element_type)
        if filtered_collector is not None:
            count = filtered_collector.GetElementCount()
        else:
            target_level_id = getattr(level_id, "IntegerValue", -1)
            count = 0
            # 某些 pyRevit/IronPython 组合下过滤器构造会失败，这里保留最慢但最稳的逐个元素兜底。
            for element in collector:
                if _get_element_level_int(DB, element) == target_level_id:
                    count += 1
    else:
        count = collector.GetElementCount()

    name_map = {"column": "柱", "beam": "梁", "slab": "板", "floor": "板"}
    if floor is None:
        return "当前模型中共有 {} 个{}构件".format(
            count, name_map.get(element_type, "")
        )
    return "当前模型第 {} 层共有 {} 个{}构件".format(
        floor, count, name_map.get(element_type, "")
    )


def _get_element_level_int(DB, element):
    level_id = getattr(element, "LevelId", None)
    integer_value = getattr(level_id, "IntegerValue", -1)
    if integer_value > 0:
        return integer_value

    for builtin in [
        DB.BuiltInParameter.FAMILY_BASE_LEVEL_PARAM,
        DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM,
        DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM,
        DB.BuiltInParameter.LEVEL_PARAM,
    ]:
        param = element.get_Parameter(builtin)
        if not param or param.StorageType != DB.StorageType.ElementId:
            continue
        param_level_id = param.AsElementId()
        integer_value = getattr(param_level_id, "IntegerValue", -1)
        if integer_value > 0:
            return integer_value

    return -1


def _apply_collector_level_filter(DB, collector, level_id, element_type):
    filtered_collector = _try_apply_element_level_filter(DB, collector, level_id)
    if filtered_collector is not None:
        return filtered_collector
    return _try_apply_level_parameter_filter(DB, collector, level_id, element_type)


def _try_apply_element_level_filter(DB, collector, level_id):
    level_filter_class = getattr(DB, "ElementLevelFilter", None)
    where_passes = getattr(collector, "WherePasses", None)
    if level_filter_class is None or where_passes is None:
        return None

    try:
        return where_passes(level_filter_class(level_id))
    except Exception:
        return None


def _try_apply_level_parameter_filter(DB, collector, level_id, element_type):
    where_passes = getattr(collector, "WherePasses", None)
    parameter_filter_class = getattr(DB, "ElementParameterFilter", None)
    provider_class = getattr(DB, "ParameterValueProvider", None)
    rule_class = getattr(DB, "FilterElementIdRule", None)
    evaluator_class = getattr(DB, "FilterNumericEquals", None)
    element_id_class = getattr(DB, "ElementId", None)
    if None in (
        where_passes,
        parameter_filter_class,
        provider_class,
        rule_class,
        evaluator_class,
        element_id_class,
    ):
        return None

    for builtin in _get_level_filter_builtins(DB, element_type):
        try:
            provider = provider_class(element_id_class(int(builtin)))
            evaluator = evaluator_class()
            rule = rule_class(provider, evaluator, level_id)
            return where_passes(parameter_filter_class(rule))
        except Exception:
            continue
    return None


def _get_level_filter_builtins(DB, element_type):
    candidates = []
    if element_type == "column":
        candidates.extend([
            "FAMILY_LEVEL_PARAM",
            "FAMILY_BASE_LEVEL_PARAM",
            "SCHEDULE_LEVEL_PARAM",
            "LEVEL_PARAM",
        ])
    else:
        candidates.extend([
            "SCHEDULE_LEVEL_PARAM",
            "INSTANCE_REFERENCE_LEVEL_PARAM",
            "LEVEL_PARAM",
        ])

    builtins = []
    for name in candidates:
        builtin = getattr(DB.BuiltInParameter, name, None)
        if builtin is not None:
            builtins.append(builtin)
    return builtins
