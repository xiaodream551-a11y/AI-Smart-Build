# -*- coding: utf-8 -*-
"""Export columns, beams, and slabs from the current model."""

__doc__ = "将当前模型中的柱、梁、板导出为 JSON 和 CSV"
__title__ = "导出\n模型"
__author__ = "AI智建"

import os

from pyrevit import forms, revit, script

from engine.export import export_model_data, export_to_json, _export_to_csv


def main():
    doc = revit.doc
    output = script.get_output()

    file_path = forms.save_file(
        file_ext="json",
        default_name="模型导出.json",
        title="选择模型导出路径",
    )
    if not file_path:
        script.exit()

    base_path, _ext = os.path.splitext(file_path)
    json_path = base_path + ".json"

    data = export_model_data(doc)
    export_to_json(data, json_path)
    csv_path = _export_to_csv(data, base_path + ".xlsx")

    summary = data.get("summary", {})
    output.print_md("## AI 智建 — 模型导出")
    output.print_md("- JSON：`{}`".format(json_path))
    output.print_md("- CSV：`{}`".format(csv_path))
    output.print_md("- 柱：`{}`".format(summary.get("columns", 0)))
    output.print_md("- 梁：`{}`".format(summary.get("beams", 0)))
    output.print_md("- 板：`{}`".format(summary.get("slabs", 0)))
    output.print_md("---")

    forms.alert(
        "模型导出完成。\n\nJSON: {}\nCSV: {}".format(json_path, csv_path),
        title="AI 智建 — 模型导出",
    )


if __name__ == "__main__":
    main()
