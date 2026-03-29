# -*- coding: utf-8 -*-
"""AI 对话会话日志解析与加载。"""

import io
import json
import os
import re

from engine.logger import ConversationLog, SOURCE_LABELS as LOGGER_SOURCE_LABELS, find_latest_output_path
from ai.recovery import (
    normalize_status_label,
    summarize_error_text,
    summarize_recovery_text,
)


SOURCE_LABELS = dict(LOGGER_SOURCE_LABELS)

FAILED_SOURCE_FILTER_LABELS = {
    "user": u"普通 AI 对话失败",
    "retry": u"重试上一条输入失败",
    "replay": u"重放上一条指令失败",
    "replay_log": u"最近会话重放失败",
    "replay_pick": u"按轮次重放失败",
    "replay_fail": u"失败记录重放再次失败",
    "replay_pick_fail": u"按失败轮次重放再次失败",
}


def normalize_failed_filter_state(source_filter_kind=None, action=None, keyword=None):
    normalized_source_filter_kind = (source_filter_kind or "").strip() or None
    normalized_action = (action or "").strip() or None
    normalized_keyword = (keyword or "").strip() or None
    if not (normalized_source_filter_kind or normalized_action or normalized_keyword):
        return None

    return {
        "source_filter_kind": normalized_source_filter_kind,
        "action": normalized_action,
        "keyword": normalized_keyword,
    }


def load_last_command_from_latest_conversation_log():
    entries = load_command_entries_from_latest_conversation_log()
    if not entries:
        return None
    return entries[-1].get("command")


def extract_last_command_from_conversation_markdown(content):
    entries = extract_command_entries_from_conversation_markdown(content)
    if not entries:
        return None
    return entries[-1].get("command")


def load_command_entries_from_latest_conversation_log():
    latest_md_path = find_latest_output_path(u"AI对话会话", "md")
    if latest_md_path:
        latest_json_path = os.path.splitext(latest_md_path)[0] + ".json"
        if os.path.exists(latest_json_path):
            return _load_command_entries_from_conversation_json(latest_json_path)
        with io.open(latest_md_path, "r", encoding="utf-8") as input_file:
            content = input_file.read()
        return extract_command_entries_from_conversation_markdown(content)

    latest_json_path = find_latest_output_path(u"AI对话会话", "json")
    if latest_json_path:
        return _load_command_entries_from_conversation_json(latest_json_path)
    return []


def load_last_failed_command_entry_from_latest_conversation_log():
    entries = load_command_entries_from_latest_conversation_log()
    for entry in reversed(entries):
        if entry.get("status") == "failed" and entry.get("command"):
            return entry
    return None


def load_last_failed_filter_from_latest_conversation_log():
    entries = load_command_entries_from_latest_conversation_log()
    for entry in reversed(entries):
        failed_filter = _normalize_failed_filter_from_entry(entry)
        if failed_filter:
            return failed_filter
    return None


def load_last_failed_selected_round_index_from_latest_conversation_log():
    entries = load_command_entries_from_latest_conversation_log()
    for entry in reversed(entries):
        round_index = normalize_failed_selected_round_index_from_entry(entry)
        if round_index is not None:
            return round_index
    return None


def load_failed_command_entries_from_latest_conversation_log():
    entries = load_command_entries_from_latest_conversation_log()
    return [
        entry for entry in entries
        if entry.get("status") == "failed" and entry.get("command")
    ]


def _load_command_entries_from_conversation_json(filepath):
    conversation_log = ConversationLog.load_from_json(filepath)
    return _build_entries_from_turns(conversation_log.turns)


def _build_entries_from_turns(turns):
    entries = []
    for round_index, turn in enumerate(turns or [], start=1):
        entries.append(_build_entry_from_turn(round_index, turn))
    return entries


def _build_entry_from_turn(round_index, turn):
    error_text = (turn.get("error") or "").strip()
    recovery_text = (turn.get("recovery_suggestion") or "").strip()
    command = turn.get("command")
    return {
        "round_index": int(round_index),
        "action": (turn.get("action") or (command or {}).get("action") or "").strip(),
        "source_kind": (turn.get("source_kind") or "user").strip() or "user",
        "status": "failed" if error_text else "success",
        "user_input": turn.get("user_input") or "",
        "error": error_text,
        "error_summary": summarize_error_text(error_text),
        "recovery_suggestion": recovery_text,
        "recovery_summary": summarize_recovery_text(recovery_text),
        "failed_filter": _normalize_failed_filter_from_entry(turn),
        "failed_selected_round_index": normalize_failed_selected_round_index_from_entry(turn),
        "command": command if isinstance(command, dict) else None,
    }


def extract_command_entries_from_conversation_markdown(content):
    sections = re.findall(
        r"## 第 (\d+) 轮 \[(.*?)\](.*?)(?=\n## 第 \d+ 轮 \[|\Z)",
        content or "",
        re.DOTALL
    )
    entries = []

    if not sections:
        matches = re.findall(
            r"### 归一化指令\s*```json\s*(.*?)\s*```",
            content or "",
            re.DOTALL
        )
        for index, raw_command in enumerate(matches, start=1):
            try:
                command = json.loads(raw_command.strip())
            except Exception:
                continue
            entries.append(_build_entry_from_turn(index, {
                "action": command.get("action", ""),
                "source_kind": "user",
                "user_input": "",
                "error": "",
                "recovery_suggestion": "",
                "failed_filter": None,
                "failed_selected_round_index": None,
                "command": command,
            }))
        return entries

    for round_index, _timestamp, body in sections:
        command_match = re.search(
            r"### 归一化指令\s*```json\s*(.*?)\s*```",
            body,
            re.DOTALL
        )
        if not command_match:
            continue

        try:
            command = json.loads(command_match.group(1).strip())
        except Exception:
            continue

        action_match = re.search(r"- 动作：`([^`]+)`", body)
        source_match = re.search(r"- 来源：([^\n]+)", body)
        status_match = re.search(r"- 状态：([^\n]+)", body)
        user_input_match = re.search(
            r"### 用户输入\s*```text\s*(.*?)\s*```",
            body,
            re.DOTALL
        )
        error_match = re.search(
            r"### 错误\s*```text\s*(.*?)\s*```",
            body,
            re.DOTALL
        )
        recovery_match = re.search(
            r"### 恢复建议\s*```text\s*(.*?)\s*```",
            body,
            re.DOTALL
        )
        failed_filter_source_match = re.search(r"- 失败筛选来源：`([^`]+)`", body)
        failed_filter_action_match = re.search(r"- 失败筛选动作：`([^`]+)`", body)
        failed_filter_keyword_match = re.search(r"- 失败筛选关键字：`([^`]+)`", body)
        failed_selected_round_index_match = re.search(r"- 失败筛选当前轮次：`([^`]+)`", body)
        status = normalize_status_label(
            status_match.group(1).strip() if status_match else ""
        )
        error_text = error_match.group(1).strip() if error_match else ""
        if status == "failed" and not error_text:
            error_text = u"执行失败"

        entries.append(_build_entry_from_turn(int(round_index), {
            "action": action_match.group(1).strip() if action_match else command.get("action", ""),
            "source_kind": _normalize_source_label_to_kind(
                source_match.group(1).strip() if source_match else ""
            ),
            "user_input": user_input_match.group(1).strip() if user_input_match else "",
            "error": error_text,
            "recovery_suggestion": recovery_match.group(1).strip() if recovery_match else "",
            "failed_filter": normalize_failed_filter_state(
                source_filter_kind=failed_filter_source_match.group(1).strip()
                if failed_filter_source_match else "",
                action=failed_filter_action_match.group(1).strip()
                if failed_filter_action_match else "",
                keyword=failed_filter_keyword_match.group(1).strip()
                if failed_filter_keyword_match else "",
            ),
            "failed_selected_round_index": normalize_failed_selected_round_index(
                failed_selected_round_index_match.group(1).strip()
                if failed_selected_round_index_match else ""
            ),
            "command": command,
        }))

    return entries


def _normalize_source_label_to_kind(label):
    text = (label or "").strip()
    for source_kind, source_label in SOURCE_LABELS.items():
        if source_label == text:
            return source_kind
    return "user"


def _normalize_failed_filter_from_entry(entry):
    if not isinstance(entry, dict):
        return None

    failed_filter = entry.get("failed_filter")
    if isinstance(failed_filter, dict):
        normalized = normalize_failed_filter_state(
            source_filter_kind=failed_filter.get("source_filter_kind"),
            action=failed_filter.get("action"),
            keyword=failed_filter.get("keyword"),
        )
        if normalized:
            return normalized

    return normalize_failed_filter_state(
        source_filter_kind=entry.get("failed_filter_source_kind"),
        action=entry.get("failed_filter_action"),
        keyword=entry.get("failed_filter_keyword"),
    )


def normalize_failed_selected_round_index(value):
    if value in (None, ""):
        return None
    try:
        round_index = int(value)
    except (TypeError, ValueError):
        return None
    if round_index <= 0:
        return None
    return round_index


def normalize_failed_selected_round_index_from_entry(entry):
    if not isinstance(entry, dict):
        return None
    return normalize_failed_selected_round_index(
        entry.get("failed_selected_round_index")
    )


def classify_failed_entry_source(entry):
    user_input = (entry.get("user_input") or "").strip().lower()
    source_kind = (entry.get("source_kind") or "").strip()

    if user_input.startswith("/replaypickfail"):
        return "replay_pick_fail"
    if user_input.startswith("/replayfail"):
        return "replay_fail"
    if user_input.startswith("/replaypick"):
        return "replay_pick"
    if user_input.startswith("/replaylog"):
        return "replay_log"
    if user_input.startswith("/replay"):
        return "replay"
    if user_input.startswith("/retry"):
        return "retry"

    if source_kind in FAILED_SOURCE_FILTER_LABELS:
        return source_kind
    return "user"


def format_failed_entry_source_label(entry):
    source_filter_kind = classify_failed_entry_source(entry)
    label = FAILED_SOURCE_FILTER_LABELS.get(source_filter_kind)
    if label:
        return label
    source_kind = entry.get("source_kind") or "user"
    return SOURCE_LABELS.get(source_kind, source_kind)
