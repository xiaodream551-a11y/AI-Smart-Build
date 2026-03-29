# -*- coding: utf-8 -*-
"""AI chat history replay and failed-command filtering."""

from pyrevit import forms

from ai.chat_common import (
    execute_command,
    format_command_text,
    print_system_message,
    shorten_text,
)
from ai.conversation_parser import (
    FAILED_SOURCE_FILTER_LABELS,
    SOURCE_LABELS,
    classify_failed_entry_source,
    format_failed_entry_source_label,
    load_command_entries_from_latest_conversation_log,
    load_failed_command_entries_from_latest_conversation_log,
    load_last_command_from_latest_conversation_log,
    load_last_failed_command_entry_from_latest_conversation_log,
    load_last_failed_filter_from_latest_conversation_log,
    load_last_failed_selected_round_index_from_latest_conversation_log,
    normalize_failed_filter_state,
    normalize_failed_selected_round_index,
)
from ai.recovery import (
    format_action_label,
    format_status_label,
    format_user_error,
    is_execution_failure_result,
    log_failed_turn,
)


class ReplayCommandOption(object):
    """Option entry for the session replay picker."""

    def __init__(self, entry):
        self.entry = entry
        action = entry.get("action") or u"unknown"
        status = entry.get("status") or ""
        user_input = (entry.get("user_input") or u"").replace("\n", " ").strip()
        status_label = format_status_label(status)
        error_summary = shorten_text(entry.get("error_summary") or u"", limit=28)
        recovery_summary = shorten_text(entry.get("recovery_summary") or u"", limit=24)
        user_input = shorten_text(user_input, limit=24)

        name_parts = [
            u"第 {round_index} 轮".format(round_index=entry.get("round_index", "?")),
            status_label,
            format_action_label(action),
            format_failed_entry_source_label(entry),
            user_input or u"<空>",
        ]
        if status == "failed" and error_summary:
            name_parts.append(error_summary)
        if status == "failed" and recovery_summary:
            name_parts.append(u"建议: " + recovery_summary)
        self.Name = u" | ".join(name_parts)
        self.Description = u"第 {round_index} 轮 | {action} | {source} | {user_input}".format(
            round_index=entry.get("round_index", "?"),
            action=format_action_label(action),
            source=format_failed_entry_source_label(entry),
            user_input=user_input or u"<空>",
        )


class ReplayActionFilterOption(object):
    """Filter option for replaying failed commands by action type."""

    def __init__(self, action, entries):
        self.action = action
        self.entries = entries or []
        if action:
            self.Name = u"{action} | {count} 条".format(
                action=format_action_label(action),
                count=len(self.entries)
            )
        else:
            self.Name = u"全部动作 | {count} 条".format(count=len(self.entries))


class ReplaySourceFilterOption(object):
    """Filter option for replaying failed commands by source kind."""

    def __init__(self, source_filter_kind, entries):
        self.source_filter_kind = source_filter_kind
        self.entries = entries or []
        if source_filter_kind:
            self.Name = u"{source} | {count} 条".format(
                source=FAILED_SOURCE_FILTER_LABELS.get(
                    source_filter_kind,
                    source_filter_kind
                ),
                count=len(self.entries)
            )
        else:
            self.Name = u"全部来源 | {count} 条".format(count=len(self.entries))


class ReplayNavigationOption(object):
    """Navigation option for stepping to the previous/next failed entry."""

    def __init__(self, direction, entry):
        self.direction = direction
        self.entry = entry
        direction_label = u"上一条" if direction == "prev" else u"下一条"
        round_index = entry.get("round_index", "?")
        action = format_action_label(entry.get("action") or "unknown")
        source = format_failed_entry_source_label(entry)
        self.Name = u"{direction} | 第 {round_index} 轮 | {action} | {source}".format(
            direction=direction_label,
            round_index=round_index,
            action=action,
            source=source,
        )


def _remember_last_failed_filter(chat_state, source_filter_kind=None, action=None, keyword=None):
    if not isinstance(chat_state, dict):
        return

    failed_filter = normalize_failed_filter_state(
        source_filter_kind=source_filter_kind,
        action=action,
        keyword=keyword,
    )
    if failed_filter:
        chat_state["last_failed_filter"] = failed_filter


def _remember_last_failed_selected_round_index(chat_state, round_index):
    if not isinstance(chat_state, dict):
        return
    chat_state["last_failed_selected_round_index"] = normalize_failed_selected_round_index(round_index)


def _get_last_failed_selected_round_index(chat_state):
    if not isinstance(chat_state, dict):
        return None
    return normalize_failed_selected_round_index(
        chat_state.get("last_failed_selected_round_index")
    )


def _get_last_failed_filter(chat_state):
    if not isinstance(chat_state, dict):
        return None

    filter_state = chat_state.get("last_failed_filter")
    if not isinstance(filter_state, dict):
        return None

    return normalize_failed_filter_state(
        source_filter_kind=filter_state.get("source_filter_kind"),
        action=filter_state.get("action"),
        keyword=filter_state.get("keyword"),
    )


def replay_last_command(
    doc,
    output,
    levels,
    operation_log,
    conversation_log,
    chat_state
):
    last_command = (chat_state or {}).get("last_command")
    if not last_command:
        print_system_message(output, u"当前没有可重放的上一条指令。")
        return levels

    action = last_command.get("action", "unknown")
    print_system_message(output, u"正在重放上一条归一化指令。")
    output.print_md("```json\n{}\n```".format(format_command_text(last_command)))

    try:
        result, levels = execute_command(doc, last_command, levels)
        if is_execution_failure_result(result):
            log_failed_turn(
                output,
                conversation_log,
                "/replay",
                result,
                command=last_command,
                action=action,
                source_kind="replay",
            )
            return levels

        operation_log.log(action, result)
        conversation_log.log_turn(
            "/replay",
            command=last_command,
            result=result,
            action=action,
            source_kind="replay",
        )
        output.print_md(u"**执行结果：** " + result)
        output.print_md("---")
        chat_state["last_result"] = result
        chat_state["last_action"] = action
        return levels

    except Exception as err:
        error_text = format_user_error(err)
        log_failed_turn(
            output,
            conversation_log,
            "/replay",
            error_text,
            command=last_command,
            action=action,
            source_kind="replay",
        )
        return levels


def replay_last_command_from_log(
    doc,
    output,
    levels,
    operation_log,
    conversation_log,
    chat_state
):
    command = load_last_command_from_latest_conversation_log()
    if not command:
        print_system_message(output, u"未找到可回放的最近会话文件。")
        return levels

    chat_state["last_command"] = command
    action = command.get("action", "unknown")
    print_system_message(output, u"正在从最近一次会话文件重放上一条归一化指令。")
    output.print_md("```json\n{}\n```".format(format_command_text(command)))

    try:
        result, levels = execute_command(doc, command, levels)
        if is_execution_failure_result(result):
            log_failed_turn(
                output,
                conversation_log,
                "/replaylog",
                result,
                command=command,
                action=action,
                source_kind="replay_log",
            )
            return levels

        operation_log.log(action, result)
        conversation_log.log_turn(
            "/replaylog",
            command=command,
            result=result,
            action=action,
            source_kind="replay_log",
        )
        output.print_md(u"**执行结果：** " + result)
        output.print_md("---")
        chat_state["last_result"] = result
        chat_state["last_action"] = action
        return levels
    except Exception as err:
        error_text = format_user_error(err)
        log_failed_turn(
            output,
            conversation_log,
            "/replaylog",
            error_text,
            command=command,
            action=action,
            source_kind="replay_log",
        )
        return levels


def replay_pick_command_from_log(
    doc,
    output,
    levels,
    operation_log,
    conversation_log,
    chat_state
):
    entries = load_command_entries_from_latest_conversation_log()
    if not entries:
        print_system_message(output, u"最近一次会话文件中没有可选的回放指令。")
        return levels

    options = [ReplayCommandOption(entry) for entry in entries]
    selected = forms.SelectFromList.show(
        options,
        name_attr="Name",
        title=u"选择要重放的历史指令",
        button_name=u"重放"
    )
    if not selected:
        print_system_message(output, u"已取消历史指令重放。")
        return levels

    command = selected.entry.get("command")
    if not command:
        print_system_message(output, u"所选历史记录缺少可执行指令。")
        return levels

    chat_state["last_command"] = command
    action = command.get("action", "unknown")
    print_system_message(output, u"正在按轮次重放历史归一化指令。")
    output.print_md("```json\n{}\n```".format(format_command_text(command)))

    try:
        result, levels = execute_command(doc, command, levels)
        if is_execution_failure_result(result):
            log_failed_turn(
                output,
                conversation_log,
                "/replaylog",
                result,
                command=command,
                action=action,
                source_kind="replay_log",
            )
            return levels

        operation_log.log(action, result)
        conversation_log.log_turn(
            "/replaylog",
            command=command,
            result=result,
            action=action,
            source_kind="replay_log",
        )
        output.print_md(u"**执行结果：** " + result)
        output.print_md("---")
        chat_state["last_result"] = result
        chat_state["last_action"] = action
        return levels
    except Exception as err:
        error_text = format_user_error(err)
        log_failed_turn(
            output,
            conversation_log,
            "/replaylog",
            error_text,
            command=command,
            action=action,
            source_kind="replay_log",
        )
        return levels


def replay_pick_failed_command_from_log(
    doc,
    output,
    levels,
    operation_log,
    conversation_log,
    chat_state,
    filter_keyword=None,
    source_filter_kind=None,
    action_filter=None,
    replay_user_input=None
):
    entries = load_failed_command_entries_from_latest_conversation_log()
    if not entries:
        print_system_message(output, u"最近一次会话文件中没有可选的失败指令。")
        return levels

    normalized_keyword = (filter_keyword or "").strip()
    replay_input_text = replay_user_input or "/replayfail"
    if normalized_keyword and replay_user_input is None:
        replay_input_text = "{} {}".format(replay_input_text, normalized_keyword)

    filtered_entries, failed_filter = _prepare_failed_entries_for_replay(
        output,
        entries,
        filter_keyword=normalized_keyword,
        source_filter_kind=source_filter_kind,
        action_filter=action_filter,
    )
    if not filtered_entries:
        return levels

    selected = _select_failed_entry_for_replay(
        output,
        filtered_entries,
        chat_state,
    )
    if not selected:
        print_system_message(output, u"已取消失败历史指令重放。")
        return levels

    if isinstance(selected, ReplayNavigationOption):
        direction_label = u"上一条" if selected.direction == "prev" else u"下一条"
        return _replay_failed_entry(
            doc,
            output,
            levels,
            operation_log,
            conversation_log,
            chat_state,
            selected.entry,
            replay_input_text,
            failed_filter,
            u"正在重放当前失败筛选结果中的{}记录（第 {} 轮）。".format(
                direction_label,
                selected.entry.get("round_index", "?")
            ),
        )

    command = selected.entry.get("command")
    if not command:
        print_system_message(output, u"所选失败记录缺少可执行指令。")
        return levels

    return _replay_failed_entry(
        doc,
        output,
        levels,
        operation_log,
        conversation_log,
        chat_state,
        selected.entry,
        replay_input_text,
        failed_filter,
        u"正在重放选中的失败历史归一化指令。",
    )


def replay_pick_failed_command_from_last_filter(
    doc,
    output,
    levels,
    operation_log,
    conversation_log,
    chat_state
):
    filter_state = _get_last_failed_filter(chat_state)
    if not filter_state:
        filter_state = load_last_failed_filter_from_latest_conversation_log()
        if not filter_state:
            print_system_message(output, u"当前没有可复用的失败筛选条件，请先执行一次 /replayfail。")
            return levels
        _remember_last_failed_filter(
            chat_state,
            source_filter_kind=filter_state.get("source_filter_kind"),
            action=filter_state.get("action"),
            keyword=filter_state.get("keyword"),
        )
        print_system_message(
            output,
            u"当前会话没有筛选缓存，已从最近一次会话文件恢复失败筛选条件：{}".format(
                _format_failed_filter_summary(filter_state)
            )
        )

    print_system_message(
        output,
        u"正在复用上次失败筛选条件：{}".format(
            _format_failed_filter_summary(filter_state)
        )
    )
    return replay_pick_failed_command_from_log(
        doc,
        output,
        levels,
        operation_log,
        conversation_log,
        chat_state,
        filter_keyword=filter_state.get("keyword"),
        source_filter_kind=filter_state.get("source_filter_kind"),
        action_filter=filter_state.get("action"),
        replay_user_input="/replayfail",
    )


def replay_adjacent_failed_command(
    doc,
    output,
    levels,
    operation_log,
    conversation_log,
    chat_state,
    step
):
    filter_state = _get_last_failed_filter(chat_state)
    current_round_index = _get_last_failed_selected_round_index(chat_state)
    if not filter_state or current_round_index is None:
        restored_filter_state = filter_state
        restored_round_index = current_round_index
        if restored_filter_state is None:
            restored_filter_state = load_last_failed_filter_from_latest_conversation_log()
        if restored_round_index is None:
            restored_round_index = load_last_failed_selected_round_index_from_latest_conversation_log()

        if not restored_filter_state or restored_round_index is None:
            print_system_message(output, u"当前没有可连续浏览的失败结果，请先执行一次 /replayfail。")
            return levels

        _remember_last_failed_filter(
            chat_state,
            source_filter_kind=restored_filter_state.get("source_filter_kind"),
            action=restored_filter_state.get("action"),
            keyword=restored_filter_state.get("keyword"),
        )
        _remember_last_failed_selected_round_index(chat_state, restored_round_index)
        filter_state = restored_filter_state
        current_round_index = restored_round_index
        print_system_message(
            output,
            u"当前会话没有连续浏览定位，已从最近一次会话文件恢复：{}，当前轮次=第 {} 轮".format(
                _format_failed_filter_summary(filter_state),
                current_round_index,
            )
        )

    entries = load_failed_command_entries_from_latest_conversation_log()
    if not entries:
        print_system_message(output, u"最近一次会话文件中没有可用的失败指令。")
        return levels

    filtered_entries, failed_filter = _prepare_failed_entries_for_replay(
        output,
        entries,
        filter_keyword=filter_state.get("keyword"),
        source_filter_kind=filter_state.get("source_filter_kind"),
        action_filter=filter_state.get("action"),
        announce_keyword_match=False,
    )
    if not filtered_entries:
        return levels

    current_index = None
    for index, entry in enumerate(filtered_entries):
        if _entry_sort_key(entry) == current_round_index:
            current_index = index
            break

    if current_index is None:
        print_system_message(output, u"当前筛选结果中未找到上次重放的失败轮次，请重新执行 /replayfail。")
        return levels

    target_index = current_index + step
    if target_index < 0:
        print_system_message(output, u"已经是当前失败筛选结果中的第一条记录。")
        return levels
    if target_index >= len(filtered_entries):
        print_system_message(output, u"已经是当前失败筛选结果中的最后一条记录。")
        return levels

    target_entry = filtered_entries[target_index]
    direction_label = u"下一条" if step > 0 else u"上一条"
    return _replay_failed_entry(
        doc,
        output,
        levels,
        operation_log,
        conversation_log,
        chat_state,
        target_entry,
        "/replayfail",
        failed_filter,
        u"正在重放当前失败筛选结果中的{}记录（第 {} 轮）。".format(
            direction_label,
            target_entry.get("round_index", "?")
        ),
    )


def replay_last_failed_command_from_log(
    doc,
    output,
    levels,
    operation_log,
    conversation_log,
    chat_state
):
    entry = load_last_failed_command_entry_from_latest_conversation_log()
    if not entry:
        print_system_message(output, u"最近一次会话文件中没有可重放的失败指令。")
        return levels

    command = entry.get("command")
    if not command:
        print_system_message(output, u"最近一次失败轮次缺少可执行指令，无法重放。")
        return levels

    return _replay_failed_entry(
        doc,
        output,
        levels,
        operation_log,
        conversation_log,
        chat_state,
        entry,
        "/replayfail",
        normalize_failed_filter_state(),
        u"正在重放最近一次失败轮次（第 {} 轮）的归一化指令。".format(
            entry.get("round_index", "?")
        ),
    )


def _prepare_failed_entries_for_replay(
    output,
    entries,
    filter_keyword=None,
    source_filter_kind=None,
    action_filter=None,
    announce_keyword_match=True
):
    if source_filter_kind:
        source_filtered_entries = filter_failed_entries_by_source_kind(
            output,
            entries,
            source_filter_kind
        )
        selected_source_filter_kind = source_filter_kind
    else:
        source_filtered_entries, selected_source_filter_kind = select_failed_entries_by_source(
            output,
            entries,
            return_filter_kind=True
        )
    if source_filtered_entries is None:
        return None, None

    if action_filter:
        filtered_entries = filter_failed_entries_by_action_kind(
            output,
            source_filtered_entries,
            action_filter
        )
        selected_action_filter = action_filter
    else:
        filtered_entries, selected_action_filter = select_failed_entries_by_action(
            output,
            source_filtered_entries,
            return_action=True
        )
    if filtered_entries is None:
        return None, None

    keyword_filtered_entries = filter_failed_entries_by_keyword(
        output,
        filtered_entries,
        filter_keyword=filter_keyword,
        announce_match=announce_keyword_match,
    )
    if keyword_filtered_entries is None:
        return None, None

    remembered_source_filter = selected_source_filter_kind or _infer_single_failed_source_kind(
        keyword_filtered_entries
    )
    remembered_action_filter = selected_action_filter or _infer_single_failed_action(
        keyword_filtered_entries
    )
    failed_filter = normalize_failed_filter_state(
        source_filter_kind=remembered_source_filter,
        action=remembered_action_filter,
        keyword=filter_keyword,
    )
    return keyword_filtered_entries, failed_filter


def _replay_failed_entry(
    doc,
    output,
    levels,
    operation_log,
    conversation_log,
    chat_state,
    entry,
    replay_input_text,
    failed_filter,
    banner_message
):
    command = entry.get("command")
    if not command:
        print_system_message(output, u"所选失败记录缺少可执行指令。")
        return levels

    _remember_last_failed_filter(
        chat_state,
        source_filter_kind=(failed_filter or {}).get("source_filter_kind"),
        action=(failed_filter or {}).get("action"),
        keyword=(failed_filter or {}).get("keyword"),
    )
    selected_round_index = normalize_failed_selected_round_index(
        entry.get("round_index")
    )
    _remember_last_failed_selected_round_index(chat_state, selected_round_index)
    chat_state["last_command"] = command
    action = command.get("action", "unknown")
    print_system_message(output, banner_message)
    output.print_md("```json\n{}\n```".format(format_command_text(command)))

    try:
        result, levels = execute_command(doc, command, levels)
        if is_execution_failure_result(result):
            log_failed_turn(
                output,
                conversation_log,
                replay_input_text,
                result,
                command=command,
                action=action,
                source_kind="replay_log",
                failed_filter=failed_filter,
                failed_selected_round_index=selected_round_index,
            )
            return levels

        operation_log.log(action, result)
        conversation_log.log_turn(
            replay_input_text,
            command=command,
            result=result,
            action=action,
            source_kind="replay_log",
            failed_filter=failed_filter,
            failed_selected_round_index=selected_round_index,
        )
        output.print_md(u"**执行结果：** " + result)
        output.print_md("---")
        chat_state["last_result"] = result
        chat_state["last_action"] = action
        return levels
    except Exception as err:
        error_text = format_user_error(err)
        log_failed_turn(
            output,
            conversation_log,
            replay_input_text,
            error_text,
            command=command,
            action=action,
            source_kind="replay_log",
            failed_filter=failed_filter,
            failed_selected_round_index=selected_round_index,
        )
        return levels


def select_failed_entries_by_source(output, entries, return_filter_kind=False):
    sorted_entries = _sort_entries_by_recency(entries)
    source_groups = group_entries_by_failed_source(sorted_entries)
    if len(source_groups) <= 1:
        if return_filter_kind:
            return sorted_entries, None
        return sorted_entries

    options = [ReplaySourceFilterOption(None, sorted_entries)]
    for source_filter_kind, grouped_entries in source_groups:
        options.append(ReplaySourceFilterOption(source_filter_kind, grouped_entries))

    selected = forms.SelectFromList.show(
        options,
        name_attr="Name",
        title=u"按来源筛选失败历史指令",
        button_name=u"查看失败指令"
    )
    if not selected:
        print_system_message(output, u"已取消失败来源筛选。")
        return None
    if return_filter_kind:
        return selected.entries, selected.source_filter_kind
    return selected.entries


def select_failed_entries_by_action(output, entries, return_action=False):
    sorted_entries = _sort_entries_by_recency(entries)
    action_groups = group_entries_by_action(sorted_entries)
    if len(action_groups) <= 1:
        if return_action:
            return sorted_entries, None
        return sorted_entries

    options = [ReplayActionFilterOption(None, sorted_entries)]
    for action, grouped_entries in action_groups:
        options.append(ReplayActionFilterOption(action, grouped_entries))

    selected = forms.SelectFromList.show(
        options,
        name_attr="Name",
        title=u"按动作筛选失败历史指令",
        button_name=u"查看失败指令"
    )
    if not selected:
        print_system_message(output, u"已取消失败动作筛选。")
        return None
    if return_action:
        return selected.entries, selected.action
    return selected.entries


def _select_failed_entry_for_replay(output, entries, chat_state):
    options = []
    current_round_index = _get_last_failed_selected_round_index(chat_state)
    previous_entry, next_entry = _get_adjacent_entries(entries, current_round_index)
    if previous_entry:
        options.append(ReplayNavigationOption("prev", previous_entry))
    if next_entry:
        options.append(ReplayNavigationOption("next", next_entry))
    options.extend([ReplayCommandOption(entry) for entry in entries])
    return forms.SelectFromList.show(
        options,
        name_attr="Name",
        title=u"选择要重放的失败历史指令",
        button_name=u"重放失败指令"
    )


def _get_adjacent_entries(entries, current_round_index):
    if current_round_index is None:
        return None, None

    current_index = None
    sorted_entries = _sort_entries_by_recency(entries)
    for index, entry in enumerate(sorted_entries):
        if _entry_sort_key(entry) == current_round_index:
            current_index = index
            break
    if current_index is None:
        return None, None

    previous_entry = sorted_entries[current_index - 1] if current_index > 0 else None
    next_entry = sorted_entries[current_index + 1] if current_index + 1 < len(sorted_entries) else None
    return previous_entry, next_entry


def filter_failed_entries_by_keyword(output, entries, filter_keyword=None, announce_match=True):
    normalized_keyword = (filter_keyword or "").strip()
    sorted_entries = _sort_entries_by_recency(entries)
    if not normalized_keyword:
        return sorted_entries

    lowered_keyword = normalized_keyword.lower()
    matched_entries = [
        entry for entry in sorted_entries
        if _failed_entry_matches_keyword(entry, lowered_keyword)
    ]
    if not matched_entries:
        if output is not None:
            print_system_message(
                output,
                u"最近一次会话文件中没有匹配关键字 `{}` 的失败指令。".format(
                    normalized_keyword
                )
            )
        return None

    if output is not None and announce_match:
        print_system_message(
            output,
            u"已按关键字 `{}` 筛选到 {} 条失败记录。".format(
                normalized_keyword,
                len(matched_entries)
            )
        )
    return matched_entries


def filter_failed_entries_by_source_kind(output, entries, source_filter_kind):
    if not source_filter_kind:
        return _sort_entries_by_recency(entries)

    matched_entries = [
        entry for entry in _sort_entries_by_recency(entries)
        if classify_failed_entry_source(entry) == source_filter_kind
    ]
    if matched_entries:
        return matched_entries

    print_system_message(
        output,
        u"最近一次会话文件中没有匹配来源 `{}` 的失败指令。".format(
            FAILED_SOURCE_FILTER_LABELS.get(source_filter_kind, source_filter_kind)
        )
    )
    return None


def filter_failed_entries_by_action_kind(output, entries, action):
    if not action:
        return _sort_entries_by_recency(entries)

    normalized_action = (action or "").strip() or "unknown"
    matched_entries = [
        entry for entry in _sort_entries_by_recency(entries)
        if (entry.get("action") or "unknown") == normalized_action
    ]
    if matched_entries:
        return matched_entries

    print_system_message(
        output,
        u"最近一次会话文件中没有匹配动作 `{}` 的失败指令。".format(
            format_action_label(normalized_action)
        )
    )
    return None


def _failed_entry_matches_keyword(entry, lowered_keyword):
    for text in (
        entry.get("error"),
        entry.get("error_summary"),
        entry.get("recovery_suggestion"),
        entry.get("recovery_summary"),
    ):
        if lowered_keyword in (u"{}".format(text or "")).lower():
            return True
    return False


def _infer_single_failed_source_kind(entries):
    source_kinds = set([
        classify_failed_entry_source(entry)
        for entry in (entries or [])
    ])
    if len(source_kinds) == 1:
        return list(source_kinds)[0]
    return None


def _infer_single_failed_action(entries):
    actions = set([
        (entry.get("action") or "unknown")
        for entry in (entries or [])
    ])
    if len(actions) == 1:
        return list(actions)[0]
    return None


def _format_failed_filter_summary(filter_state):
    summary_parts = []
    source_filter_kind = filter_state.get("source_filter_kind")
    action = filter_state.get("action")
    keyword = filter_state.get("keyword")

    if source_filter_kind:
        summary_parts.append(
            u"来源={}".format(
                FAILED_SOURCE_FILTER_LABELS.get(source_filter_kind, source_filter_kind)
            )
        )
    if action:
        summary_parts.append(u"动作={}".format(format_action_label(action)))
    if keyword:
        summary_parts.append(u"关键字={}".format(keyword))

    return u"，".join(summary_parts) or u"无"


def group_entries_by_action(entries):
    groups = {}
    for entry in entries or []:
        action = entry.get("action") or u"unknown"
        grouped_entries = groups.get(action)
        if grouped_entries is None:
            groups[action] = [entry]
            continue
        grouped_entries.append(entry)

    for action, grouped_entries in groups.items():
        groups[action] = _sort_entries_by_recency(grouped_entries)

    ordered = sorted(
        groups.items(),
        key=lambda item: _entry_sort_key(item[1][0] if item[1] else {}),
        reverse=True
    )
    return ordered


def group_entries_by_failed_source(entries):
    groups = {}
    for entry in entries or []:
        source_filter_kind = classify_failed_entry_source(entry)
        grouped_entries = groups.get(source_filter_kind)
        if grouped_entries is None:
            groups[source_filter_kind] = [entry]
            continue
        grouped_entries.append(entry)

    for source_filter_kind, grouped_entries in groups.items():
        groups[source_filter_kind] = _sort_entries_by_recency(grouped_entries)

    ordered = sorted(
        groups.items(),
        key=lambda item: _entry_sort_key(item[1][0] if item[1] else {}),
        reverse=True
    )
    return ordered


def _sort_entries_by_recency(entries):
    return sorted(entries or [], key=_entry_sort_key, reverse=True)


def _entry_sort_key(entry):
    round_index = entry.get("round_index")
    try:
        return int(round_index)
    except (TypeError, ValueError):
        return -1
