# -*- coding: utf-8 -*-
"""AI 对话智能建模"""

__doc__ = "用中文对话控制 Revit 建模 — 输入指令，AI 自动执行"
__title__ = "智能\n对话"
__author__ = "AI智建"

from pyrevit import revit, DB, forms, script

from config import DEEPSEEK_API_KEY
from ai.client import DeepSeekClient
from ai.parser import parse_command, dispatch_command
from utils import find_level_by_name


def get_all_levels(doc):
    """获取当前文档所有标高，按高程排序"""
    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.Level)
    levels = sorted(collector, key=lambda lv: lv.Elevation)
    return levels


def main():
    doc = revit.doc
    output = script.get_output()

    # 检查 API Key
    if not DEEPSEEK_API_KEY:
        forms.alert(
            "请先在 lib/config.py 中填入 DeepSeek API Key\n\n"
            "申请地址: https://platform.deepseek.com",
            title="AI 智建 — 配置缺失"
        )
        script.exit()

    output.print_md("## AI 智建 — 智能对话建模")
    output.print_md("输入中文建模指令，如：")
    output.print_md('- "在坐标(6000,0)处创建一根500x500的柱子"')
    output.print_md('- "生成一个3跨x2跨、5层的框架"')
    output.print_md('- "查询模型中有多少根柱子"')
    output.print_md("---")

    client = DeepSeekClient()
    levels = get_all_levels(doc)

    # 多轮对话循环
    while True:
        user_input = forms.ask_for_string(
            prompt="请输入建模指令（输入 q 退出）：",
            title="AI 智建 — 对话"
        )

        if not user_input or user_input.strip().lower() == "q":
            break

        output.print_md("**你：** " + user_input)

        try:
            # 调用大模型
            reply = client.chat(user_input)
            output.print_md("**AI 解析：** `{}`".format(
                reply[:200] + "..." if len(reply) > 200 else reply
            ))

            # 解析 JSON 指令
            command = parse_command(reply)

            # 在事务中执行
            with revit.Transaction("AI智建：" + command.get("action", "操作")):
                result = dispatch_command(doc, command, levels)

            # 刷新标高列表
            levels = get_all_levels(doc)

            output.print_md("**执行结果：** " + result)
            output.print_md("---")

        except Exception as e:
            output.print_md("**错误：** {}".format(str(e)))
            output.print_md("---")

    output.print_md("对话结束。")


if __name__ == "__main__":
    main()
