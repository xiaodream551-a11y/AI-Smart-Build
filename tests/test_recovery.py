# -*- coding: utf-8 -*-

import pytest

from ai import recovery


class FakeOutput(object):
    def __init__(self):
        self.records = []

    def print_md(self, text):
        self.records.append(text)


class FakeConversationLog(object):
    def __init__(self):
        self.turns = []

    def log_turn(self, *args, **kwargs):
        self.turns.append(kwargs)


@pytest.mark.parametrize(
    "error_text, expected_text",
    [
        ("", "发生未知错误"),
        ("API 请求失败：timeout", "AI 服务请求失败"),
        ("API 返回错误：401 unauthorized", "AI 服务返回错误"),
        ("API 返回格式异常", "AI 服务返回内容异常"),
        ("无法从回复中提取 JSON 指令：abc", "AI 回复无法解析为建模指令"),
        ("不支持的操作类型: wall", "当前版本暂不支持"),
        ("楼层超出范围", "执行失败：楼层超出范围"),
    ],
)
def test_format_user_error_covers_common_branches(error_text, expected_text):
    message = recovery.format_user_error(error_text)

    assert expected_text in message


@pytest.mark.parametrize(
    "result_text, expected",
    [
        ("楼层超出范围，可用楼层为 1 到 3", True),
        ("缺少楼层参数", True),
        ("未找到可删除的梁", True),
        ("当前模型中共有 3 个柱构件", False),
        ("", False),
    ],
)
def test_is_execution_failure_result_detects_failure_prefixes(result_text, expected):
    assert recovery.is_execution_failure_result(result_text) is expected


def test_log_failed_turn_records_recovery_and_filter_metadata():
    output = FakeOutput()
    conversation_log = FakeConversationLog()

    recovery.log_failed_turn(
        output,
        conversation_log,
        "/replayfail 楼层",
        "缺少新截面参数",
        command={
            "action": "modify_section",
            "params": {
                "element_type": "column",
                "floor": 2,
                "old_section": "400x400",
            },
        },
        action="modify_section",
        source_kind="replay_log",
        failed_filter={
            "source_filter_kind": "replay_fail",
            "action": "modify_section",
            "keyword": "楼层",
        },
        failed_selected_round_index=4,
    )

    assert len(conversation_log.turns) == 1
    turn = conversation_log.turns[0]
    assert turn["error"] == "缺少新截面参数"
    assert turn["source_kind"] == "replay_log"
    assert turn["failed_filter"]["source_filter_kind"] == "replay_fail"
    assert turn["failed_selected_round_index"] == 4
    assert "新截面" in turn["recovery_suggestion"]
    assert any(text.startswith("**错误：**") for text in output.records)
    assert any(text.startswith("**建议：**") for text in output.records)
