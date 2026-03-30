# -*- coding: utf-8 -*-
"""Export columns, beams, and slabs from the current model."""

__doc__ = "将当前模型中的柱、梁、板导出为 Excel 和 JSON"
__title__ = "导出\n模型"
__author__ = "AI智建"

import os
import sys

_vendor = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), "lib", "vendor")
if _vendor not in sys.path:
    sys.path.insert(0, _vendor)

from pyrevit import forms, revit, script

from engine.export import export_model_data, export_to_excel, export_to_json


def main():
    doc = revit.doc
    output = script.get_output()

    file_path = forms.save_file(
        file_ext="xlsx",
        default_name="模型导出.xlsx",
        title="选择模型导出路径",
    )
    if not file_path:
        script.exit()

    base_path, _ext = os.path.splitext(file_path)
    json_path = base_path + ".json"
    xlsx_path = base_path + ".xlsx"

    data = export_model_data(doc)
    export_to_json(data, json_path)

    excel_error = None
    try:
        export_to_excel(data, xlsx_path)
    except Exception as err:
        excel_error = err

    summary = data.get("summary", {})
    output.print_md("## AI 智建 — 模型导出")
    output.print_md("- JSON：`{}`".format(json_path))
    if excel_error:
        output.print_md("- Excel：导出失败（{}）".format(excel_error))
    else:
        output.print_md("- Excel：`{}`".format(xlsx_path))
    output.print_md("- 柱：`{}`".format(summary.get("columns", 0)))
    output.print_md("- 梁：`{}`".format(summary.get("beams", 0)))
    output.print_md("- 板：`{}`".format(summary.get("slabs", 0)))
    output.print_md("---")

    if excel_error:
        forms.alert(
            "JSON 已导出，但 Excel 导出失败：{}\n\n请确认当前环境可用 openpyxl / CPython。".format(excel_error),
            title="AI 智建 — 模型导出",
        )
    else:
        forms.alert(
            "模型导出完成。\n\nJSON: {}\nExcel: {}".format(json_path, xlsx_path),
            title="AI 智建 — 模型导出",
        )


if __name__ == "__main__":
    main()
