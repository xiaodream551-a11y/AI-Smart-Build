# -*- coding: utf-8 -*-

import sys
import types

from tools.offline_runtime import (
    FakeBuiltInCategory,
    FakeDocument,
    FakeElement,
    make_story_levels,
)

from ai import parser


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
