# -*- coding: utf-8 -*-

import ai.replay as replay


class FakeOutput(object):
    def __init__(self):
        self.records = []

    def print_md(self, text):
        self.records.append(text)


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


def test_replay_last_command_returns_message_when_no_history():
    output = FakeOutput()
    levels = replay.replay_last_command(
        doc=None,
        output=output,
        levels=["L1"],
        operation_log=FakeOperationLog(),
        conversation_log=FakeConversationLog(),
        chat_state={},
    )

    assert levels == ["L1"]
    assert any(u"当前没有可重放的上一条指令" in text for text in output.records)


def test_replay_last_command_runs_success_flow(monkeypatch):
    output = FakeOutput()
    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = {
        "last_command": {"action": "query_count", "params": {"element_type": "column"}},
    }

    monkeypatch.setattr(
        replay,
        "execute_command",
        lambda doc, command, levels: ("当前模型中共有 3 个柱构件", ["new-levels"])
    )

    levels = replay.replay_last_command(
        doc="doc",
        output=output,
        levels=["old-levels"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
    )

    assert levels == ["new-levels"]
    assert operation_log.items == [("query_count", "当前模型中共有 3 个柱构件")]
    assert conversation_log.items[0]["source_kind"] == "replay"
    assert chat_state["last_result"] == "当前模型中共有 3 个柱构件"
    assert chat_state["last_action"] == "query_count"
    assert any("```json" in text for text in output.records)


def test_replay_last_command_from_log_returns_message_when_log_missing(monkeypatch):
    output = FakeOutput()
    monkeypatch.setattr(replay, "load_last_command_from_latest_conversation_log", lambda: None)

    levels = replay.replay_last_command_from_log(
        doc=None,
        output=output,
        levels=["L1"],
        operation_log=FakeOperationLog(),
        conversation_log=FakeConversationLog(),
        chat_state={},
    )

    assert levels == ["L1"]
    assert any(u"未找到可回放的最近会话文件" in text for text in output.records)


def test_replay_last_command_from_log_runs_success_flow(monkeypatch):
    output = FakeOutput()
    operation_log = FakeOperationLog()
    conversation_log = FakeConversationLog()
    chat_state = {}
    command = {"action": "create_beam", "params": {"floor": 2, "section": "300x600"}}

    monkeypatch.setattr(replay, "load_last_command_from_latest_conversation_log", lambda: command)
    monkeypatch.setattr(
        replay,
        "execute_command",
        lambda doc, command_arg, levels: ("已创建 300x600 梁", ["L1", "L2"])
    )

    levels = replay.replay_last_command_from_log(
        doc="doc",
        output=output,
        levels=["old"],
        operation_log=operation_log,
        conversation_log=conversation_log,
        chat_state=chat_state,
    )

    assert levels == ["L1", "L2"]
    assert chat_state["last_command"] == command
    assert operation_log.items == [("create_beam", "已创建 300x600 梁")]
    assert conversation_log.items[0]["source_kind"] == "replay_log"
    assert any(u"正在从最近一次会话文件重放上一条归一化指令" in text for text in output.records)
