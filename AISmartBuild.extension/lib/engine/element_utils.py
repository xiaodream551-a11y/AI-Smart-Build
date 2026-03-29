# -*- coding: utf-8 -*-
"""Revit element property extraction -- shared utility functions for parser and export."""

import re

from utils import feet_to_mm


# ============================================================
# Text utilities
# ============================================================

def to_text(value):
    if value is None:
        return ""
    return "{}".format(value).strip()


def looks_like_plain_numeric_text(text):
    return re.match(r"^\d+(?:\.\d+)?$", to_text(text)) is not None


def normalize_numeric_text(text):
    value = float(to_text(text))
    if int(value) == value:
        return str(int(value))
    return "{}".format(value)


def format_number(value):
    rounded = round(float(value), 3)
    if abs(rounded - int(rounded)) < 0.001:
        return str(int(rounded))
    return str(rounded).rstrip("0").rstrip(".")


# ============================================================
# ElementId utilities
# ============================================================

def is_valid_element_id(element_id):
    return element_id is not None and getattr(element_id, "IntegerValue", -1) > 0


def get_element_level_id(DB, element):
    level_id = getattr(element, "LevelId", None)
    if is_valid_element_id(level_id):
        return level_id

    for builtin in [
        DB.BuiltInParameter.FAMILY_BASE_LEVEL_PARAM,
        DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM,
        DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM,
        DB.BuiltInParameter.LEVEL_PARAM,
    ]:
        level_id = get_level_id_from_parameter(DB, element, builtin)
        if is_valid_element_id(level_id):
            return level_id
    return None


def get_level_id_from_parameter(DB, element, builtin):
    param = element.get_Parameter(builtin)
    if not param or param.StorageType != DB.StorageType.ElementId:
        return None
    level_id = param.AsElementId()
    if is_valid_element_id(level_id):
        return level_id
    return None


def get_element_level_int(DB, element):
    level_id = get_element_level_id(DB, element)
    return getattr(level_id, "IntegerValue", -1)


# ============================================================
# Level name resolution
# ============================================================

def resolve_level_name(doc, level_id):
    if not is_valid_element_id(level_id):
        return ""
    level = doc.GetElement(level_id)
    return getattr(level, "Name", "")


# ============================================================
# Section information
# ============================================================

def get_element_section_text(DB, element):
    element_type = getattr(element, "Symbol", None)
    if element_type is None and hasattr(element, "GetTypeId"):
        type_id = element.GetTypeId()
        if is_valid_element_id(type_id):
            document = getattr(element, "Document", None)
            if document is not None:
                element_type = document.GetElement(type_id)

    if element_type is None:
        return ""

    type_name = to_text(getattr(element_type, "Name", ""))
    parsed_name = try_parse_section_name(type_name)
    if parsed_name:
        return parsed_name

    width_mm = get_type_dimension_mm(DB, element_type, ["b", "B", "Width", u"宽度"])
    height_mm = get_type_dimension_mm(DB, element_type, ["h", "H", "Depth", "Height", u"高度"])
    if width_mm is None or height_mm is None:
        return type_name
    return "{}x{}".format(
        format_number(width_mm),
        format_number(height_mm),
    )


def try_parse_section_name(name):
    text = to_text(name).replace(" ", "").replace("mm", "").replace("MM", "")
    if not text:
        return ""

    for separator in ("x", "X", u"\u00d7"):
        if separator not in text:
            continue
        left, right = text.split(separator, 1)
        if not looks_like_plain_numeric_text(left) or not looks_like_plain_numeric_text(right):
            return ""
        return "{}x{}".format(
            normalize_numeric_text(left),
            normalize_numeric_text(right),
        )
    return ""


def get_type_dimension_mm(DB, element_type, param_names):
    lookup = getattr(element_type, "LookupParameter", None)
    if lookup is None:
        return None

    for name in param_names:
        param = lookup(name)
        if not param or param.StorageType != DB.StorageType.Double:
            continue
        return feet_to_mm(param.AsDouble())
    return None


# ============================================================
# Area
# ============================================================

def get_element_area_sqm(DB, element):
    area = getattr(element, "Area", None)
    if area not in (None, ""):
        return float(area) * (0.3048 ** 2)

    builtin = getattr(DB.BuiltInParameter, "HOST_AREA_COMPUTED", None)
    param = element.get_Parameter(builtin)
    if param and param.StorageType == DB.StorageType.Double:
        return float(param.AsDouble()) * (0.3048 ** 2)

    for name in ("Area", u"面积"):
        lookup_fn = getattr(element, "LookupParameter", None)
        if lookup_fn is None:
            continue
        named_param = lookup_fn(name)
        if named_param and named_param.StorageType == DB.StorageType.Double:
            return float(named_param.AsDouble()) * (0.3048 ** 2)

    return 0.0
