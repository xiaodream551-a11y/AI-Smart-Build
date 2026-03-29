# -*- coding: utf-8 -*-

from pathlib import Path
import os

from ai.conversation_parser import _load_command_entries_from_latest_conversation_log
from engine.logger import (
    ConversationLog,
    OperationLog,
    find_latest_output_path,
    export_conversation_log,
    export_operation_log,
)


def test_operation_log_summary_and_detail():
    operation_log = OperationLog()
    operation_log.log("create_column", "创建首层柱", count=3)
    operation_log.log("skip_row", "第 8 行已跳过：截面为空")

    assert operation_log.get_summary() == "本次操作：创建 3 根柱、跳过 1 行"

    detail = operation_log.get_detail()
    assert "create_column x3" in detail
    assert "skip_row" in detail


def test_operation_log_skips_zero_and_negative_count(capsys):
    operation_log = OperationLog()

    assert operation_log.log("query_count", "忽略零次", count=0) is None
    assert operation_log.log("query_count", "忽略负次", count=-3) is None

    assert operation_log.logs == []
    assert operation_log.counts == {}
    assert "负数 count=-3" in capsys.readouterr().out


def test_export_operation_log(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    operation_log = OperationLog()
    operation_log.log("query_count", "统计首层柱数量")

    output_path = export_operation_log(operation_log, "单元测试")

    assert output_path is not None
    output_file = Path(output_path)
    assert output_file.exists()
    assert "AI智建日志" in str(output_file)
    assert "query_count" in output_file.read_text(encoding="utf-8")


def test_export_conversation_log(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    conversation_log = ConversationLog()
    conversation_log.log_turn(
        "统计一下柱子数量",
        reply='{"action":"query_count","params":{"element_type":"column"}}',
        command={"action": "query_count", "params": {"element_type": "column"}},
        result="当前模型中共有 3 个柱构件",
        action="query_count",
        request_duration_ms=128,
        source_kind="retry",
    )
    conversation_log.log_turn(
        "/replayfail",
        command={"action": "create_beam", "params": {"floor": 2}},
        error="执行失败：梁截面参数缺失",
        recovery_suggestion="先核对楼层编号、坐标和截面参数是否完整；修正后可用 /replayfail 或 /replaypickfail 直接重放失败指令。",
        action="create_beam",
        source_kind="replay_log",
        failed_filter={
            "source_filter_kind": "replay_fail",
            "action": "create_beam",
            "keyword": "楼层",
        },
        failed_selected_round_index=7,
    )

    output_path = export_conversation_log(conversation_log, "AI对话会话")

    assert output_path is not None
    output_file = Path(output_path)
    assert output_file.exists()
    assert output_file.suffix == ".md"
    content = output_file.read_text(encoding="utf-8")
    assert "AI 对话会话记录" in content
    assert "归一化指令" in content
    assert "query_count" in content
    assert "AI 请求耗时" in content
    assert "动作统计" in content
    assert "来源统计" in content
    assert "重试上一条输入" in content
    assert "恢复建议" in content
    assert "/replaypickfail" in content
    assert "失败筛选来源" in content
    assert "replay_fail" in content
    assert "失败筛选关键字" in content
    assert "失败筛选当前轮次" in content
    assert "`7`" in content

    json_file = output_file.with_suffix(".json")
    assert json_file.exists()
    restored_log = ConversationLog.load_from_json(str(json_file))
    assert len(restored_log.turns) == 2
    assert restored_log.turns[1]["failed_selected_round_index"] == 7


def test_conversation_parser_prefers_json_companion(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    conversation_log = ConversationLog()
    conversation_log.log_turn(
        "查询柱子",
        command={"action": "query_count", "params": {"element_type": "column"}},
        result="当前模型中共有 1 个柱构件",
        action="query_count",
    )

    output_path = export_conversation_log(conversation_log, "AI对话会话")
    output_file = Path(output_path)
    output_file.write_text("# AI 对话会话记录\n\n损坏的 Markdown", encoding="utf-8")

    entries = _load_command_entries_from_latest_conversation_log()

    assert len(entries) == 1
    assert entries[0]["command"]["action"] == "query_count"


def test_conversation_parser_falls_back_to_markdown_when_json_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    conversation_log = ConversationLog()
    conversation_log.log_turn(
        "查询柱子",
        command={"action": "query_count", "params": {"element_type": "column"}},
        result="当前模型中共有 1 个柱构件",
        action="query_count",
    )

    output_path = export_conversation_log(conversation_log, "AI对话会话")
    output_file = Path(output_path)
    output_file.with_suffix(".json").unlink()

    entries = _load_command_entries_from_latest_conversation_log()

    assert len(entries) == 1
    assert entries[0]["command"]["action"] == "query_count"


def test_find_latest_output_path(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    older = Path(tmp_path) / "Documents" / "AI智建日志" / "AI对话会话-20240101-000000.md"
    newer = Path(tmp_path) / "Documents" / "AI智建日志" / "AI对话会话-20240101-000001.md"
    older.parent.mkdir(parents=True, exist_ok=True)
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")
    os.utime(str(older), (1, 1))
    os.utime(str(newer), (2, 2))

    latest = find_latest_output_path("AI对话会话", "md")

    assert latest == str(newer)
