# -*- coding: utf-8 -*-
"""批量回归检查 AI 回复解析结果。"""

import argparse
import contextlib
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT_DIR / "examples" / "ai_reply_regression_cases.json"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools import debug_ai_floor as ai_debug  # noqa: E402
from tools.offline_runtime import (  # noqa: E402
    FakeBuiltInCategory,
    FakeDocument,
    FakeElement,
)
from ai.parser import dispatch_command  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="批量回归检查 AI 回复解析结果")
    parser.add_argument(
        "--cases",
        default=str(DEFAULT_CASES_PATH),
        help="回归用例 JSON 文件路径",
    )
    return parser.parse_args()


def load_cases(path):
    with open(path, "r", encoding="utf-8") as input_file:
        data = json.load(input_file)
    if not isinstance(data, list):
        raise ValueError("回归用例文件必须是数组")
    return data


def build_levels(case):
    return ai_debug.build_levels(SimpleNamespace(
        levels=case.get("levels"),
        stories=case.get("stories", 5),
    ))


def assert_subset(expected, actual, path="root"):
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError("{} 应为对象，当前值: {}".format(path, actual))
        for key, value in expected.items():
            if key not in actual:
                raise AssertionError("{} 缺少键 {}".format(path, key))
            assert_subset(value, actual[key], "{}.{}".format(path, key))
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            raise AssertionError("{} 应为数组，当前值: {}".format(path, actual))
        if len(actual) < len(expected):
            raise AssertionError(
                "{} 长度不足，期望至少 {}，当前 {}".format(
                    path, len(expected), len(actual)
                )
            )
        for index, value in enumerate(expected):
            assert_subset(value, actual[index], "{}[{}]".format(path, index))
        return

    if expected != actual:
        raise AssertionError(
            "{} 不匹配，期望 {!r}，当前 {!r}".format(path, expected, actual)
        )


def evaluate_case(case):
    name = case.get("name", "unnamed")
    reply = _get_case_reply(case)
    expected_error = _get_expected_error(case)

    try:
        levels = build_levels(case)
        command = ai_debug.parse_command(reply)
        inspection = ai_debug.describe_resolution(command, levels)

        result = {
            "name": name,
            "command": command,
            "inspection": inspection,
        }

        if expected_error:
            raise AssertionError(
                "期望失败并包含 {!r}，但当前解析成功".format(expected_error)
            )

        expected = case.get("expected", {})
        if not expected:
            expected = _build_expected_from_short_case(case)
        if expected:
            assert_subset(expected.get("command", {}), command, "command")
            assert_subset(expected.get("inspection", {}), inspection, "inspection")

        expected_dispatch_result_contains = case.get("expected_dispatch_result_contains")
        if expected_dispatch_result_contains:
            with _install_dispatch_stubs():
                doc = build_dispatch_document(case, command, levels)
                dispatch_result = dispatch_command(doc, command, levels)
            result["dispatch_result"] = dispatch_result
            if expected_dispatch_result_contains not in dispatch_result:
                raise AssertionError(
                    "dispatch_result 未包含 {!r}，当前 {!r}".format(
                        expected_dispatch_result_contains,
                        dispatch_result,
                    )
                )

        return result
    except Exception as err:
        if not expected_error:
            raise

        message = "{}".format(err)
        if expected_error not in message:
            raise AssertionError(
                "错误信息不匹配，期望包含 {!r}，当前 {!r}".format(
                    expected_error, message
                )
            )
        return {
            "name": name,
            "error": message,
        }


def _build_expected_from_short_case(case):
    expected = {}
    command_expected = {}

    expect_action = case.get("expected_action", case.get("expect_action"))
    if expect_action not in (None, ""):
        command_expected["action"] = expect_action

    expect_params = case.get("expected_params", case.get("expect_params"))
    if isinstance(expect_params, dict):
        command_expected["params"] = expect_params

    if command_expected:
        expected["command"] = command_expected

    inspection_expected = case.get("expected_inspection", case.get("expect_inspection"))
    if isinstance(inspection_expected, dict):
        expected["inspection"] = inspection_expected

    return expected


def _get_case_reply(case):
    return case.get("input", case.get("ai_reply", case.get("reply", "")))


def _get_expected_error(case):
    return case.get("expected_error", case.get("expect_error"))


def build_dispatch_document(case, command, levels):
    elements = _build_dispatch_elements(command, levels)
    return FakeDocument(levels=levels, elements=elements)


def _build_dispatch_elements(command, levels):
    commands = _flatten_commands(command)
    elements = []
    for item in commands:
        if item.get("action") != "query_count":
            continue
        params = item.get("params", {})
        element_type = params.get("element_type")
        floor = params.get("floor")
        elements.extend(_build_query_elements(element_type, floor, levels))
    return elements


def _flatten_commands(command):
    if not isinstance(command, dict):
        return []
    if command.get("action") == "batch":
        commands = (command.get("params") or {}).get("commands") or []
        flattened = []
        for item in commands:
            flattened.extend(_flatten_commands(item))
        return flattened
    return [command]


def _build_query_elements(element_type, floor, levels):
    category = _resolve_query_category(element_type)
    if category is None:
        return []

    matching_level_id = _resolve_query_level_id(levels, category, floor)
    fallback_level_id = getattr(levels[0].Id, "IntegerValue", 1)
    elements = []
    if matching_level_id is not None:
        elements.append(FakeElement(1000 + len(elements), category, level_id=matching_level_id, name=_category_name(category)))
    if matching_level_id != fallback_level_id:
        elements.append(FakeElement(2000 + len(elements), category, level_id=fallback_level_id, name=_category_name(category)))
    return elements


def _resolve_query_category(element_type):
    normalized = "{}".format(element_type or "").strip().lower()
    if normalized in ("column", "columns", "柱", "柱子"):
        return FakeBuiltInCategory.OST_StructuralColumns
    if normalized in ("beam", "beams", "梁"):
        return FakeBuiltInCategory.OST_StructuralFraming
    if normalized in ("slab", "slabs", "floor", "floors", "板", "楼板"):
        return FakeBuiltInCategory.OST_Floors
    return None


def _resolve_query_level_id(levels, category, floor):
    if floor is None:
        if category == FakeBuiltInCategory.OST_StructuralColumns:
            return getattr(levels[0].Id, "IntegerValue", None)
        if len(levels) > 1:
            return getattr(levels[1].Id, "IntegerValue", None)
        return getattr(levels[0].Id, "IntegerValue", None)

    story_index = ai_debug.resolve_story_base_level(levels, floor) if category == FakeBuiltInCategory.OST_StructuralColumns else ai_debug.resolve_story_framing_level(levels, floor)
    if story_index is None:
        return None
    return getattr(story_index.Id, "IntegerValue", None)


def _category_name(category):
    if category == FakeBuiltInCategory.OST_StructuralColumns:
        return "柱"
    if category == FakeBuiltInCategory.OST_StructuralFraming:
        return "梁"
    if category == FakeBuiltInCategory.OST_Floors:
        return "板"
    return "构件"


@contextlib.contextmanager
def _install_dispatch_stubs():
    stub_modules = {
        "engine.column": _build_column_stub(),
        "engine.beam": _build_beam_stub(),
        "engine.floor": _build_floor_stub(),
        "engine.frame_generator": _build_frame_generator_stub(),
        "engine.modify": _build_modify_stub(),
    }
    original_modules = {}
    try:
        for name, module in stub_modules.items():
            original_modules[name] = sys.modules.get(name)
            sys.modules[name] = module
        yield
    finally:
        for name, original in original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _build_column_stub():
    module = ModuleType("engine.column")
    module.create_column = lambda doc, x, y, base_level, top_level, section: None
    return module


def _build_beam_stub():
    module = ModuleType("engine.beam")
    module.create_beam = lambda doc, sx, sy, ex, ey, level, section: None
    return module


def _build_floor_stub():
    module = ModuleType("engine.floor")
    module.create_floor = lambda doc, boundary, level: None
    return module


def _build_frame_generator_stub():
    module = ModuleType("engine.frame_generator")

    def generate_frame(doc, params):
        return {
            "grids": len(params.get("x_spans", [])) + len(params.get("y_spans", [])),
            "levels": (params.get("num_floors") or 0) + 1,
            "columns": 4,
            "beams": 6,
            "floors": params.get("num_floors") or 0,
        }

    def format_stats(stats):
        return (
            "生成完成：\n"
            "  轴线 {grids} 根\n"
            "  标高 {levels} 个\n"
            "  柱   {columns} 根\n"
            "  梁   {beams} 根\n"
            "  板   {floors} 块"
        ).format(**stats)

    module.generate_frame = generate_frame
    module.format_stats = format_stats
    return module


def _build_modify_stub():
    module = ModuleType("engine.modify")

    def batch_modify_by_filter(doc, category, level, old_section, new_section):
        label = _category_name(_resolve_query_category(category))
        return "已修改 1 根{}截面为 {}，标高：{}".format(
            label,
            new_section,
            getattr(level, "Name", ""),
        )

    def batch_delete_by_filter(doc, category, level):
        label = _category_name(_resolve_query_category(category))
        if level is None:
            return "已删除 2 根{}".format(label)
        return "已删除 1 根{}，标高：{}".format(
            label,
            getattr(level, "Name", ""),
        )

    module.batch_modify_by_filter = batch_modify_by_filter
    module.batch_delete_by_filter = batch_delete_by_filter
    return module


def run_cases(cases):
    passed = []
    failed = []

    for case in cases:
        try:
            passed.append(evaluate_case(case))
        except Exception as err:
            failed.append({
                "name": case.get("name", "unnamed"),
                "error": "{}".format(err),
            })

    return {
        "total": len(cases),
        "passed": passed,
        "failed": failed,
    }


def main():
    args = parse_args()
    cases = load_cases(args.cases)
    summary = run_cases(cases)

    print("回归用例总数: {}".format(summary["total"]))
    print("通过: {}".format(len(summary["passed"])))
    print("失败: {}".format(len(summary["failed"])))

    for item in summary["passed"]:
        print("[PASS] {}".format(item["name"]))

    for item in summary["failed"]:
        print("[FAIL] {} -> {}".format(item["name"], item["error"]))

    if not summary["failed"]:
        print("all passed")

    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
