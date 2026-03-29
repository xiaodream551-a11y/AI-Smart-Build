# -*- coding: utf-8 -*-
"""批量回归检查 AI 回复解析结果。"""

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT_DIR / "examples" / "ai_reply_regression_cases.json"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools import debug_ai_floor as ai_debug  # noqa: E402


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
    reply = case.get("ai_reply", case.get("reply", ""))
    expected_error = case.get("expect_error", case.get("expected_error"))

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

    expect_action = case.get("expect_action")
    if expect_action not in (None, ""):
        command_expected["action"] = expect_action

    expect_params = case.get("expect_params")
    if isinstance(expect_params, dict):
        command_expected["params"] = expect_params

    if command_expected:
        expected["command"] = command_expected

    inspection_expected = case.get("expect_inspection")
    if isinstance(inspection_expected, dict):
        expected["inspection"] = inspection_expected

    return expected


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

    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
