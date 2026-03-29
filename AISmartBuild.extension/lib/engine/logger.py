# -*- coding: utf-8 -*-
"""操作日志记录"""

from datetime import datetime
import io
import json
import os


SOURCE_LABELS = {
    "user": "用户输入",
    "retry": "重试上一条输入",
    "replay": "重放上一条指令",
    "replay_log": "从会话文件重放",
}


class OperationLog(object):
    """简单的操作日志记录器"""

    _SUMMARY_GROUPS = [
        (("create_grid",), "创建", "根轴线"),
        (("create_level",), "创建", "个标高"),
        (("create_column",), "创建", "根柱"),
        (("create_beam",), "创建", "根梁"),
        (("create_floor", "create_slab"), "创建", "块板"),
        (("modify_element", "batch_modify_by_filter"), "修改", "次"),
        (("delete_element", "batch_delete_by_filter"), "删除", "次"),
        (("query_count",), "查询", "次"),
        (("skip_row",), "跳过", "行"),
    ]

    def __init__(self):
        """初始化空日志列表"""
        self.logs = []
        self.counts = {}

    def log(self, action, detail, count=1):
        """
        记录一条操作日志
        Args:
            action: 操作类型，如 create_column
            detail: 操作详情文本
            count: 计数，默认为 1
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
            print("警告：OperationLog.log 收到负数 count={}，已按 0 处理并跳过记录。".format(count_value))
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
        返回中文摘要
        Returns:
            str
        """
        if not self.logs:
            return "本次操作：无"

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
                parts.append("{} {} 次".format(action_name, self.counts[action_name]))
                used_actions[action_name] = True

        return "本次操作：" + "、".join(parts)

    def get_detail(self):
        """
        返回完整日志文本
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
        保存日志到 txt 文件
        Args:
            filepath: 输出文件路径
        Returns:
            str: 文件路径
        """
        with io.open(filepath, "w", encoding="utf-8") as log_file:
            detail = self.get_detail()
            if detail:
                log_file.write(detail)
            else:
                log_file.write("无操作日志")
        return filepath

    def _to_text(self, value):
        if value is None:
            return ""
        return "{}".format(value)


class ConversationLog(object):
    """AI 对话会话记录。"""

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
        """追加一轮会话记录。"""
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
        """将当前会话记录渲染为 Markdown。"""
        if not self.turns:
            return ""

        sections = ["# AI 对话会话记录", ""]
        sections.extend(self._build_summary_lines())
        for index, entry in enumerate(self.turns, start=1):
            sections.append("")
            sections.append("## 第 {} 轮 [{}]".format(index, entry["timestamp"]))

            meta_lines = self._build_turn_meta_lines(entry)
            if meta_lines:
                sections.append("")
                sections.append("### 元信息")
                sections.extend(meta_lines)

            sections.append("")
            sections.append("### 用户输入")
            sections.append("```text")
            sections.append(entry["user_input"] or "")
            sections.append("```")

            if entry["reply"]:
                sections.append("")
                sections.append("### AI 原始回复")
                sections.append("```text")
                sections.append(entry["reply"])
                sections.append("```")

            if entry["command"] is not None:
                sections.append("")
                sections.append("### 归一化指令")
                sections.append("```json")
                sections.append(json.dumps(entry["command"], ensure_ascii=False, indent=2))
                sections.append("```")

            if entry["result"]:
                sections.append("")
                sections.append("### 执行结果")
                sections.append("```text")
                sections.append(entry["result"])
                sections.append("```")

            if entry["error"]:
                sections.append("")
                sections.append("### 错误")
                sections.append("```text")
                sections.append(entry["error"])
                sections.append("```")

            if entry["recovery_suggestion"]:
                sections.append("")
                sections.append("### 恢复建议")
                sections.append("```text")
                sections.append(entry["recovery_suggestion"])
                sections.append("```")

        return "\n".join(sections)

    def save_to_file(self, filepath):
        """保存 Markdown 会话文件，并同步写入同名 JSON。"""
        with io.open(filepath, "w", encoding="utf-8") as output_file:
            content = self.to_markdown()
            if content:
                output_file.write(content)
            else:
                output_file.write("无会话记录")
        json_path = os.path.splitext(filepath)[0] + ".json"
        self.save_to_json(json_path)
        return filepath

    def save_to_json(self, filepath):
        """将会话记录保存为 JSON 文件。"""
        with io.open(filepath, "w", encoding="utf-8") as output_file:
            json.dump(self.turns, output_file, ensure_ascii=False, indent=2)
        return filepath

    @classmethod
    def load_from_json(cls, filepath):
        """从 JSON 文件加载会话记录。"""
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
            "- 总轮次：{}".format(total),
            "- 成功：{}，失败：{}".format(success, failed),
        ]

        if duration_values:
            avg_duration = int(round(sum(duration_values) / float(len(duration_values))))
            lines.append("- AI 请求耗时：平均 {} ms，最大 {} ms".format(
                avg_duration,
                max(duration_values)
            ))

        if action_counts:
            ordered = sorted(action_counts.items(), key=lambda item: item[0])
            action_text = "，".join(
                "{} x{}".format(action, count) for action, count in ordered
            )
            lines.append("- 动作统计：{}".format(action_text))

        if source_counts:
            ordered = sorted(source_counts.items(), key=lambda item: item[0])
            source_text = "，".join(
                "{} x{}".format(
                    SOURCE_LABELS.get(source_kind, source_kind),
                    count
                ) for source_kind, count in ordered
            )
            lines.append("- 来源统计：{}".format(source_text))

        return lines

    def _build_turn_meta_lines(self, entry):
        lines = []

        if entry.get("action"):
            lines.append("- 动作：`{}`".format(entry["action"]))

        if entry.get("source_kind"):
            lines.append("- 来源：{}".format(
                SOURCE_LABELS.get(entry["source_kind"], entry["source_kind"])
            ))

        if entry.get("request_duration_ms") is not None:
            lines.append("- AI 请求耗时：`{} ms`".format(entry["request_duration_ms"]))

        failed_filter = entry.get("failed_filter") or {}
        if failed_filter.get("source_filter_kind"):
            lines.append("- 失败筛选来源：`{}`".format(
                failed_filter["source_filter_kind"]
            ))
        if failed_filter.get("action"):
            lines.append("- 失败筛选动作：`{}`".format(
                failed_filter["action"]
            ))
        if failed_filter.get("keyword"):
            lines.append("- 失败筛选关键字：`{}`".format(
                failed_filter["keyword"]
            ))
        if entry.get("failed_selected_round_index") is not None:
            lines.append("- 失败筛选当前轮次：`{}`".format(
                entry["failed_selected_round_index"]
            ))

        if entry.get("error"):
            lines.append("- 状态：失败")
        else:
            lines.append("- 状态：成功")

        return lines

    def _to_text(self, value):
        if value is None:
            return ""
        return "{}".format(value)


def build_default_output_path(prefix, extension="txt"):
    """生成默认输出文件路径。"""
    base_dir = get_default_output_dir()
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    safe_prefix = "{}".format(prefix or "操作日志").strip() or "操作日志"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_extension = "{}".format(extension or "txt").strip().lstrip(".") or "txt"
    filename = "{}-{}.{}".format(safe_prefix, timestamp, safe_extension)
    return os.path.join(base_dir, filename)


def get_default_output_dir():
    """返回默认输出目录。"""
    return os.path.join(
        os.path.expanduser("~"),
        "Documents",
        "AI智建日志"
    )


def build_default_log_path(prefix):
    """生成默认日志文件路径"""
    return build_default_output_path(prefix, "txt")


def export_operation_log(operation_log, prefix):
    """导出操作日志到默认目录"""
    if not operation_log or not operation_log.logs:
        return None

    output_path = build_default_log_path(prefix)
    operation_log.save_to_file(output_path)
    return output_path


def export_conversation_log(conversation_log, prefix):
    """导出 AI 对话会话记录。"""
    if not conversation_log or not conversation_log.turns:
        return None

    output_path = build_default_output_path(prefix, "md")
    conversation_log.save_to_file(output_path)
    return output_path


def find_latest_output_path(prefix, extension):
    """查找默认目录下最近生成的匹配文件。"""
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
