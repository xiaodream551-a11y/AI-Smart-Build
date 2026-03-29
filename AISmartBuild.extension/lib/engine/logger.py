# -*- coding: utf-8 -*-
"""Operation logging."""

from datetime import datetime
import io
import json
import os


SOURCE_LABELS = {
    "user": u"用户输入",
    "retry": u"重试上一条输入",
    "replay": u"重放上一条指令",
    "replay_log": u"从会话文件重放",
}


class OperationLog(object):
    """Simple operation logger."""

    _SUMMARY_GROUPS = [
        (("create_grid",), u"创建", u"根轴线"),
        (("create_level",), u"创建", u"个标高"),
        (("create_column",), u"创建", u"根柱"),
        (("create_beam",), u"创建", u"根梁"),
        (("create_floor", "create_slab"), u"创建", u"块板"),
        (("modify_element", "batch_modify_by_filter"), u"修改", u"次"),
        (("delete_element", "batch_delete_by_filter"), u"删除", u"次"),
        (("query_count", "query_detail", "query_summary"), u"查询", u"次"),
        (("skip_row",), u"跳过", u"行"),
    ]

    def __init__(self):
        """Initialize an empty log list."""
        self.logs = []
        self.counts = {}

    def log(self, action, detail, count=1):
        """
        Record an operation log entry.

        Args:
            action: Operation type, e.g. create_column
            detail: Operation detail text
            count: Count, defaults to 1
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        action_text = self._to_text(action)
        detail_text = self._to_text(detail)
        try:
            count_value = int(count)
        except (TypeError, ValueError):
            count_value = 1
        if count_value == 0:
            return None
        if count_value < 0:
            print(u"警告：OperationLog.log 收到负数 count={}，已按 0 处理并跳过记录。".format(count_value))
            return None

        entry = {
            "timestamp": timestamp,
            "action": action_text,
            "detail": detail_text,
            "count": count_value,
        }
        self.logs.append(entry)
        self.counts[action_text] = self.counts.get(action_text, 0) + count_value
        return entry

    def get_summary(self):
        """
        Return a Chinese-language summary string.

        Returns:
            str
        """
        if not self.logs:
            return u"本次操作：无"

        parts = []
        used_actions = {}

        for actions, verb, unit in self._SUMMARY_GROUPS:
            count = 0
            for action in actions:
                count += self.counts.get(action, 0)

            if count <= 0:
                continue
            parts.append("{} {} {}".format(verb, count, unit))
            for action in actions:
                used_actions[action] = True

        for action in self.logs:
            action_name = action["action"]
            if action_name in used_actions:
                continue
            if action_name in self.counts:
                parts.append(u"{} {} 次".format(action_name, self.counts[action_name]))
                used_actions[action_name] = True

        return u"本次操作：" + u"、".join(parts)

    def get_detail(self):
        """
        Return the full log text.

        Returns:
            str
        """
        if not self.logs:
            return ""

        lines = []
        for entry in self.logs:
            count_text = ""
            if entry.get("count", 1) > 1:
                count_text = " x{}".format(entry["count"])
            lines.append(
                "[{time}] {action}{count}: {detail}".format(
                    time=entry["timestamp"],
                    action=entry["action"],
                    count=count_text,
                    detail=entry["detail"]
                )
            )
        return "\n".join(lines)

    def save_to_file(self, filepath):
        """
        Save log to a txt file.

        Args:
            filepath: Output file path
        Returns:
            str: File path
        """
        with io.open(filepath, "w", encoding="utf-8") as log_file:
            detail = self.get_detail()
            if detail:
                log_file.write(detail)
            else:
                log_file.write(u"无操作日志")
        return filepath

    def _to_text(self, value):
        if value is None:
            return ""
        return "{}".format(value)


class ConversationLog(object):
    """AI conversation session log."""

    def __init__(self):
        self.turns = []

    def log_turn(
        self,
        user_input,
        reply=None,
        command=None,
        result=None,
        error=None,
        recovery_suggestion=None,
        action=None,
        request_duration_ms=None,
        source_kind=None,
        failed_filter=None,
        failed_selected_round_index=None
    ):
        """Append one conversation turn."""
        entry = self._normalize_turn({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "user_input": user_input,
            "reply": reply,
            "command": command,
            "result": result,
            "error": error,
            "recovery_suggestion": recovery_suggestion,
            "action": action,
            "request_duration_ms": request_duration_ms,
            "source_kind": source_kind,
            "failed_filter": failed_filter,
            "failed_selected_round_index": failed_selected_round_index,
        })
        self.turns.append(entry)
        return entry

    def to_markdown(self):
        """Render the current session log as Markdown."""
        if not self.turns:
            return ""

        sections = [u"# AI 对话会话记录", ""]
        sections.extend(self._build_summary_lines())
        for index, entry in enumerate(self.turns, start=1):
            sections.append("")
            sections.append(u"## 第 {} 轮 [{}]".format(index, entry["timestamp"]))

            meta_lines = self._build_turn_meta_lines(entry)
            if meta_lines:
                sections.append("")
                sections.append(u"### 元信息")
                sections.extend(meta_lines)

            sections.append("")
            sections.append(u"### 用户输入")
            sections.append("```text")
            sections.append(entry["user_input"] or "")
            sections.append("```")

            if entry["reply"]:
                sections.append("")
                sections.append(u"### AI 原始回复")
                sections.append("```text")
                sections.append(entry["reply"])
                sections.append("```")

            if entry["command"] is not None:
                sections.append("")
                sections.append(u"### 归一化指令")
                sections.append("```json")
                sections.append(json.dumps(entry["command"], ensure_ascii=False, indent=2))
                sections.append("```")

            if entry["result"]:
                sections.append("")
                sections.append(u"### 执行结果")
                sections.append("```text")
                sections.append(entry["result"])
                sections.append("```")

            if entry["error"]:
                sections.append("")
                sections.append(u"### 错误")
                sections.append("```text")
                sections.append(entry["error"])
                sections.append("```")

            if entry["recovery_suggestion"]:
                sections.append("")
                sections.append(u"### 恢复建议")
                sections.append("```text")
                sections.append(entry["recovery_suggestion"])
                sections.append("```")

        return "\n".join(sections)

    def save_to_file(self, filepath):
        """Save Markdown session file and write a companion JSON file."""
        with io.open(filepath, "w", encoding="utf-8") as output_file:
            content = self.to_markdown()
            if content:
                output_file.write(content)
            else:
                output_file.write(u"无会话记录")
        json_path = os.path.splitext(filepath)[0] + ".json"
        self.save_to_json(json_path)
        return filepath

    def save_to_json(self, filepath):
        """Save the session log as a JSON file."""
        with io.open(filepath, "w", encoding="utf-8") as output_file:
            json.dump(self.turns, output_file, ensure_ascii=False, indent=2)
        return filepath

    @classmethod
    def load_from_json(cls, filepath):
        """Load session log from a JSON file."""
        with io.open(filepath, "r", encoding="utf-8") as input_file:
            data = json.load(input_file)

        turns = data
        if isinstance(data, dict):
            turns = data.get("turns", [])
        if not isinstance(turns, list):
            turns = []

        conversation_log = cls()
        conversation_log.turns = [
            conversation_log._normalize_turn(entry)
            for entry in turns
            if isinstance(entry, dict)
        ]
        return conversation_log

    def _normalize_turn(self, entry):
        timestamp = self._to_text(entry.get("timestamp")).strip()
        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
        return {
            "timestamp": timestamp,
            "user_input": self._to_text(entry.get("user_input")),
            "reply": self._to_text(entry.get("reply")),
            "command": self._normalize_command(entry.get("command")),
            "result": self._to_text(entry.get("result")),
            "error": self._to_text(entry.get("error")),
            "recovery_suggestion": self._to_text(entry.get("recovery_suggestion")),
            "action": self._to_text(entry.get("action")),
            "request_duration_ms": self._normalize_duration(entry.get("request_duration_ms")),
            "source_kind": self._normalize_source_kind(entry.get("source_kind")),
            "failed_filter": self._normalize_failed_filter(entry.get("failed_filter")),
            "failed_selected_round_index": self._normalize_round_index(
                entry.get("failed_selected_round_index")
            ),
        }

    def _normalize_command(self, command):
        if isinstance(command, dict):
            return command
        return None

    def _normalize_duration(self, value):
        if value in (None, ""):
            return None
        try:
            duration = int(round(float(value)))
        except (TypeError, ValueError):
            return None
        if duration < 0:
            return None
        return duration

    def _normalize_round_index(self, value):
        if value in (None, ""):
            return None
        try:
            round_index = int(value)
        except (TypeError, ValueError):
            return None
        if round_index <= 0:
            return None
        return round_index

    def _normalize_source_kind(self, value):
        text = self._to_text(value)
        if not text:
            return "user"
        return text

    def _normalize_failed_filter(self, value):
        if not isinstance(value, dict):
            return None

        source_filter_kind = self._to_text(value.get("source_filter_kind")).strip()
        action = self._to_text(value.get("action")).strip()
        keyword = self._to_text(value.get("keyword")).strip()
        if not (source_filter_kind or action or keyword):
            return None

        return {
            "source_filter_kind": source_filter_kind or "",
            "action": action or "",
            "keyword": keyword or "",
        }

    def _build_summary_lines(self):
        total = len(self.turns)
        success = 0
        failed = 0
        action_counts = {}
        source_counts = {}
        duration_values = []

        for entry in self.turns:
            if entry.get("error"):
                failed += 1
            else:
                success += 1

            action = entry.get("action")
            if action:
                action_counts[action] = action_counts.get(action, 0) + 1

            source_kind = entry.get("source_kind")
            if source_kind:
                source_counts[source_kind] = source_counts.get(source_kind, 0) + 1

            if entry.get("request_duration_ms") is not None:
                duration_values.append(entry["request_duration_ms"])

        lines = [
            u"- 总轮次：{}".format(total),
            u"- 成功：{}，失败：{}".format(success, failed),
        ]

        if duration_values:
            avg_duration = int(round(sum(duration_values) / float(len(duration_values))))
            lines.append(u"- AI 请求耗时：平均 {} ms，最大 {} ms".format(
                avg_duration,
                max(duration_values)
            ))

        if action_counts:
            ordered = sorted(action_counts.items(), key=lambda item: item[0])
            action_text = u"，".join(
                "{} x{}".format(action, count) for action, count in ordered
            )
            lines.append(u"- 动作统计：{}".format(action_text))

        if source_counts:
            ordered = sorted(source_counts.items(), key=lambda item: item[0])
            source_text = u"，".join(
                "{} x{}".format(
                    SOURCE_LABELS.get(source_kind, source_kind),
                    count
                ) for source_kind, count in ordered
            )
            lines.append(u"- 来源统计：{}".format(source_text))

        return lines

    def _build_turn_meta_lines(self, entry):
        lines = []

        if entry.get("action"):
            lines.append(u"- 动作：`{}`".format(entry["action"]))

        if entry.get("source_kind"):
            lines.append(u"- 来源：{}".format(
                SOURCE_LABELS.get(entry["source_kind"], entry["source_kind"])
            ))

        if entry.get("request_duration_ms") is not None:
            lines.append(u"- AI 请求耗时：`{} ms`".format(entry["request_duration_ms"]))

        failed_filter = entry.get("failed_filter") or {}
        if failed_filter.get("source_filter_kind"):
            lines.append(u"- 失败筛选来源：`{}`".format(
                failed_filter["source_filter_kind"]
            ))
        if failed_filter.get("action"):
            lines.append(u"- 失败筛选动作：`{}`".format(
                failed_filter["action"]
            ))
        if failed_filter.get("keyword"):
            lines.append(u"- 失败筛选关键字：`{}`".format(
                failed_filter["keyword"]
            ))
        if entry.get("failed_selected_round_index") is not None:
            lines.append(u"- 失败筛选当前轮次：`{}`".format(
                entry["failed_selected_round_index"]
            ))

        if entry.get("error"):
            lines.append(u"- 状态：失败")
        else:
            lines.append(u"- 状态：成功")

        return lines

    def _to_text(self, value):
        if value is None:
            return ""
        return "{}".format(value)


def build_default_output_path(prefix, extension="txt"):
    """Build a default output file path."""
    base_dir = get_default_output_dir()
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    safe_prefix = "{}".format(prefix or u"操作日志").strip() or u"操作日志"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_extension = "{}".format(extension or "txt").strip().lstrip(".") or "txt"
    filename = "{}-{}.{}".format(safe_prefix, timestamp, safe_extension)
    return os.path.join(base_dir, filename)


def get_default_output_dir():
    """Return the default output directory."""
    return os.path.join(
        os.path.expanduser("~"),
        "Documents",
        u"AI智建日志"
    )


def build_default_log_path(prefix):
    """Build a default log file path."""
    return build_default_output_path(prefix, "txt")


def export_operation_log(operation_log, prefix):
    """Export operation log to the default directory."""
    if not operation_log or not operation_log.logs:
        return None

    output_path = build_default_log_path(prefix)
    operation_log.save_to_file(output_path)
    return output_path


def export_conversation_log(conversation_log, prefix):
    """Export AI conversation session log."""
    if not conversation_log or not conversation_log.turns:
        return None

    output_path = build_default_output_path(prefix, "md")
    conversation_log.save_to_file(output_path)
    return output_path


def find_latest_output_path(prefix, extension):
    """Find the most recently generated matching file in the default directory."""
    base_dir = get_default_output_dir()
    if not os.path.exists(base_dir):
        return None

    safe_prefix = "{}".format(prefix or "").strip()
    safe_extension = "{}".format(extension or "").strip().lstrip(".")
    candidates = []

    for filename in os.listdir(base_dir):
        if safe_prefix and not filename.startswith(safe_prefix + "-"):
            continue
        if safe_extension and not filename.endswith("." + safe_extension):
            continue

        full_path = os.path.join(base_dir, filename)
        if os.path.isfile(full_path):
            candidates.append(full_path)

    if not candidates:
        return None

    candidates.sort(key=lambda item: os.path.getmtime(item), reverse=True)
    return candidates[0]
