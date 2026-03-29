# -*- coding: utf-8 -*-

from pathlib import Path

from ai import conversation_parser
from engine.logger import ConversationLog, export_conversation_log


def test_normalize_failed_filter_state_and_round_index():
    assert conversation_parser.normalize_failed_filter_state(
        source_filter_kind=" replay_fail ",
        action=" create_beam ",
        keyword=" 楼层 ",
    ) == {
        "source_filter_kind": "replay_fail",
        "action": "create_beam",
        "keyword": "楼层",
    }
    assert conversation_parser.normalize_failed_filter_state() is None
    assert conversation_parser.normalize_failed_selected_round_index("7") == 7
    assert conversation_parser.normalize_failed_selected_round_index("0") is None
    assert conversation_parser.normalize_failed_selected_round_index_from_entry({
        "failed_selected_round_index": "5",
    }) == 5


def test_extract_command_entries_from_markdown_parses_failed_metadata():
    content = """
## 第 1 轮 [2026-03-29 10:00:00]
- 动作：`query_count`
- 来源：普通 AI 对话
- 状态：成功

### 用户输入
```text
统计一下柱子数量
```

### 归一化指令
```json
{"action":"query_count","params":{"element_type":"column"}}
```

## 第 2 轮 [2026-03-29 10:01:00]
- 动作：`create_beam`
- 来源：从会话文件重放
- 状态：失败
- 失败筛选来源：`replay_fail`
- 失败筛选动作：`create_beam`
- 失败筛选关键字：`楼层`
- 失败筛选当前轮次：`8`

### 用户输入
```text
/replayfail 楼层
```

### 错误
```text
楼层超出范围，可用楼层为 1 到 3
```

### 恢复建议
```text
请按当前模型实际楼层范围重试。
```

### 归一化指令
```json
{"action":"create_beam","params":{"floor":9,"section":"300x600"}}
```
"""
    entries = conversation_parser.extract_command_entries_from_conversation_markdown(content)

    assert len(entries) == 2
    assert entries[0]["status"] == "success"
    assert entries[0]["command"]["action"] == "query_count"
    assert entries[1]["status"] == "failed"
    assert entries[1]["source_kind"] == "replay_log"
    assert entries[1]["failed_filter"] == {
        "source_filter_kind": "replay_fail",
        "action": "create_beam",
        "keyword": "楼层",
    }
    assert entries[1]["failed_selected_round_index"] == 8


def test_extract_last_command_from_legacy_markdown_format():
    content = """
### 归一化指令
```json
{"action":"create_column","params":{"x":0,"y":0}}
```

### 归一化指令
```json
{"action":"create_beam","params":{"floor":2}}
```
"""
    command = conversation_parser.extract_last_command_from_conversation_markdown(content)

    assert command["action"] == "create_beam"
    assert command["params"]["floor"] == 2


def test_load_failed_command_helpers_from_latest_log(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    conversation_log = ConversationLog()
    conversation_log.log_turn(
        "统计柱子",
        command={"action": "query_count", "params": {"element_type": "column"}},
        result="当前模型中共有 3 个柱构件",
        action="query_count",
        source_kind="user",
    )
    conversation_log.log_turn(
        "/replayfail 楼层",
        command={"action": "create_beam", "params": {"floor": 9, "section": "300x600"}},
        error="楼层超出范围，可用楼层为 1 到 3",
        recovery_suggestion="请按当前模型实际楼层范围重试。",
        action="create_beam",
        source_kind="replay_log",
        failed_filter={
            "source_filter_kind": "replay_fail",
            "action": "create_beam",
            "keyword": "楼层",
        },
        failed_selected_round_index=6,
    )

    output_path = export_conversation_log(conversation_log, "AI对话会话")
    assert Path(output_path).exists()

    entries = conversation_parser.load_command_entries_from_latest_conversation_log()
    assert len(entries) == 2
    assert conversation_parser.load_last_command_from_latest_conversation_log()["action"] == "create_beam"
    assert conversation_parser.load_last_failed_command_entry_from_latest_conversation_log()["action"] == "create_beam"
    assert conversation_parser.load_last_failed_filter_from_latest_conversation_log() == {
        "source_filter_kind": "replay_fail",
        "action": "create_beam",
        "keyword": "楼层",
    }
    assert conversation_parser.load_last_failed_selected_round_index_from_latest_conversation_log() == 6
    failed_entries = conversation_parser.load_failed_command_entries_from_latest_conversation_log()
    assert len(failed_entries) == 1
    assert failed_entries[0]["error_summary"] == "楼层超出范围，可用楼层为 1 到 3"


def test_classify_failed_entry_source_and_format_label():
    entry = {
        "user_input": "/retry 创建一根梁",
        "source_kind": "user",
    }

    assert conversation_parser.classify_failed_entry_source(entry) == "retry"
    assert conversation_parser.format_failed_entry_source_label(entry) == u"重试上一条输入失败"
