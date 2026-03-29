# -*- coding: utf-8 -*-
"""Command parser -- extracts JSON from the LLM reply and dispatches to modelling functions."""

import json
import re

from config import API_TIMEOUT_MS, FRAME_API_TIMEOUT_MS
from engine.element_utils import (
    format_number,
    get_element_area_sqm,
    get_element_level_id,
    get_element_level_int,
    get_element_section_text,
    is_valid_element_id,
    looks_like_plain_numeric_text,
    normalize_numeric_text,
    resolve_level_name,
    to_text,
    try_parse_section_name,
)
from utils import (
    feet_to_mm,
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
    "query_detail": "query_detail",
    "detail": "query_detail",
    "query_list": "query_detail",
    "list_elements": "query_detail",
    "查询详情": "query_detail",
    "查询明细": "query_detail",
    "构件明细": "query_detail",
    "query_summary": "query_summary",
    "summary": "query_summary",
    "model_summary": "query_summary",
    "查询汇总": "query_summary",
    "统计汇总": "query_summary",
    "模型统计": "query_summary",
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
    Extract a JSON command from the LLM reply text.

    Args:
        reply_text: Raw reply text from the LLM.

    Returns:
        dict: ``{"action": "...", "params": {...}}``

    Raises:
        ValueError: If no valid JSON command can be extracted.
    """
    text = reply_text.strip()

    # Attempt direct JSON parsing
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        pass
    else:
        return _normalize_parsed_command_payload(payload)

    # Attempt to extract from a markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(1).strip())
        except (ValueError, TypeError):
            pass
        else:
            return _normalize_parsed_command_payload(payload)

    # Attempt to extract the first [...] or {...}
    for pattern in (r"\[.*\]", r"\{.*\}"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except (ValueError, TypeError):
                pass
            else:
                return _normalize_parsed_command_payload(payload)

    raise ValueError("无法从回复中提取 JSON 指令：{}".format(
        text[:100] + "..." if len(text) > 100 else text
    ))


def dispatch_command(doc, command, levels=None):
    """
    Dispatch a parsed command to the corresponding modelling function.

    Args:
        doc: Revit Document.
        command: Return value of ``parse_command``.
        levels: Level list (sorted by elevation index) used for floor lookup.

    Returns:
        str: A human-readable execution result description.
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
    elif action == "batch":
        return _exec_batch(doc, params, levels)
    elif action == "generate_frame":
        return _exec_generate_frame(doc, params)
    elif action == "query_count":
        return _exec_query_count(doc, params)
    elif action == "query_detail":
        return _exec_query_detail(doc, params)
    elif action == "query_summary":
        return _exec_query_summary(doc, params)
    elif action == "modify_section":
        return _exec_modify_section(doc, params, levels)
    elif action == "delete_element":
        return _exec_delete_element(doc, params, levels)
    elif action == "unknown":
        return params.get("message", "无法理解你的指令，请换个说法试试")
    else:
        return "不支持的操作类型: {}".format(action)


def normalize_command(command):
    """Normalize a model-output command into the project's internal format."""
    if not isinstance(command, dict):
        raise ValueError("命令必须为 JSON 对象")

    action = _normalize_action(command.get("action", ""))
    params = command.get("params", {})
    if not isinstance(params, dict):
        params = {}
    else:
        params = dict(params)

    if action == "batch":
        commands = params.get("commands")
        if not isinstance(commands, list) or not commands:
            raise ValueError("批量命令至少需要 1 条子指令")
        return {
            "action": "batch",
            "params": {
                "commands": [normalize_command(item) for item in commands],
            },
        }

    params = _normalize_common_params(params)
    params = _normalize_params_by_action(action, params)

    return {
        "action": action,
        "params": params,
    }


def resolve_ai_timeout_ms(user_input):
    """Infer the AI request timeout for this turn based on user input."""
    text = to_text(user_input)
    if _looks_like_generate_frame_request(text):
        return FRAME_API_TIMEOUT_MS
    return API_TIMEOUT_MS


def _normalize_parsed_command_payload(payload):
    if isinstance(payload, list):
        if not payload:
            raise ValueError("JSON 指令数组不能为空")

        commands = [normalize_command(item) for item in payload]
        if len(commands) == 1:
            return commands[0]
        return {
            "action": "batch",
            "params": {
                "commands": commands,
            },
        }

    return normalize_command(payload)


def _normalize_action(action):
    text = to_text(action)
    if not text:
        return ""
    return _ACTION_ALIASES.get(text.lower(), _ACTION_ALIASES.get(text, text))


def _normalize_common_params(params):
    normalized = dict(params)

    element_type = _first_present(
        normalized,
        [
            "element_type", "type", "category", "target_type", "component_type",
            "构件类型", "构件类别", "类别", "类型",
        ]
    )
    if element_type is not None:
        normalized["element_type"] = _normalize_element_type(element_type)

    return normalized


def _normalize_params_by_action(action, params):
    normalized = dict(params)

    if action == "create_column":
        base_floor = _first_present(
            normalized,
            [
                "base_floor", "start_floor", "from_floor", "floor", "level",
                "起始楼层", "开始楼层", "起始层", "开始层",
            ]
        )
        top_floor = _first_present(
            normalized,
            [
                "top_floor", "end_floor", "to_floor", "upper_floor",
                "结束楼层", "终止楼层", "顶部楼层", "上层楼层",
            ]
        )
        if base_floor is not None:
            normalized["base_floor"] = _normalize_floor_param_value(base_floor)
        if top_floor is not None:
            normalized["top_floor"] = _normalize_floor_param_value(top_floor)
        elif base_floor is not None:
            base_floor_number = normalize_floor_number(base_floor)
            if base_floor_number is not None:
                normalized["top_floor"] = base_floor_number + 1
        section = _first_present(
            normalized,
            ["section", "截面", "柱截面"]
        )
        if section is not None:
            normalized["section"] = _normalize_section_param_value(section)
        return normalized

    if action in (
        "create_beam",
        "create_slab",
        "modify_section",
        "delete_element",
        "query_count",
        "query_detail",
        "query_summary",
    ):
        floor = _first_present(
            normalized,
            ["floor", "level", "story", "楼层", "层", "故事层"]
        )
        if floor is not None:
            normalized["floor"] = _normalize_floor_param_value(floor)

    if action == "create_slab" and "boundary" not in normalized:
        boundary = _first_present(
            normalized,
            ["points", "vertices", "polygon", "boundary_points", "边界", "轮廓", "顶点"]
        )
        if boundary is not None:
            normalized["boundary"] = boundary

    if action == "modify_section":
        old_section = _first_present(
            normalized,
            ["old_section", "from_section", "source_section", "旧截面", "原截面"]
        )
        new_section = _first_present(
            normalized,
            ["new_section", "to_section", "target_section", "新截面", "目标截面"]
        )
        if old_section is not None:
            normalized["old_section"] = _normalize_section_param_value(old_section)
        if new_section is not None:
            normalized["new_section"] = _normalize_section_param_value(new_section)

    if action == "generate_frame":
        num_floors = _first_present(
            normalized,
            ["num_floors", "floors", "floor_count", "story_count", "stories", "层数"]
        )
        floor_height = _first_present(
            normalized,
            ["floor_height", "story_height", "height", "standard_floor_height", "层高", "标准层层高"]
        )
        first_floor_height = _first_present(
            normalized,
            ["first_floor_height", "first_height", "ground_floor_height", "首层层高"]
        )
        beam_section = _first_present(
            normalized,
            ["beam_section", "beam_size", "beam_section_default", "梁截面"]
        )
        beam_section_x = _first_present(
            normalized,
            ["beam_section_x", "beam_x_section", "x向梁截面", "X向梁截面"]
        )
        beam_section_y = _first_present(
            normalized,
            ["beam_section_y", "beam_y_section", "y向梁截面", "Y向梁截面"]
        )
        column_section = _first_present(
            normalized,
            ["column_section", "柱截面"]
        )

        if num_floors is not None:
            normalized["num_floors"] = _normalize_floor_param_value(num_floors)
        if floor_height is not None:
            normalized["floor_height"] = floor_height
        if first_floor_height is not None:
            normalized["first_floor_height"] = first_floor_height
        if column_section is not None:
            normalized["column_section"] = _normalize_section_param_value(column_section)
        if beam_section is not None:
            beam_section = _normalize_section_param_value(beam_section)
        if beam_section_x is not None:
            beam_section_x = _normalize_section_param_value(beam_section_x)
        if beam_section_y is not None:
            beam_section_y = _normalize_section_param_value(beam_section_y)
        if beam_section_x is None and beam_section is not None:
            beam_section_x = beam_section
        if beam_section_y is None:
            beam_section_y = beam_section_x or beam_section
        if beam_section_x is not None:
            normalized["beam_section_x"] = beam_section_x
        if beam_section_y is not None:
            normalized["beam_section_y"] = beam_section_y

    if action == "create_beam":
        section = _first_present(
            normalized,
            ["section", "截面", "梁截面"]
        )
        if section is not None:
            normalized["section"] = _normalize_section_param_value(section)

    if action == "query_detail":
        section = _first_present(
            normalized,
            ["section", "截面", "构件截面"]
        )
        if section is not None:
            normalized["section"] = _normalize_section_param_value(section)

    return normalized


def _normalize_element_type(element_type):
    text = to_text(element_type)
    if not text:
        return ""
    return _ELEMENT_TYPE_ALIASES.get(text.lower(), _ELEMENT_TYPE_ALIASES.get(text, text))


def _first_present(data, keys):
    for key in keys:
        if key in data and data.get(key) not in (None, ""):
            return data.get(key)
    return None


def _looks_like_generate_frame_request(text):
    normalized_text = to_text(text).lower()
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


def _normalize_floor_param_value(value):
    text = to_text(value)
    if text and looks_like_plain_numeric_text(text):
        return value

    normalized_floor = normalize_floor_number(value)
    if normalized_floor is None:
        return value
    return normalized_floor


def _normalize_section_param_value(value):
    text = to_text(value)
    if not text:
        return text

    normalized = text.replace(u"×", "x").replace("X", "x").strip()
    if "x" in normalized:
        parts = normalized.split("x")
        if len(parts) == 2 and looks_like_plain_numeric_text(parts[0]) and looks_like_plain_numeric_text(parts[1]):
            return "{}x{}".format(normalize_numeric_text(parts[0]), normalize_numeric_text(parts[1]))
        return normalized

    if looks_like_plain_numeric_text(normalized):
        token = normalize_numeric_text(normalized)
        return "{}x{}".format(token, token)
    return normalized


# ============================================================
# Execution functions for each action
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


def _exec_batch(doc, params, levels):
    from utils import get_sorted_levels

    commands = params.get("commands") or []
    if not isinstance(commands, list) or not commands:
        return "批量指令为空"

    results = []
    current_levels = levels
    for index, command in enumerate(commands, start=1):
        normalized_command = normalize_command(command)
        try:
            result = dispatch_command(doc, normalized_command, current_levels)
        except Exception as err:
            result = "执行失败：{}".format(err)
        results.append("{}. {}".format(index, result))

        if normalized_command.get("action") in ("generate_frame", "batch") and doc is not None:
            try:
                current_levels = get_sorted_levels(doc)
            except Exception:
                pass

    return "批量执行 {} 条指令：\n{}".format(
        len(commands),
        "\n".join(results)
    )


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
    element_type = params.get("element_type", "")
    floor = params.get("floor")
    elements, _levels, error_text = _collect_query_elements(
        doc,
        element_type,
        floor=floor,
    )
    if error_text:
        return error_text

    count = len(elements)

    name_map = {"column": "柱", "beam": "梁", "slab": "板", "floor": "板"}
    if floor is None:
        return "当前模型中共有 {} 个{}构件".format(
            count, name_map.get(element_type, "")
        )
    return "当前模型第 {} 层共有 {} 个{}构件".format(
        floor, count, name_map.get(element_type, "")
    )


def _exec_query_detail(doc, params):
    element_type = params.get("element_type", "")
    floor = params.get("floor")
    section = params.get("section", "")

    elements, levels, error_text = _collect_query_elements(
        doc,
        element_type,
        floor=floor,
        section=section,
    )
    if error_text:
        return error_text
    if not elements:
        return _format_query_detail_empty(element_type, floor, section)

    from pyrevit import DB

    lines = [_format_query_detail_header(len(elements), element_type, floor, section)]
    for index, element in enumerate(elements, start=1):
        lines.append("{}. {}".format(
            index,
            _format_query_detail_line(DB, doc, levels, element, element_type),
        ))
    return "\n".join(lines)


def _exec_query_summary(doc, params):
    from utils import get_sorted_levels

    floor = params.get("floor")
    levels = get_sorted_levels(doc)
    if not levels:
        return "标高不足"

    header = "模型统计："
    if floor is not None:
        header = "第 {} 层模型统计：".format(floor)

    column_elements, _levels, error_text = _collect_query_elements(doc, "column", floor=floor)
    if error_text:
        return error_text
    beam_elements, _levels, error_text = _collect_query_elements(doc, "beam", floor=floor)
    if error_text:
        return error_text
    slab_elements, _levels, error_text = _collect_query_elements(doc, "slab", floor=floor)
    if error_text:
        return error_text

    lines = [
        header,
        "标高：{} 个（{} ~ {}）".format(
            len(levels),
            getattr(levels[0], "Name", ""),
            getattr(levels[-1], "Name", ""),
        ),
        _format_query_summary_line("column", column_elements),
        _format_query_summary_line("beam", beam_elements),
        _format_query_summary_line("slab", slab_elements),
    ]
    return "\n".join(lines)


def _collect_query_elements(doc, element_type, floor=None, section=None):
    from pyrevit import DB
    from utils import get_sorted_levels

    cat = _get_query_category(DB, element_type)
    if not cat:
        return None, None, "不支持查询的构件类型: {}".format(element_type)

    collector = DB.FilteredElementCollector(doc) \
        .OfCategory(cat) \
        .WhereElementIsNotElementType()
    elements = list(collector)
    levels = get_sorted_levels(doc)

    if floor is not None:
        if not levels:
            return None, None, "标高不足"

        floor_index = normalize_floor_number(floor)
        if floor_index is None:
            return None, levels, "楼层参数无效: {}".format(floor)

        level = resolve_story_level_by_category(levels, cat, floor_index)
        if not level:
            return None, levels, "楼层超出范围，可用楼层为 1 到 {}".format(get_story_count(levels))

        level_id = level.Id
        filtered_collector = _apply_collector_level_filter(DB, collector, level_id, element_type)
        if filtered_collector is not None:
            elements = list(filtered_collector)
        else:
            target_level_id = getattr(level_id, "IntegerValue", -1)
            elements = [
                element for element in elements
                if get_element_level_int(DB, element) == target_level_id
            ]

    if section:
        target_section = _normalize_section_param_value(section)
        elements = [
            element for element in elements
            if _normalize_section_param_value(get_element_section_text(DB, element)) == target_section
        ]

    elements.sort(key=lambda element: _build_query_sort_key(DB, element, element_type))
    return elements, levels, ""


def _get_query_category(DB, element_type):
    return {
        "column": DB.BuiltInCategory.OST_StructuralColumns,
        "beam": DB.BuiltInCategory.OST_StructuralFraming,
        "slab": DB.BuiltInCategory.OST_Floors,
        "floor": DB.BuiltInCategory.OST_Floors,
    }.get(element_type)


def _format_query_detail_empty(element_type, floor=None, section=None):
    scope_text = "当前模型中"
    if floor is not None:
        scope_text = "第 {} 层".format(floor)

    target_text = _get_query_element_name(element_type)
    if section and element_type in ("column", "beam"):
        target_text = "{} {}".format(
            _normalize_section_param_value(section),
            target_text,
        )

    return "{}未找到 {}".format(scope_text, target_text)


def _format_query_detail_header(count, element_type, floor=None, section=None):
    scope_text = "当前模型中"
    if floor is not None:
        scope_text = "第 {} 层".format(floor)

    if section and element_type in ("column", "beam"):
        return "{}共有 {} {} {} {}：".format(
            scope_text,
            count,
            _get_query_element_unit(element_type),
            _normalize_section_param_value(section),
            _get_query_element_name(element_type),
        )

    return "{}共有 {} {}{}：".format(
        scope_text,
        count,
        _get_query_element_unit(element_type),
        _get_query_element_name(element_type),
    )


def _format_query_detail_line(DB, doc, levels, element, element_type):
    parts = ["ID={}".format(getattr(getattr(element, "Id", None), "IntegerValue", ""))]
    floor_label = _resolve_element_story_label(DB, levels, element_type, element)
    if not floor_label:
        floor_label = resolve_level_name(doc, get_element_level_id(DB, element))

    if element_type == "column":
        point = getattr(getattr(element, "Location", None), "Point", None)
        parts.append("位置 {}".format(_format_point_text(point)))
    elif element_type == "beam":
        curve = getattr(getattr(element, "Location", None), "Curve", None)
        if curve is not None:
            parts.append("起点 {}".format(_format_point_text(curve.GetEndPoint(0))))
            parts.append("终点 {}".format(_format_point_text(curve.GetEndPoint(1))))
    elif element_type == "slab":
        parts.append("面积 {} m²".format(format_number(get_element_area_sqm(DB, element))))

    if floor_label:
        parts.append("楼层 {}".format(floor_label))

    section_text = get_element_section_text(DB, element)
    if section_text and element_type in ("column", "beam"):
        parts.append("截面 {}".format(section_text))

    return ", ".join(parts)


def _format_query_summary_line(element_type, elements):
    count = len(elements)
    label = _get_query_element_name(element_type)
    unit = _get_query_element_unit(element_type)
    if element_type == "slab":
        return "{}：{} {}".format(label, count, unit)

    from pyrevit import DB

    section_counts = {}
    for element in elements:
        section_text = get_element_section_text(DB, element) or "未标注截面"
        section_counts[section_text] = section_counts.get(section_text, 0) + 1

    if not section_counts:
        return "{}：{} {}".format(label, count, unit)

    details = []
    for section_text in sorted(section_counts):
        details.append("{}: {}".format(section_text, section_counts[section_text]))
    return "{}：{} {}（{}）".format(label, count, unit, ", ".join(details))


def _get_query_element_name(element_type):
    return {
        "column": "柱",
        "beam": "梁",
        "slab": "板",
        "floor": "板",
    }.get(element_type, "")


def _get_query_element_unit(element_type):
    return {
        "column": "根",
        "beam": "根",
        "slab": "块",
        "floor": "块",
    }.get(element_type, "个")


def _build_query_sort_key(DB, element, element_type):
    element_id = getattr(getattr(element, "Id", None), "IntegerValue", -1)
    if element_type == "column":
        point = getattr(getattr(element, "Location", None), "Point", None)
        return _build_point_sort_key(point) + (element_id,)

    if element_type == "beam":
        curve = getattr(getattr(element, "Location", None), "Curve", None)
        if curve is not None:
            start = curve.GetEndPoint(0)
            end = curve.GetEndPoint(1)
            return _build_point_sort_key(start) + _build_point_sort_key(end) + (element_id,)

    return (get_element_level_int(DB, element), element_id)


def _build_point_sort_key(point):
    if point is None:
        return (0.0, 0.0)
    return (float(getattr(point, "X", 0.0)), float(getattr(point, "Y", 0.0)))


def _format_point_text(point):
    if point is None:
        return "未知"
    return "({}, {})".format(
        format_number(feet_to_mm(getattr(point, "X", 0.0))),
        format_number(feet_to_mm(getattr(point, "Y", 0.0))),
    )


def _resolve_element_story_label(DB, levels, element_type, element):
    if not levels:
        return ""

    target_level_id = get_element_level_int(DB, element)
    if target_level_id <= 0:
        return ""

    for floor_number in range(1, get_story_count(levels) + 1):
        level = resolve_story_level_by_category(levels, element_type, floor_number)
        if getattr(getattr(level, "Id", None), "IntegerValue", -1) == target_level_id:
            return "第 {} 层".format(floor_number)
    return ""


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
