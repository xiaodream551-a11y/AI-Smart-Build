# -*- coding: utf-8 -*-
"""操作日志记录"""

from datetime import datetime
import io


class OperationLog(object):
    """简单的操作日志记录器"""

    _SUMMARY_GROUPS = [
        (("create_column",), "创建", "根柱"),
        (("create_beam",), "创建", "根梁"),
        (("create_floor", "create_slab"), "创建", "块板"),
        (("modify_element", "batch_modify_by_filter"), "修改", "次"),
        (("delete_element", "batch_delete_by_filter"), "删除", "次"),
    ]

    def __init__(self):
        """初始化空日志列表"""
        self.logs = []
        self.counts = {}

    def log(self, action, detail):
        """
        记录一条操作日志
        Args:
            action: 操作类型，如 create_column
            detail: 操作详情文本
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        action_text = self._to_text(action)
        detail_text = self._to_text(detail)

        entry = {
            "timestamp": timestamp,
            "action": action_text,
            "detail": detail_text,
        }
        self.logs.append(entry)
        self.counts[action_text] = self.counts.get(action_text, 0) + 1
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
            lines.append(
                "[{time}] {action}: {detail}".format(
                    time=entry["timestamp"],
                    action=entry["action"],
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
