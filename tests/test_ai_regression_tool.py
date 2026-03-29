# -*- coding: utf-8 -*-

import json

from conftest import load_project_script


regression_tool = load_project_script(
    "ai_regression_tool_for_tests",
    "tools/run_ai_regression.py",
)


def test_run_cases_reports_pass_and_fail():
    summary = regression_tool.run_cases([
        {
            "name": "pass-case",
            "stories": 3,
            "reply": "{\"action\":\"query_count\",\"params\":{\"element_type\":\"柱\",\"floor\":1}}",
            "expected": {
                "command": {
                    "action": "query_count",
                    "params": {
                        "element_type": "column"
                    }
                }
            }
        },
        {
            "name": "fail-case",
            "stories": 3,
            "reply": "{\"action\":\"query_count\",\"params\":{\"element_type\":\"梁\",\"floor\":2}}",
            "expected": {
                "inspection": {
                    "resolved": {
                        "level": "F9"
                    }
                }
            }
        },
    ])

    assert summary["total"] == 2
    assert len(summary["passed"]) == 1
    assert summary["passed"][0]["name"] == "pass-case"
    assert len(summary["failed"]) == 1
    assert summary["failed"][0]["name"] == "fail-case"
    assert "F9" in summary["failed"][0]["error"]


def test_load_cases_reads_json_array(tmp_path):
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps([{"name": "one", "reply": "{}"}], ensure_ascii=False),
        encoding="utf-8",
    )

    cases = regression_tool.load_cases(str(cases_path))

    assert len(cases) == 1
    assert cases[0]["name"] == "one"


def test_evaluate_case_accepts_expected_error():
    result = regression_tool.evaluate_case({
        "name": "invalid-json",
        "stories": 3,
        "ai_reply": "这不是 JSON",
        "expect_error": "无法从回复中提取 JSON 指令",
    })

    assert result["name"] == "invalid-json"
    assert "无法从回复中提取 JSON 指令" in result["error"]


def test_evaluate_case_accepts_short_case_format():
    result = regression_tool.evaluate_case({
        "name": "short-format",
        "stories": 3,
        "ai_reply": "{\"action\":\"create_beam\",\"params\":{\"start_x\":0,\"start_y\":0,\"end_x\":6000,\"end_y\":0,\"floor\":2,\"section\":\"300x600\"}}",
        "expect_action": "create_beam",
        "expect_params": {
            "floor": 2,
            "section": "300x600",
        },
    })

    assert result["name"] == "short-format"
    assert result["command"]["action"] == "create_beam"
    assert result["command"]["params"]["floor"] == 2
