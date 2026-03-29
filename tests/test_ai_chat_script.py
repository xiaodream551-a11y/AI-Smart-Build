# -*- coding: utf-8 -*-

import pytest

from conftest import load_project_script
from tools.offline_runtime import FakeDocument, make_story_levels


chat_script = load_project_script(
    "ai_chat_script_for_tests",
    "AI智建.extension/AI智建.tab/AI对话.panel/智能对话.pushbutton/script.py",
)


def test_execute_command_uses_transaction_for_write_actions(monkeypatch):
    doc = FakeDocument(levels=make_story_levels(2))
    levels = ["old-levels"]
    records = []

    class FakeTransaction(object):
        def __init__(self, name):
            records.append(("init", name))
            self.name = name

        def __enter__(self):
            records.append(("enter", self.name))
            return self

        def __exit__(self, exc_type, exc, tb):
            records.append(("exit", self.name))
            return False

    monkeypatch.setattr(chat_script.revit, "Transaction", FakeTransaction)
    monkeypatch.setattr(
        chat_script.chat_common,
        "dispatch_command",
        lambda doc_arg, command_arg, levels_arg: "ok"
    )
    monkeypatch.setattr(
        chat_script.chat_common,
        "get_all_levels",
        lambda doc_arg: ["new-levels"]
    )

    result, new_levels = chat_script._execute_command(
        doc,
        {"action": "create_beam", "params": {}},
        levels
    )

    assert result == "ok"
    assert new_levels == ["new-levels"]
    assert records == [
        ("init", "AI智建：create_beam"),
        ("enter", "AI智建：create_beam"),
        ("exit", "AI智建：create_beam"),
    ]


def test_execute_command_skips_transaction_for_query_actions(monkeypatch):
    doc = FakeDocument(levels=make_story_levels(2))
    levels = ["old-levels"]

    monkeypatch.setattr(
        chat_script.revit,
        "Transaction",
        lambda name: (_ for _ in ()).throw(AssertionError("不应开启事务"))
    )
    monkeypatch.setattr(
        chat_script.chat_common,
        "dispatch_command",
        lambda doc_arg, command_arg, levels_arg: "count=1"
    )
    monkeypatch.setattr(
        chat_script.chat_common,
        "get_all_levels",
        lambda doc_arg: (_ for _ in ()).throw(AssertionError("不应刷新标高"))
    )

    result, new_levels = chat_script._execute_command(
        doc,
        {"action": "query_count", "params": {}},
        levels
    )

    assert result == "count=1"
    assert new_levels == levels


def test_handle_local_command_reset(monkeypatch):
    records = []
    chat_state = {
        "last_user_input": "old",
        "last_reply": "reply",
        "last_command": {"action": "query_count"},
        "last_result": "ok",
        "last_action": "query_count",
        "last_failed_filter": {"source_filter_kind": "user", "action": "create_beam", "keyword": "楼层"},
        "last_failed_selected_round_index": 8,
    }

    class FakeClient(object):
        def reset(self):
            records.append("reset")

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    handled, levels = chat_script._handle_local_command(
        "/reset",
        FakeOutput(),
        FakeClient(),
        levels=["x"],
        chat_state=chat_state,
    )

    assert handled is True
    assert levels == ["x"]
    assert records[0] == "reset"
    assert "已重置对话上下文" in records[1]
    assert chat_state["last_user_input"] is None
    assert chat_state["last_command"] is None
    assert chat_state["last_failed_filter"] is None
    assert chat_state["last_failed_selected_round_index"] is None


def test_format_user_error_for_parse_failure():
    message = chat_script._format_user_error(
        Exception("无法从回复中提取 JSON 指令：abc")
    )

    assert "无法解析为建模指令" in message
    assert "更明确的说法" in message


def test_build_recovery_suggestion_for_parse_failure():
    suggestion = chat_script._build_recovery_suggestion(
        "AI 回复无法解析为建模指令。\n建议换更明确的说法后重试，例如直接说明构件类型、楼层和尺寸；如果只是想重复执行上一条成功指令，可用 /replay。"
    )

    assert "第2层" in suggestion
    assert "300x600梁" in suggestion


@pytest.mark.parametrize(
    "result_text, expected",
    [
        ("楼层超出范围，可用楼层为 1 到 3", True),
        ("未找到可删除的梁", True),
        ("已创建 300x600 梁，从 (0,0) 到 (6000,0)，第 2 层", False),
        ("当前模型中共有 3 个柱构件", False),
    ]
)
def test_is_execution_failure_result(result_text, expected):
    assert chat_script._is_execution_failure_result(result_text) is expected


@pytest.mark.parametrize(
    "error_text, action, command, expected_text",
    [
        (
            "楼层超出范围，可用楼层为 1 到 3",
            "create_column",
            {"action": "create_column", "params": {"x": 0, "y": 0, "base_floor": 3, "top_floor": 6}},
            "base_floor/top_floor"
        ),
        (
            "缺少新截面参数",
            "modify_section",
            {"action": "modify_section", "params": {"element_type": "column", "floor": 2, "old_section": "400x400"}},
            "新截面"
        ),
        (
            "不支持查询的构件类型: wall",
            "query_count",
            {"action": "query_count", "params": {"element_type": "wall"}},
            "`column`、`beam`、`slab`"
        ),
    ]
)
def test_build_recovery_suggestion_for_action_specific_failures(
    error_text,
    action,
    command,
    expected_text
):
    suggestion = chat_script._build_recovery_suggestion(
        error_text,
        action=action,
        command=command,
    )

    assert expected_text in suggestion


def test_log_failed_turn_outputs_suggestion():
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    conversation_log = FakeConversationLog()

    chat_script._log_failed_turn(
        FakeOutput(),
        conversation_log,
        "创建一根梁",
        "执行失败：梁截面参数缺失",
        command={"action": "create_beam"},
        action="create_beam",
        source_kind="user",
    )

    assert any(text.startswith("**建议：**") for text in records)
    assert "recovery_suggestion" in conversation_log.items[0]
    assert "/replayfail" in conversation_log.items[0]["recovery_suggestion"]


def test_run_ai_turn_treats_failed_result_as_error(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeClient(object):
        def chat(self, user_input, timeout_ms=None):
            return '{"action":"create_beam","params":{"floor":9}}'

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.chat_controller,
        "parse_command",
        lambda reply: {"action": "create_beam", "params": {"floor": 9}}
    )
    monkeypatch.setattr(
        chat_script.chat_controller,
        "_execute_command",
        lambda doc, command, levels: ("楼层超出范围，可用楼层为 1 到 3", levels)
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = chat_script._build_chat_state()

    levels = chat_script._run_ai_turn(
        doc=None,
        output=FakeOutput(),
        client=FakeClient(),
        levels=["L1", "L2"],
        user_input="在第9层创建一根梁",
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
    )

    assert levels == ["L1", "L2"]
    assert operation_log.items == []
    assert conversation_log.items[0]["error"] == "楼层超出范围，可用楼层为 1 到 3"
    assert "故事层编号" in conversation_log.items[0]["recovery_suggestion"]
    assert any(text.startswith("**错误：**") for text in records)
    assert any(text.startswith("**建议：**") for text in records)
    assert chat_state["last_command"]["action"] == "create_beam"


def test_handle_local_command_retry_calls_helper(monkeypatch):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_retry_last_input",
        lambda doc, output, client, levels, operation_log, conversation_log, chat_state: (
            records.append(chat_state["last_user_input"]) or ["retried-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        "/retry",
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={"last_user_input": "上一条指令"},
    )

    assert handled is True
    assert levels == ["retried-levels"]
    assert records == ["上一条指令"]


def test_handle_local_command_replay_calls_helper(monkeypatch):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_replay_last_command",
        lambda doc, output, levels, operation_log, conversation_log, chat_state: (
            records.append(chat_state["last_command"]["action"]) or ["replayed-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        "/replay",
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={"last_command": {"action": "create_beam"}},
    )

    assert handled is True
    assert levels == ["replayed-levels"]
    assert records == ["create_beam"]


def test_handle_local_command_replaylog_calls_helper(monkeypatch):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_replay_last_command_from_log",
        lambda doc, output, levels, operation_log, conversation_log, chat_state: (
            records.append("replaylog") or ["file-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        "/replaylog",
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={},
    )

    assert handled is True
    assert levels == ["file-levels"]
    assert records == ["replaylog"]


def test_handle_local_command_replaypick_calls_helper(monkeypatch):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_replay_pick_command_from_log",
        lambda doc, output, levels, operation_log, conversation_log, chat_state: (
            records.append("replaypick") or ["picked-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        "/replaypick",
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={},
    )

    assert handled is True
    assert levels == ["picked-levels"]
    assert records == ["replaypick"]


def test_handle_local_command_replaypickfail_calls_helper(monkeypatch):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_replay_pick_failed_command_from_log",
        lambda doc, output, levels, operation_log, conversation_log, chat_state, filter_keyword=None, replay_user_input=None: (
            records.append(filter_keyword or "replaypickfail") or ["picked-failed-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        "/replaypickfail",
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={},
    )

    assert handled is True
    assert levels == ["picked-failed-levels"]
    assert records == ["replaypickfail"]


def test_handle_local_command_replaypickfail_passes_keyword(monkeypatch):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_replay_pick_failed_command_from_log",
        lambda doc, output, levels, operation_log, conversation_log, chat_state, filter_keyword=None, replay_user_input=None: (
            records.append(filter_keyword) or ["picked-failed-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        "/replaypickfail 楼层",
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={},
    )

    assert handled is True
    assert levels == ["picked-failed-levels"]
    assert records == ["楼层"]


def test_handle_local_command_replaypickfaillast_calls_helper(monkeypatch):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_replay_pick_failed_command_from_last_filter",
        lambda doc, output, levels, operation_log, conversation_log, chat_state: (
            records.append(chat_state["last_failed_filter"]["keyword"]) or ["picked-failed-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        "/replaypickfaillast",
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={
            "last_failed_filter": {"source_filter_kind": "user", "action": "create_beam", "keyword": "楼层"},
        },
    )

    assert handled is True
    assert levels == ["picked-failed-levels"]
    assert records == ["楼层"]


@pytest.mark.parametrize(
    "command_text,step",
    [
        ("/replaypickfailnext", 1),
        ("/replaypickfailprev", -1),
    ]
)
def test_handle_local_command_replaypickfail_navigation_calls_helper(monkeypatch, command_text, step):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_replay_adjacent_failed_command",
        lambda doc, output, levels, operation_log, conversation_log, chat_state, step=None: (
            records.append(step) or ["picked-failed-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        command_text,
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={},
    )

    assert handled is True
    assert levels == ["picked-failed-levels"]
    assert records == [step]


def test_handle_local_command_replayfail_calls_helper(monkeypatch):
    records = []

    monkeypatch.setattr(
        chat_script.chat_controller,
        "_replay_pick_failed_command_from_log",
        lambda doc, output, levels, operation_log, conversation_log, chat_state, filter_keyword=None, replay_user_input=None: (
            records.append(replay_user_input) or ["failed-levels"]
        )
    )

    handled, levels = chat_script._handle_local_command(
        "/replayfail",
        output=None,
        client=None,
        doc="doc",
        levels=["old-levels"],
        operation_log="oplog",
        conversation_log="convlog",
        chat_state={},
    )

    assert handled is True
    assert levels == ["failed-levels"]
    assert records == ["/replayfail"]


def test_retry_last_input_without_history():
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    levels = chat_script._retry_last_input(
        doc=None,
        output=FakeOutput(),
        client=None,
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state={},
    )

    assert levels == ["old-levels"]
    assert "没有可重试的上一条输入" in records[0]


def test_replay_last_command_without_history():
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    levels = chat_script._replay_last_command(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state={},
    )

    assert levels == ["old-levels"]
    assert "没有可重放的上一条指令" in records[0]


def test_extract_last_command_from_conversation_markdown():
    content = """
# AI 对话会话记录

### 归一化指令
```json
{"action":"query_count","params":{"element_type":"column"}}
```

### 归一化指令
```json
{"action":"create_beam","params":{"floor":2}}
```
"""

    command = chat_script._extract_last_command_from_conversation_markdown(content)

    assert command["action"] == "create_beam"
    assert command["params"]["floor"] == 2


def test_extract_command_entries_from_conversation_markdown():
    content = """
# AI 对话会话记录

## 第 1 轮 [10:00:00]

### 元信息
- 动作：`query_count`
- 来源：用户输入
- 状态：成功

### 用户输入
```text
统计柱子
```

### 归一化指令
```json
{"action":"query_count","params":{"element_type":"column"}}
```

## 第 2 轮 [10:00:02]

### 元信息
- 动作：`create_beam`
- 来源：从会话文件重放
- 失败筛选来源：`replay_fail`
- 失败筛选动作：`create_beam`
- 失败筛选关键字：`楼层`
- 失败筛选当前轮次：`7`
- 状态：失败

### 用户输入
```text
/replaylog
```

### 归一化指令
```json
{"action":"create_beam","params":{"floor":2}}
```

### 错误
```text
执行失败：梁截面参数缺失
请检查输入
```

### 恢复建议
```text
请补全梁截面、故事层编号后重试；修正后可用 /replayfail 直接复现。
```
"""

    entries = chat_script._extract_command_entries_from_conversation_markdown(content)

    assert len(entries) == 2
    assert entries[0]["round_index"] == 1
    assert entries[0]["source_kind"] == "user"
    assert entries[0]["status"] == "success"
    assert entries[1]["source_kind"] == "replay_log"
    assert entries[1]["status"] == "failed"
    assert entries[1]["error_summary"] == "执行失败：梁截面参数缺失"
    assert entries[1]["recovery_summary"] == "请补全梁截面、故事层编号后重试；修正后可用 /replayfail 直接复现。"
    assert entries[1]["failed_filter"] == {
        "source_filter_kind": "replay_fail",
        "action": "create_beam",
        "keyword": "楼层",
    }
    assert entries[1]["failed_selected_round_index"] == 7
    assert entries[1]["command"]["action"] == "create_beam"


def test_replay_last_command_from_log_without_file(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    monkeypatch.setattr(chat_script.replay, "_load_last_command_from_latest_conversation_log", lambda: None)

    levels = chat_script._replay_last_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state={},
    )

    assert levels == ["old-levels"]
    assert "未找到可回放的最近会话文件" in records[0]


def test_replay_pick_command_from_log_without_entries(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    monkeypatch.setattr(chat_script.replay, "_load_command_entries_from_latest_conversation_log", lambda: [])

    levels = chat_script._replay_pick_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state={},
    )

    assert levels == ["old-levels"]
    assert "最近一次会话文件中没有可选的回放指令" in records[0]


def test_replay_last_failed_command_from_log_without_entries(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_last_failed_command_entry_from_latest_conversation_log",
        lambda: None
    )

    levels = chat_script._replay_last_failed_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state={},
    )

    assert levels == ["old-levels"]
    assert "最近一次会话文件中没有可重放的失败指令" in records[0]


def test_replay_pick_failed_command_from_log_without_entries(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: []
    )

    levels = chat_script._replay_pick_failed_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state={},
    )

    assert levels == ["old-levels"]
    assert "最近一次会话文件中没有可选的失败指令" in records[0]


def test_select_failed_entries_by_action_without_filter():
    entries = [{
        "round_index": 2,
        "action": "create_beam",
        "command": {"action": "create_beam"},
    }]

    selected = chat_script._select_failed_entries_by_action(output=None, entries=entries)

    assert selected == entries


def test_classify_failed_entry_source_variants():
    assert chat_script._classify_failed_entry_source({
        "user_input": "创建一根梁",
        "source_kind": "user",
    }) == "user"
    assert chat_script._classify_failed_entry_source({
        "user_input": "/replaylog",
        "source_kind": "replay_log",
    }) == "replay_log"
    assert chat_script._classify_failed_entry_source({
        "user_input": "/replayfail",
        "source_kind": "replay_log",
    }) == "replay_fail"
    assert chat_script._classify_failed_entry_source({
        "user_input": "/replaypickfail",
        "source_kind": "replay_log",
    }) == "replay_pick_fail"


def test_select_failed_entries_by_source_without_filter():
    entries = [{
        "round_index": 2,
        "action": "create_beam",
        "source_kind": "user",
        "user_input": "创建梁",
        "command": {"action": "create_beam"},
    }]

    selected = chat_script._select_failed_entries_by_source(output=None, entries=entries)

    assert selected == entries


def test_select_failed_entries_by_source_cancel(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    monkeypatch.setattr(
        chat_script.forms.SelectFromList,
        "show",
        lambda options, **kwargs: None
    )

    selected = chat_script._select_failed_entries_by_source(
        FakeOutput(),
        [
            {"round_index": 2, "action": "create_beam", "source_kind": "user", "user_input": "创建梁"},
            {"round_index": 3, "action": "create_column", "source_kind": "replay_log", "user_input": "/replayfail"},
        ]
    )

    assert selected is None
    assert "已取消失败来源筛选" in records[0]


def test_select_failed_entries_by_action_cancel(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    monkeypatch.setattr(
        chat_script.forms.SelectFromList,
        "show",
        lambda options, **kwargs: None
    )

    selected = chat_script._select_failed_entries_by_action(
        FakeOutput(),
        [
            {"round_index": 2, "action": "create_beam", "command": {"action": "create_beam"}},
            {"round_index": 3, "action": "create_column", "command": {"action": "create_column"}},
        ]
    )

    assert selected is None
    assert "已取消失败动作筛选" in records[0]


def test_filter_failed_entries_by_source_kind_without_match(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    selected = chat_script._filter_failed_entries_by_source_kind(
        FakeOutput(),
        [{
            "round_index": 4,
            "source_kind": "user",
            "user_input": "创建梁",
        }],
        "replay_fail",
    )

    assert selected is None
    assert "没有匹配来源 `失败记录重放再次失败` 的失败指令" in records[0]


def test_filter_failed_entries_by_action_kind_without_match(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    selected = chat_script._filter_failed_entries_by_action_kind(
        FakeOutput(),
        [{
            "round_index": 4,
            "action": "create_beam",
        }],
        "create_column",
    )

    assert selected is None
    assert "没有匹配动作 `创建柱(create_column)` 的失败指令" in records[0]


@pytest.mark.parametrize(
    "filter_keyword,expected_round_indexes",
    [
        ("楼层", [5, 3]),
        ("截面", [4]),
    ]
)
def test_filter_failed_entries_by_keyword_matches_error_and_recovery_summary(
    filter_keyword,
    expected_round_indexes
):
    entries = [
        {
            "round_index": 3,
            "error_summary": "执行失败：楼层超出范围",
            "recovery_summary": "",
        },
        {
            "round_index": 4,
            "error_summary": "执行失败：梁截面参数缺失",
            "recovery_summary": "",
        },
        {
            "round_index": 5,
            "error_summary": "",
            "recovery_summary": "请先核对楼层编号后再试",
        },
    ]

    selected = chat_script._filter_failed_entries_by_keyword(
        output=None,
        entries=entries,
        filter_keyword=filter_keyword,
    )

    assert [entry["round_index"] for entry in selected] == expected_round_indexes


def test_filter_failed_entries_by_keyword_without_keyword_returns_sorted_entries():
    entries = [
        {"round_index": 2, "error_summary": "a"},
        {"round_index": 4, "error_summary": "b"},
    ]

    selected = chat_script._filter_failed_entries_by_keyword(
        output=None,
        entries=entries,
        filter_keyword="",
    )

    assert [entry["round_index"] for entry in selected] == [4, 2]


def test_filter_failed_entries_by_keyword_without_match(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    selected = chat_script._filter_failed_entries_by_keyword(
        output=FakeOutput(),
        entries=[{
            "round_index": 4,
            "error_summary": "执行失败：梁截面参数缺失",
            "recovery_summary": "请补全梁截面",
        }],
        filter_keyword="楼层",
    )

    assert selected is None
    assert "没有匹配关键字 `楼层` 的失败指令" in records[0]


def test_replay_pick_command_from_log_executes_selected_entry(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_command_entries_from_latest_conversation_log",
        lambda: [{
            "round_index": 3,
            "action": "create_beam",
            "source_kind": "user",
            "user_input": "创建梁",
            "command": {"action": "create_beam", "params": {"floor": 2}},
        }]
    )
    monkeypatch.setattr(
        chat_script.forms.SelectFromList,
        "show",
        lambda options, **kwargs: options[0]
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = {}

    levels = chat_script._replay_pick_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
    )

    assert levels == ["new-levels"]
    assert operation_log.items == [("create_beam", "ok")]
    assert conversation_log.items[0]["source_kind"] == "replay_log"
    assert chat_state["last_command"]["action"] == "create_beam"


def test_replay_pick_failed_command_from_log_executes_selected_entry(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: [{
            "round_index": 4,
            "action": "create_beam",
            "source_kind": "replay_log",
            "status": "failed",
            "user_input": "/replaylog",
            "error_summary": "执行失败：梁截面参数缺失",
            "command": {"action": "create_beam", "params": {"floor": 4}},
        }]
    )
    selection_calls = {"count": 0}

    def fake_select(options, **kwargs):
        selection_calls["count"] += 1
        if selection_calls["count"] == 1:
            return options[0]
        return options[0]

    monkeypatch.setattr(
        chat_script.forms.SelectFromList,
        "show",
        fake_select
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = {}

    levels = chat_script._replay_pick_failed_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
    )

    assert levels == ["new-levels"]
    assert any("正在重放选中的失败历史归一化指令" in text for text in records)
    assert operation_log.items == [("create_beam", "ok")]
    assert conversation_log.items[0]["source_kind"] == "replay_log"
    assert chat_state["last_command"]["action"] == "create_beam"


def test_replay_pick_failed_command_from_log_filters_by_selected_action(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 4,
                "action": "create_beam",
                "source_kind": "replay_log",
                "status": "failed",
                "user_input": "/replaylog",
                "error_summary": "执行失败：梁截面参数缺失",
                "command": {"action": "create_beam", "params": {"floor": 4}},
            },
            {
                "round_index": 5,
                "action": "create_column",
                "source_kind": "replay_log",
                "status": "failed",
                "user_input": "/replaylog",
                "error_summary": "执行失败：柱楼层范围无效",
                "command": {"action": "create_column", "params": {"base_floor": 3, "top_floor": 6}},
            },
        ]
    )

    selected_options = []

    def fake_select(options, **kwargs):
        selected_options.append([option.Name for option in options])
        title = kwargs.get("title")
        if title == "按动作筛选失败历史指令":
            return options[1]
        return options[0]

    monkeypatch.setattr(
        chat_script.forms.SelectFromList,
        "show",
        fake_select
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = {}

    levels = chat_script._replay_pick_failed_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
    )

    assert levels == ["new-levels"]
    assert any("创建柱(create_column) | 1 条" in name for name in selected_options[0])
    assert operation_log.items == [("create_column", "ok")]
    assert chat_state["last_command"]["action"] == "create_column"


def test_replay_pick_failed_command_from_log_filters_by_selected_source(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 4,
                "action": "create_beam",
                "source_kind": "user",
                "status": "failed",
                "user_input": "创建梁",
                "error_summary": "执行失败：梁截面参数缺失",
                "command": {"action": "create_beam", "params": {"floor": 4}},
            },
            {
                "round_index": 5,
                "action": "create_column",
                "source_kind": "replay_log",
                "status": "failed",
                "user_input": "/replayfail",
                "error_summary": "执行失败：柱楼层范围无效",
                "command": {"action": "create_column", "params": {"base_floor": 3, "top_floor": 6}},
            },
        ]
    )

    selected_options = []

    def fake_select(options, **kwargs):
        selected_options.append([option.Name for option in options])
        title = kwargs.get("title")
        if title == "按来源筛选失败历史指令":
            return options[1]
        return options[0]

    monkeypatch.setattr(
        chat_script.forms.SelectFromList,
        "show",
        fake_select
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = {}

    levels = chat_script._replay_pick_failed_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
    )

    assert levels == ["new-levels"]
    assert any("普通 AI 对话失败 | 1 条" in name for name in selected_options[0])
    assert any("失败记录重放再次失败 | 1 条" in name for name in selected_options[0])
    assert operation_log.items == [("create_column", "ok")]
    assert chat_state["last_command"]["action"] == "create_column"


def test_replay_pick_failed_command_from_log_filters_by_keyword(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 4,
                "action": "create_beam",
                "source_kind": "user",
                "status": "failed",
                "user_input": "创建梁",
                "error_summary": "执行失败：梁截面参数缺失",
                "command": {"action": "create_beam", "params": {"floor": 4}},
            },
            {
                "round_index": 5,
                "action": "create_beam",
                "source_kind": "user",
                "status": "failed",
                "user_input": "创建梁",
                "error_summary": "执行失败：楼层超出范围",
                "command": {"action": "create_beam", "params": {"floor": 6}},
            },
        ]
    )
    monkeypatch.setattr(
        chat_script.forms.SelectFromList,
        "show",
        lambda options, **kwargs: options[0]
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = {}

    levels = chat_script._replay_pick_failed_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
        filter_keyword="楼层",
    )

    assert levels == ["new-levels"]
    assert any("已按关键字 `楼层` 筛选到 1 条失败记录" in text for text in records)
    assert operation_log.items == [("create_beam", "ok")]
    assert chat_state["last_command"]["params"]["floor"] == 6
    assert chat_state["last_failed_selected_round_index"] == 5


def test_replay_pick_failed_command_from_log_remembers_selected_filters(monkeypatch):
    class FakeOutput(object):
        def print_md(self, text):
            pass

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 4,
                "action": "create_beam",
                "source_kind": "user",
                "status": "failed",
                "user_input": "创建梁",
                "error_summary": "执行失败：梁截面参数缺失",
                "command": {"action": "create_beam", "params": {"floor": 4}},
            },
            {
                "round_index": 5,
                "action": "create_column",
                "source_kind": "replay_log",
                "status": "failed",
                "user_input": "/replayfail",
                "error_summary": "执行失败：柱楼层范围无效",
                "command": {"action": "create_column", "params": {"base_floor": 3, "top_floor": 6}},
            },
        ]
    )

    def fake_select(options, **kwargs):
        title = kwargs.get("title")
        if title == "按来源筛选失败历史指令":
            return options[1]
        if title == "按动作筛选失败历史指令":
            return options[1]
        return options[0]

    monkeypatch.setattr(chat_script.forms.SelectFromList, "show", fake_select)
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = chat_script._build_chat_state()

    levels = chat_script._replay_pick_failed_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
        filter_keyword="楼层",
    )

    assert levels == ["new-levels"]
    assert chat_state["last_failed_filter"] == {
        "source_filter_kind": "replay_fail",
        "action": "create_column",
        "keyword": "楼层",
    }


def test_replay_pick_failed_command_from_last_filter_without_saved_state():
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    levels = chat_script._replay_pick_failed_command_from_last_filter(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state=chat_script._build_chat_state(),
    )

    assert levels == ["old-levels"]
    assert "当前没有可复用的失败筛选条件" in records[0]


def test_replay_adjacent_failed_command_without_state():
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    levels = chat_script._replay_adjacent_failed_command(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state=chat_script._build_chat_state(),
        step=1,
    )

    assert levels == ["old-levels"]
    assert "当前没有可连续浏览的失败结果" in records[0]


def test_replay_adjacent_failed_command_hits_boundary():
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    chat_state = chat_script._build_chat_state()
    chat_state["last_failed_filter"] = {
        "source_filter_kind": "user",
        "action": "create_beam",
        "keyword": "楼层",
    }
    chat_state["last_failed_selected_round_index"] = 5
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: [{
            "round_index": 5,
            "action": "create_beam",
            "source_kind": "user",
            "status": "failed",
            "user_input": "创建梁",
            "error_summary": "执行失败：楼层超出范围",
            "recovery_summary": "请先核对楼层编号后再试",
            "command": {"action": "create_beam", "params": {"floor": 6}},
        }]
    )

    try:
        levels = chat_script._replay_adjacent_failed_command(
            doc=None,
            output=FakeOutput(),
            levels=["old-levels"],
            operation_log=None,
            conversation_log=None,
            chat_state=chat_state,
            step=-1,
        )
    finally:
        monkeypatch.undo()

    assert levels == ["old-levels"]
    assert "已经是当前失败筛选结果中的第一条记录" in records[0]


def test_replay_adjacent_failed_command_executes_next_entry(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 5,
                "action": "create_beam",
                "source_kind": "user",
                "status": "failed",
                "user_input": "创建梁",
                "error_summary": "执行失败：楼层超出范围",
                "recovery_summary": "请先核对楼层编号后再试",
                "command": {"action": "create_beam", "params": {"floor": 6}},
            },
            {
                "round_index": 3,
                "action": "create_beam",
                "source_kind": "user",
                "status": "failed",
                "user_input": "创建梁",
                "error_summary": "执行失败：楼层参数无效",
                "recovery_summary": "请先核对楼层编号后再试",
                "command": {"action": "create_beam", "params": {"floor": 5}},
            },
        ]
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = chat_script._build_chat_state()
    chat_state["last_failed_filter"] = {
        "source_filter_kind": "user",
        "action": "create_beam",
        "keyword": "楼层",
    }
    chat_state["last_failed_selected_round_index"] = 5

    levels = chat_script._replay_adjacent_failed_command(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
        step=1,
    )

    assert levels == ["new-levels"]
    assert any("正在重放当前失败筛选结果中的下一条记录（第 3 轮）" in text for text in records)
    assert operation_log.items == [("create_beam", "ok")]
    assert chat_state["last_failed_selected_round_index"] == 3
    assert conversation_log.items[0]["failed_filter"] == {
        "source_filter_kind": "user",
        "action": "create_beam",
        "keyword": "楼层",
    }

def test_load_last_failed_filter_from_latest_conversation_log(monkeypatch):
    monkeypatch.setattr(
        chat_script.conversation_parser,
        "_load_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 1,
                "failed_filter": None,
            },
            {
                "round_index": 2,
                "failed_filter": {
                    "source_filter_kind": "replay_fail",
                    "action": "create_column",
                    "keyword": "楼层",
                },
            },
        ]
    )

    failed_filter = chat_script._load_last_failed_filter_from_latest_conversation_log()

    assert failed_filter == {
        "source_filter_kind": "replay_fail",
        "action": "create_column",
        "keyword": "楼层",
    }


def test_load_last_failed_selected_round_index_from_latest_conversation_log(monkeypatch):
    monkeypatch.setattr(
        chat_script.conversation_parser,
        "_load_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 1,
                "failed_selected_round_index": None,
            },
            {
                "round_index": 2,
                "failed_selected_round_index": 7,
            },
        ]
    )

    selected_round_index = chat_script._load_last_failed_selected_round_index_from_latest_conversation_log()

    assert selected_round_index == 7


def test_replay_pick_failed_command_from_last_filter_restores_from_latest_log(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_last_failed_filter_from_latest_conversation_log",
        lambda: {
            "source_filter_kind": "replay_fail",
            "action": "create_column",
            "keyword": "楼层",
        }
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_replay_pick_failed_command_from_log",
        lambda doc, output, levels, operation_log, conversation_log, chat_state, filter_keyword=None, source_filter_kind=None, action_filter=None, replay_user_input=None: (
            records.append((filter_keyword, source_filter_kind, action_filter, replay_user_input)) or ["new-levels"]
        )
    )

    chat_state = chat_script._build_chat_state()

    levels = chat_script._replay_pick_failed_command_from_last_filter(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state=chat_state,
    )

    assert levels == ["new-levels"]
    assert "当前会话没有筛选缓存，已从最近一次会话文件恢复失败筛选条件" in records[0]
    assert "正在复用上次失败筛选条件" in records[2]
    assert records[4] == ("楼层", "replay_fail", "create_column", "/replayfail")
    assert chat_state["last_failed_filter"] == {
        "source_filter_kind": "replay_fail",
        "action": "create_column",
        "keyword": "楼层",
    }


def test_replay_adjacent_failed_command_restores_state_from_latest_log(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_last_failed_filter_from_latest_conversation_log",
        lambda: {
            "source_filter_kind": "user",
            "action": "create_beam",
            "keyword": "楼层",
        }
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_load_last_failed_selected_round_index_from_latest_conversation_log",
        lambda: 5
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_load_failed_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 5,
                "action": "create_beam",
                "source_kind": "user",
                "status": "failed",
                "user_input": "创建梁",
                "error_summary": "执行失败：楼层超出范围",
                "recovery_summary": "请先核对楼层编号后再试",
                "command": {"action": "create_beam", "params": {"floor": 6}},
            },
            {
                "round_index": 3,
                "action": "create_beam",
                "source_kind": "user",
                "status": "failed",
                "user_input": "创建梁",
                "error_summary": "执行失败：楼层参数无效",
                "recovery_summary": "请先核对楼层编号后再试",
                "command": {"action": "create_beam", "params": {"floor": 5}},
            },
        ]
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = chat_script._build_chat_state()

    levels = chat_script._replay_adjacent_failed_command(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
        step=1,
    )

    assert levels == ["new-levels"]
    assert any("当前会话没有连续浏览定位，已从最近一次会话文件恢复" in text for text in records)
    assert any("正在重放当前失败筛选结果中的下一条记录（第 3 轮）" in text for text in records)
    assert chat_state["last_failed_filter"] == {
        "source_filter_kind": "user",
        "action": "create_beam",
        "keyword": "楼层",
    }
    assert chat_state["last_failed_selected_round_index"] == 3
    assert conversation_log.items[0]["failed_selected_round_index"] == 3


def test_replay_pick_failed_command_from_last_filter_reuses_saved_filters(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    monkeypatch.setattr(
        chat_script.replay,
        "_replay_pick_failed_command_from_log",
        lambda doc, output, levels, operation_log, conversation_log, chat_state, filter_keyword=None, source_filter_kind=None, action_filter=None, replay_user_input=None: (
            records.append((filter_keyword, source_filter_kind, action_filter, replay_user_input)) or ["new-levels"]
        )
    )

    chat_state = chat_script._build_chat_state()
    chat_state["last_failed_filter"] = {
        "source_filter_kind": "replay_fail",
        "action": "create_column",
        "keyword": "楼层",
    }

    levels = chat_script._replay_pick_failed_command_from_last_filter(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=None,
        conversation_log=None,
        chat_state=chat_state,
    )

    assert levels == ["new-levels"]
    assert "正在复用上次失败筛选条件" in records[0]
    assert records[2] == ("楼层", "replay_fail", "create_column", "/replayfail")


def test_load_last_failed_command_entry_from_latest_conversation_log(monkeypatch):
    monkeypatch.setattr(
        chat_script.conversation_parser,
        "_load_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 1,
                "status": "success",
                "command": {"action": "query_count"},
            },
            {
                "round_index": 2,
                "status": "failed",
                "command": {"action": "create_column"},
            },
            {
                "round_index": 3,
                "status": "failed",
                "command": {"action": "create_beam"},
            },
        ]
    )

    entry = chat_script._load_last_failed_command_entry_from_latest_conversation_log()

    assert entry["round_index"] == 3
    assert entry["command"]["action"] == "create_beam"


def test_load_failed_command_entries_from_latest_conversation_log(monkeypatch):
    monkeypatch.setattr(
        chat_script.conversation_parser,
        "_load_command_entries_from_latest_conversation_log",
        lambda: [
            {
                "round_index": 1,
                "status": "success",
                "command": {"action": "query_count"},
            },
            {
                "round_index": 2,
                "status": "failed",
                "command": {"action": "create_column"},
            },
            {
                "round_index": 3,
                "status": "failed",
                "command": {"action": "create_beam"},
            },
        ]
    )

    entries = chat_script._load_failed_command_entries_from_latest_conversation_log()

    assert [entry["round_index"] for entry in entries] == [2, 3]


def test_group_entries_by_action_sorts_entries_within_group_by_recency():
    groups = chat_script._group_entries_by_action([
        {"round_index": 1, "action": "create_beam"},
        {"round_index": 2, "action": "create_column"},
        {"round_index": 3, "action": "create_beam"},
    ])

    assert [group[0] for group in groups] == ["create_beam", "create_column"]
    assert [entry["round_index"] for entry in groups[0][1]] == [3, 1]


def test_group_entries_by_action_sorts_groups_by_latest_round():
    groups = chat_script._group_entries_by_action([
        {"round_index": 4, "action": "create_beam"},
        {"round_index": 6, "action": "create_column"},
        {"round_index": 5, "action": "modify_section"},
    ])

    assert [group[0] for group in groups] == [
        "create_column",
        "modify_section",
        "create_beam",
    ]


def test_group_entries_by_failed_source_sorts_by_latest_round():
    groups = chat_script._group_entries_by_failed_source([
        {"round_index": 4, "source_kind": "user", "user_input": "创建梁"},
        {"round_index": 6, "source_kind": "replay_log", "user_input": "/replayfail"},
        {"round_index": 5, "source_kind": "replay_log", "user_input": "/replaylog"},
    ])

    assert [group[0] for group in groups] == [
        "replay_fail",
        "replay_log",
        "user",
    ]


def test_replay_last_failed_command_from_log_executes_latest_failure(monkeypatch):
    records = []

    class FakeOutput(object):
        def print_md(self, text):
            records.append(text)

    class FakeOperationLog(object):
        def __init__(self):
            self.items = []

        def log(self, action, result):
            self.items.append((action, result))

    class FakeConversationLog(object):
        def __init__(self):
            self.items = []

        def log_turn(self, *args, **kwargs):
            self.items.append(kwargs)

    monkeypatch.setattr(
        chat_script.replay,
        "_load_last_failed_command_entry_from_latest_conversation_log",
        lambda: {
            "round_index": 4,
            "status": "failed",
            "command": {"action": "create_beam", "params": {"floor": 3}},
        }
    )
    monkeypatch.setattr(
        chat_script.replay,
        "_execute_command",
        lambda doc, command, levels: ("ok", ["new-levels"])
    )

    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = {}

    levels = chat_script._replay_last_failed_command_from_log(
        doc=None,
        output=FakeOutput(),
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
    )

    assert levels == ["new-levels"]
    assert any("第 4 轮" in text for text in records)
    assert operation_log.items == [("create_beam", "ok")]
    assert conversation_log.items[0]["source_kind"] == "replay_log"
    assert chat_state["last_command"]["action"] == "create_beam"


def test_replay_command_option_shows_failed_error_summary():
    option = chat_script.ReplayCommandOption({
        "round_index": 5,
        "action": "create_beam",
        "source_kind": "replay_log",
        "status": "failed",
        "user_input": "重放一条因为梁截面缺失而失败的命令",
        "error_summary": "执行失败：梁截面参数缺失",
        "recovery_summary": "请补全梁截面和楼层参数后重试",
    })

    assert "第 5 轮" in option.Name
    assert "失败" in option.Name
    assert "创建梁(create_beam)" in option.Name
    assert "最近会话重放失败" in option.Name
    assert "执行失败：梁截面参数缺失" in option.Name
    assert "建议: 请补全梁截面和楼层参数后重试" in option.Name
