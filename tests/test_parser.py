# -*- coding: utf-8 -*-

import sys
import types

import pytest

from tools.offline_runtime import (
    FakeBuiltInCategory,
    FakeCurve,
    FakeCurveLocation,
    FakeDocument,
    FakeElement,
    FakeElementType,
    FakePointLocation,
    FakeXYZ,
    make_story_levels,
)

from ai import parser


def _mm_to_feet(value_mm):
    return float(value_mm) / 304.8


def _make_point_location(x_mm, y_mm):
    return FakePointLocation(FakeXYZ(_mm_to_feet(x_mm), _mm_to_feet(y_mm), 0))


def _make_curve_location(start_x_mm, start_y_mm, end_x_mm, end_y_mm):
    return FakeCurveLocation(FakeCurve(
        FakeXYZ(_mm_to_feet(start_x_mm), _mm_to_feet(start_y_mm), 0),
        FakeXYZ(_mm_to_feet(end_x_mm), _mm_to_feet(end_y_mm), 0),
    ))


def _make_query_test_doc():
    levels = make_story_levels(5)
    column_500 = FakeElementType(9001, name="500x500")
    column_600 = FakeElementType(9002, name="600x600")
    beam_300x600 = FakeElementType(9003, name="300x600")
    beam_300x700 = FakeElementType(9004, name="300x700")

    elements = [
        FakeElement(
            301,
            FakeBuiltInCategory.OST_StructuralColumns,
            level_id=2,
            name="柱",
            location=_make_point_location(0, 0),
            symbol=column_500,
        ),
        FakeElement(
            302,
            FakeBuiltInCategory.OST_StructuralColumns,
            level_id=2,
            name="柱",
            location=_make_point_location(6000, 0),
            symbol=column_500,
        ),
        FakeElement(
            303,
            FakeBuiltInCategory.OST_StructuralColumns,
            level_id=2,
            name="柱",
            location=_make_point_location(0, 6000),
            symbol=column_600,
        ),
        FakeElement(
            304,
            FakeBuiltInCategory.OST_StructuralColumns,
            level_id=3,
            name="柱",
            location=_make_point_location(0, 12000),
            symbol=column_500,
        ),
        FakeElement(
            401,
            FakeBuiltInCategory.OST_StructuralFraming,
            level_id=3,
            name="梁",
            location=_make_curve_location(0, 0, 6000, 0),
            symbol=beam_300x600,
        ),
        FakeElement(
            402,
            FakeBuiltInCategory.OST_StructuralFraming,
            level_id=4,
            name="梁",
            location=_make_curve_location(0, 6000, 6000, 6000),
            symbol=beam_300x700,
        ),
        FakeElement(
            501,
            FakeBuiltInCategory.OST_Floors,
            level_id=3,
            name="板",
            area=36.0 / (0.3048 ** 2),
        ),
    ]
    doc = FakeDocument(
        levels=levels,
        elements=elements,
        element_types=[column_500, column_600, beam_300x600, beam_300x700],
    )
    return levels, doc


def test_parse_command_from_markdown_code_block():
    reply_text = """
这里是解释文字。

```json
{"action":"create_beam","params":{"start_x":0,"start_y":0,"end_x":6000,"end_y":0,"floor":2,"section":"300x600"}}
```
"""
    command = parser.parse_command(reply_text)

    assert command["action"] == "create_beam"
    assert command["params"]["floor"] == 2


def test_parse_command_normalizes_action_and_param_aliases():
    reply_text = """
```json
{
  "action": "create_floor",
  "params": {
    "points": [[0, 0], [6000, 0], [6000, 6000], [0, 6000]],
    "level": "2"
  }
}
```
"""
    command = parser.parse_command(reply_text)

    assert command["action"] == "create_slab"
    assert command["params"]["boundary"][2] == [6000, 6000]
    assert command["params"]["floor"] == "2"


def test_parse_command_normalizes_chinese_floor_and_section_aliases():
    reply_text = """
```json
{
  "action": "create_column",
  "params": {
    "x": 12000,
    "y": 6000,
    "起始楼层": "二层",
    "结束楼层": "三层",
    "截面": "500"
  }
}
```
"""
    command = parser.parse_command(reply_text)

    assert command["action"] == "create_column"
    assert command["params"]["base_floor"] == 2
    assert command["params"]["top_floor"] == 3
    assert command["params"]["section"] == "500x500"


def test_parse_command_normalizes_chinese_story_floor_text():
    reply_text = """
```json
{
  "action": "create_slab",
  "params": {
    "boundary": [[0, 0], [6000, 0], [6000, 6000], [0, 6000]],
    "floor": "三层"
  }
}
```
"""
    command = parser.parse_command(reply_text)

    assert command["action"] == "create_slab"
    assert command["params"]["floor"] == 3


def test_parse_command_normalizes_single_number_beam_section():
    reply_text = """
```json
{
  "action": "create_beam",
  "params": {
    "start_x": 0,
    "start_y": 0,
    "end_x": 6000,
    "end_y": 0,
    "floor": 2,
    "section": "500"
  }
}
```
"""
    command = parser.parse_command(reply_text)

    assert command["action"] == "create_beam"
    assert command["params"]["section"] == "500x500"


def test_parse_command_wraps_json_array_as_batch():
    reply_text = """
```json
[
  {"action": "query_count", "params": {"element_type": "column"}},
  {"action": "query_count", "params": {"element_type": "beam"}}
]
```
"""
    command = parser.parse_command(reply_text)

    assert command["action"] == "batch"
    assert len(command["params"]["commands"]) == 2
    assert command["params"]["commands"][0]["action"] == "query_count"
    assert command["params"]["commands"][1]["params"]["element_type"] == "beam"


def test_parse_command_returns_single_command_for_single_item_array():
    reply_text = """
```json
[
  {"action": "创建楼板", "params": {"points": [[0, 0], [6000, 0], [6000, 6000]], "楼层": "2"}}
]
```
"""
    command = parser.parse_command(reply_text)

    assert command["action"] == "create_slab"
    assert command["params"]["floor"] == "2"
    assert command["params"]["boundary"][1] == [6000, 0]


def test_parse_command_rejects_empty_json_array():
    with pytest.raises(ValueError, match="JSON 指令数组不能为空"):
        parser.parse_command("[]")


def test_normalize_command_expands_beam_section_to_x_and_y():
    command = parser.normalize_command({
        "action": "generate_frame",
        "params": {
            "beam_section": "350x700",
        },
    })

    assert command["action"] == "generate_frame"
    assert command["params"]["beam_section_x"] == "350x700"
    assert command["params"]["beam_section_y"] == "350x700"


def test_normalize_command_normalizes_batch_subcommands():
    command = parser.normalize_command({
        "action": "batch",
        "params": {
            "commands": [
                {"action": "创建梁", "params": {"floor": "三层", "section": "500"}},
                {"action": "create_floor", "params": {"points": [[0, 0], [1, 0], [1, 1]], "level": 2}},
            ],
        },
    })

    assert command["action"] == "batch"
    assert command["params"]["commands"][0]["action"] == "create_beam"
    assert command["params"]["commands"][0]["params"]["floor"] == 3
    assert command["params"]["commands"][0]["params"]["section"] == "500x500"
    assert command["params"]["commands"][1]["action"] == "create_slab"


def test_dispatch_create_column_uses_boundary_levels(monkeypatch):
    records = {}
    fake_module = types.ModuleType("engine.column")

    def fake_create_column(doc, x, y, base_level, top_level, section):
        records["x"] = x
        records["y"] = y
        records["base_level"] = base_level.Name
        records["top_level"] = top_level.Name
        records["section"] = section

    fake_module.create_column = fake_create_column
    monkeypatch.setitem(sys.modules, "engine.column", fake_module)

    levels = make_story_levels(3)
    result = parser.dispatch_command(None, {
        "action": "create_column",
        "params": {
            "x": 6000,
            "y": 0,
            "base_floor": 2,
            "top_floor": 3,
            "section": "500x500",
        },
    }, levels)

    assert result == "已在 (6000,0) 创建 500x500 柱，2 层到 3 层"
    assert records["base_level"] == "F1"
    assert records["top_level"] == "F2"


def test_dispatch_modify_section_uses_story_base_level_for_columns(monkeypatch):
    records = {}
    fake_module = types.ModuleType("engine.modify")

    def fake_batch_modify_by_filter(doc, category, level, old_section, new_section):
        records["category"] = category
        records["level"] = level.Name
        records["old_section"] = old_section
        records["new_section"] = new_section
        return "ok"

    fake_module.batch_modify_by_filter = fake_batch_modify_by_filter
    monkeypatch.setitem(sys.modules, "engine.modify", fake_module)

    levels = make_story_levels(3)
    result = parser.dispatch_command(None, {
        "action": "modify_section",
        "params": {
            "element_type": "column",
            "floor": 2,
            "old_section": "400x400",
            "new_section": "500x500",
        },
    }, levels)

    assert result == "ok"
    assert records["category"] == "column"
    assert records["level"] == "F1"


def test_exec_modify_section_returns_error_when_levels_missing():
    result = parser._exec_modify_section(None, {
        "element_type": "column",
        "floor": 2,
        "old_section": "400x400",
        "new_section": "500x500",
    }, None)

    assert result == "标高不足"


def test_dispatch_command_executes_batch_and_aggregates_results(monkeypatch):
    records = []

    monkeypatch.setattr(
        parser,
        "_exec_create_column",
        lambda doc, params, levels: records.append(("column", params["x"])) or "已创建柱A"
    )
    monkeypatch.setattr(
        parser,
        "_exec_create_beam",
        lambda doc, params, levels: records.append(("beam", params["start_x"])) or "已创建梁B"
    )

    result = parser.dispatch_command(None, {
        "action": "batch",
        "params": {
            "commands": [
                {"action": "create_column", "params": {"x": 0}},
                {"action": "create_beam", "params": {"start_x": 6000}},
            ],
        },
    }, make_story_levels(3))

    assert records == [("column", 0), ("beam", 6000)]
    assert "批量执行 2 条指令" in result
    assert "1. 已创建柱A" in result
    assert "2. 已创建梁B" in result


def test_dispatch_command_batch_continues_after_exception(monkeypatch):
    records = []

    def fake_exec_create_column(doc, params, levels):
        records.append("column")
        raise ValueError("柱参数错误")

    def fake_exec_create_beam(doc, params, levels):
        records.append("beam")
        return "已创建梁"

    monkeypatch.setattr(parser, "_exec_create_column", fake_exec_create_column)
    monkeypatch.setattr(parser, "_exec_create_beam", fake_exec_create_beam)

    result = parser.dispatch_command(None, {
        "action": "batch",
        "params": {
            "commands": [
                {"action": "create_column", "params": {}},
                {"action": "create_beam", "params": {}},
            ],
        },
    }, make_story_levels(3))

    assert records == ["column", "beam"]
    assert "1. 执行失败：柱参数错误" in result
    assert "2. 已创建梁" in result


def test_dispatch_generate_frame_normalizes_alias_fields(monkeypatch):
    records = {}
    fake_module = types.ModuleType("engine.frame_generator")

    def fake_generate_frame(doc, params):
        records["params"] = dict(params)
        return {"grids": 1, "levels": 2, "columns": 3, "beams": 4, "floors": 5}

    def fake_format_stats(stats):
        return "ok:{}".format(stats["beams"])

    fake_module.generate_frame = fake_generate_frame
    fake_module.format_stats = fake_format_stats
    monkeypatch.setitem(sys.modules, "engine.frame_generator", fake_module)

    result = parser.dispatch_command(None, {
        "action": "create_frame",
        "params": {
            "x_spans": [6000, 6000],
            "y_spans": [6000],
            "floor_count": 4,
            "height": 3600,
            "beam_section": "300x700",
        },
    })

    assert result == "ok:4"
    assert records["params"]["num_floors"] == 4
    assert records["params"]["floor_height"] == 3600
    assert records["params"]["beam_section_x"] == "300x700"
    assert records["params"]["beam_section_y"] == "300x700"


def test_query_count_filters_beams_by_story_level():
    levels = make_story_levels(3)
    doc = FakeDocument(
        levels=levels,
        elements=[
            FakeElement(101, FakeBuiltInCategory.OST_StructuralFraming, level_id=2, name="梁"),
            FakeElement(102, FakeBuiltInCategory.OST_StructuralFraming, level_id=3, name="梁"),
            FakeElement(103, FakeBuiltInCategory.OST_StructuralColumns, level_id=1, name="柱"),
        ],
    )

    result = parser.dispatch_command(doc, {
        "action": "query_count",
        "params": {
            "element_type": "beam",
            "floor": 2,
        },
    }, levels)

    assert result == "当前模型第 2 层共有 1 个梁构件"


def test_query_count_accepts_chinese_element_type():
    levels = make_story_levels(3)
    doc = FakeDocument(
        levels=levels,
        elements=[
            FakeElement(201, FakeBuiltInCategory.OST_StructuralColumns, level_id=1, name="柱"),
            FakeElement(202, FakeBuiltInCategory.OST_StructuralColumns, level_id=2, name="柱"),
        ],
    )

    result = parser.dispatch_command(doc, {
        "action": "query_count",
        "params": {
            "element_type": "柱子",
            "floor": 1,
        },
    }, levels)

    assert result == "当前模型第 1 层共有 1 个柱构件"


def test_parse_command_supports_query_detail_aliases():
    command = parser.parse_command(
        '{"action":"查询详情","params":{"构件类型":"柱子","楼层":"二层","截面":"500"}}'
    )

    assert command["action"] == "query_detail"
    assert command["params"]["element_type"] == "column"
    assert command["params"]["floor"] == 2
    assert command["params"]["section"] == "500x500"


def test_query_detail_filters_by_floor_and_section():
    levels, doc = _make_query_test_doc()

    result = parser.dispatch_command(doc, {
        "action": "query_detail",
        "params": {
            "element_type": "column",
            "floor": 2,
            "section": "500",
        },
    }, levels)

    assert result.startswith("第 2 层共有 2 根 500x500 柱：")
    assert "1. ID=301, 位置 (0, 0), 楼层 第 2 层, 截面 500x500" in result
    assert "2. ID=302, 位置 (6000, 0), 楼层 第 2 层, 截面 500x500" in result
    assert "ID=303" not in result
    assert "ID=304" not in result


def test_query_detail_returns_empty_message_when_no_match():
    levels, doc = _make_query_test_doc()

    result = parser.dispatch_command(doc, {
        "action": "query_detail",
        "params": {
            "element_type": "column",
            "floor": 4,
            "section": "700",
        },
    }, levels)

    assert result == "第 4 层未找到 700x700 柱"


def test_query_detail_lists_beam_endpoints():
    levels, doc = _make_query_test_doc()

    result = parser.dispatch_command(doc, {
        "action": "query_detail",
        "params": {
            "element_type": "beam",
            "floor": 2,
        },
    }, levels)

    assert result.startswith("第 2 层共有 1 根梁：")
    assert "ID=401, 起点 (0, 0), 终点 (6000, 0), 楼层 第 2 层, 截面 300x600" in result


def test_query_summary_reports_model_statistics():
    levels, doc = _make_query_test_doc()

    result = parser.dispatch_command(doc, {
        "action": "query_summary",
        "params": {},
    }, levels)

    assert result.startswith("模型统计：")
    assert "标高：6 个（±0.000 ~ 屋面）" in result
    assert "柱：4 根（500x500: 3, 600x600: 1）" in result
    assert "梁：2 根（300x600: 1, 300x700: 1）" in result
    assert "板：1 块" in result


def test_query_summary_accepts_chinese_floor_alias():
    levels, doc = _make_query_test_doc()

    result = parser.dispatch_command(doc, {
        "action": "模型统计",
        "params": {
            "楼层": "二层",
        },
    }, levels)

    assert result.startswith("第 2 层模型统计：")
    assert "柱：3 根（500x500: 2, 600x600: 1）" in result
    assert "梁：1 根（300x600: 1）" in result
    assert "板：1 块" in result


def test_exec_delete_element_without_floor_uses_full_delete_path(monkeypatch):
    records = {}
    fake_module = types.ModuleType("engine.modify")

    def fake_batch_delete_by_filter(doc, category, level):
        records["doc"] = doc
        records["category"] = category
        records["level"] = level
        return "deleted"

    fake_module.batch_delete_by_filter = fake_batch_delete_by_filter
    monkeypatch.setitem(sys.modules, "engine.modify", fake_module)

    result = parser._exec_delete_element("doc", {
        "element_type": "beam",
    }, levels=make_story_levels(3))

    assert result == "deleted"
    assert records["doc"] == "doc"
    assert records["category"] == "beam"
    assert records["level"] is None


def test_resolve_ai_timeout_ms_uses_frame_timeout_for_frame_requests():
    assert parser.resolve_ai_timeout_ms("生成一个 3 跨 x 2 跨、5 层的框架") == parser.FRAME_API_TIMEOUT_MS
    assert parser.resolve_ai_timeout_ms("统计一下柱子数量") == parser.API_TIMEOUT_MS


def test_apply_collector_level_filter_prefers_element_level_filter():
    records = {}

    class FakeCollector(object):
        def WherePasses(self, filter_obj):
            records["filter"] = filter_obj
            return self

    fake_db = types.SimpleNamespace(
        ElementLevelFilter=lambda level_id: ("level-filter", level_id),
    )

    filtered = parser._apply_collector_level_filter(
        fake_db,
        FakeCollector(),
        "L2",
        "beam",
    )

    assert filtered is not None
    assert records["filter"] == ("level-filter", "L2")


def test_apply_collector_level_filter_falls_back_to_parameter_filter():
    records = {}

    class FakeCollector(object):
        def WherePasses(self, filter_obj):
            records["filter"] = filter_obj
            return self

    fake_db = types.SimpleNamespace(
        ElementLevelFilter=None,
        ElementParameterFilter=lambda rule: ("param-filter", rule),
        ParameterValueProvider=lambda parameter_id: ("provider", parameter_id),
        FilterElementIdRule=lambda provider, evaluator, level_id: (
            "rule",
            provider,
            evaluator,
            level_id,
        ),
        FilterNumericEquals=lambda: "equals",
        ElementId=lambda value: ("eid", value),
        BuiltInParameter=types.SimpleNamespace(
            SCHEDULE_LEVEL_PARAM=10,
            INSTANCE_REFERENCE_LEVEL_PARAM=11,
            LEVEL_PARAM=12,
        ),
    )

    filtered = parser._apply_collector_level_filter(
        fake_db,
        FakeCollector(),
        "L3",
        "beam",
    )

    assert filtered is not None
    assert records["filter"] == (
        "param-filter",
        ("rule", ("provider", ("eid", 10)), "equals", "L3"),
    )


# ---------------------------------------------------------------------------
# strip_markdown_json_blocks tests
# ---------------------------------------------------------------------------

class TestStripMarkdownJsonBlocks(object):
    def test_strips_json_code_block(self):
        text = '```json\n{"action":"create_column","params":{"x":0}}\n```'
        assert parser.strip_markdown_json_blocks(text) == '{"action":"create_column","params":{"x":0}}'

    def test_strips_plain_code_block(self):
        text = '```\n{"action":"create_beam","params":{}}\n```'
        assert parser.strip_markdown_json_blocks(text) == '{"action":"create_beam","params":{}}'

    def test_strips_leading_trailing_whitespace(self):
        text = '  \n```json\n{"a":1}\n```\n  '
        assert parser.strip_markdown_json_blocks(text) == '{"a":1}'

    def test_handles_multiple_code_blocks(self):
        text = '```json\n{"a":1}\n```\nsome text\n```json\n{"b":2}\n```'
        result = parser.strip_markdown_json_blocks(text)
        assert '{"a":1}' in result
        assert '{"b":2}' in result

    def test_returns_plain_text_unchanged(self):
        text = '{"action":"query_count","params":{}}'
        assert parser.strip_markdown_json_blocks(text) == text

    def test_returns_stripped_text_without_code_blocks(self):
        text = '  {"action":"query_count"}  '
        assert parser.strip_markdown_json_blocks(text) == '{"action":"query_count"}'


class TestParseCommandMarkdownStripping(object):
    """Verify that parse_command correctly handles markdown-wrapped JSON."""

    def test_json_code_block_only(self):
        text = '```json\n{"action":"create_column","params":{"x":0,"y":0}}\n```'
        cmd = parser.parse_command(text)
        assert cmd["action"] == "create_column"
        assert cmd["params"]["x"] == 0

    def test_plain_code_block_only(self):
        text = '```\n{"action":"create_beam","params":{"start_x":0,"start_y":0,"end_x":6000,"end_y":0,"floor":1,"section":"300x600"}}\n```'
        cmd = parser.parse_command(text)
        assert cmd["action"] == "create_beam"

    def test_code_block_with_surrounding_text(self):
        text = u"AI \u8bf4\u660e\u6587\u5b57\n```json\n{\"action\":\"query_count\",\"params\":{\"element_type\":\"column\"}}\n```\n\u540e\u7eed\u8bf4\u660e"
        cmd = parser.parse_command(text)
        assert cmd["action"] == "query_count"

    def test_code_block_with_extra_whitespace(self):
        text = '\n\n  ```json\n  {"action":"query_summary","params":{}}  \n  ```\n\n'
        cmd = parser.parse_command(text)
        assert cmd["action"] == "query_summary"
