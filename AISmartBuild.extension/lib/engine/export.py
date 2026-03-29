# -*- coding: utf-8 -*-
"""Model data export."""

import io
import json
import os

from pyrevit import DB

from engine.element_utils import (
    get_element_area_sqm,
    get_element_level_id,
    get_element_section_text,
    get_level_id_from_parameter,
    is_valid_element_id,
    resolve_level_name,
)
from utils import feet_to_mm, get_sorted_levels


_CATEGORY_TO_NAME = {
    DB.BuiltInCategory.OST_StructuralColumns: "columns",
    DB.BuiltInCategory.OST_StructuralFraming: "beams",
    DB.BuiltInCategory.OST_Floors: "slabs",
}


def export_model_data(doc):
    levels = get_sorted_levels(doc)
    data = {
        "levels": [
            {
                "name": level.Name,
                "elevation_mm": _round_mm(feet_to_mm(level.Elevation)),
            }
            for level in levels
        ],
        "columns": [],
        "beams": [],
        "slabs": [],
        "summary": {
            "columns": 0,
            "beams": 0,
            "slabs": 0,
        },
    }

    collectors = (
        (DB.BuiltInCategory.OST_StructuralColumns, _collect_column_data),
        (DB.BuiltInCategory.OST_StructuralFraming, _collect_beam_data),
        (DB.BuiltInCategory.OST_Floors, _collect_slab_data),
    )
    for category, builder in collectors:
        items = []
        for element in DB.FilteredElementCollector(doc).OfCategory(category).WhereElementIsNotElementType():
            item = builder(doc, element)
            if item:
                items.append(item)
        key = _CATEGORY_TO_NAME[category]
        data[key] = items
        data["summary"][key] = len(items)

    return data


def export_to_json(data, filepath):
    _ensure_parent_dir(filepath)
    with io.open(filepath, "w", encoding="utf-8") as output_file:
        json.dump(data, output_file, ensure_ascii=False, indent=2)


def export_to_excel(data, filepath):
    from openpyxl import Workbook

    _ensure_parent_dir(filepath)

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    _append_sheet(workbook, "柱", ["ID", "X(mm)", "Y(mm)", "底标高", "顶标高", "截面"], [
        [
            item["id"],
            item["x_mm"],
            item["y_mm"],
            item["base_level"],
            item["top_level"],
            item["section"],
        ]
        for item in data.get("columns", [])
    ])
    _append_sheet(workbook, "梁", ["ID", "起点X", "起点Y", "终点X", "终点Y", "标高", "截面"], [
        [
            item["id"],
            item["start_x_mm"],
            item["start_y_mm"],
            item["end_x_mm"],
            item["end_y_mm"],
            item["level"],
            item["section"],
        ]
        for item in data.get("beams", [])
    ])
    _append_sheet(workbook, "板", ["ID", "标高", "面积(m²)"], [
        [
            item["id"],
            item["level"],
            item["area_sqm"],
        ]
        for item in data.get("slabs", [])
    ])
    _append_sheet(workbook, "汇总", ["项目", "数量"], [
        ["柱", data.get("summary", {}).get("columns", 0)],
        ["梁", data.get("summary", {}).get("beams", 0)],
        ["板", data.get("summary", {}).get("slabs", 0)],
    ])

    workbook.save(filepath)


def _append_sheet(workbook, title, headers, rows):
    worksheet = workbook.create_sheet(title)
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    return worksheet


def _collect_column_data(doc, element):
    point = getattr(getattr(element, "Location", None), "Point", None)
    if point is None:
        return None

    base_level = resolve_level_name(doc, get_element_level_id(DB, element))
    top_level = resolve_level_name(
        doc,
        get_level_id_from_parameter(DB, element, DB.BuiltInParameter.FAMILY_TOP_LEVEL_PARAM)
    )
    return {
        "id": element.Id.IntegerValue,
        "x_mm": _round_mm(feet_to_mm(point.X)),
        "y_mm": _round_mm(feet_to_mm(point.Y)),
        "base_level": base_level,
        "top_level": top_level,
        "section": get_element_section_text(DB, element),
    }


def _collect_beam_data(doc, element):
    curve = getattr(getattr(element, "Location", None), "Curve", None)
    if curve is None:
        return None

    start = curve.GetEndPoint(0)
    end = curve.GetEndPoint(1)
    return {
        "id": element.Id.IntegerValue,
        "start_x_mm": _round_mm(feet_to_mm(start.X)),
        "start_y_mm": _round_mm(feet_to_mm(start.Y)),
        "end_x_mm": _round_mm(feet_to_mm(end.X)),
        "end_y_mm": _round_mm(feet_to_mm(end.Y)),
        "level": resolve_level_name(doc, get_element_level_id(DB, element)),
        "section": get_element_section_text(DB, element),
    }


def _collect_slab_data(doc, element):
    area_sqm = round(get_element_area_sqm(DB, element), 3)
    return {
        "id": element.Id.IntegerValue,
        "level": resolve_level_name(doc, get_element_level_id(DB, element)),
        "area_sqm": area_sqm,
    }


def _round_mm(value):
    return round(float(value), 3)


def _ensure_parent_dir(filepath):
    parent_dir = os.path.dirname(filepath)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
