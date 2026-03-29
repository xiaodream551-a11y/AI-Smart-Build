# -*- coding: utf-8 -*-
"""Element modification and deletion."""

from pyrevit import DB
from utils import (
    get_sorted_levels,
    mm_to_feet,
    normalize_floor_number,
    parse_section,
    resolve_story_level_by_category,
)

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)

try:
    integer_types = (int, long)
except NameError:
    integer_types = (int,)


_CATEGORY_MAP = {
    "column": DB.BuiltInCategory.OST_StructuralColumns,
    "columns": DB.BuiltInCategory.OST_StructuralColumns,
    u"柱": DB.BuiltInCategory.OST_StructuralColumns,
    "beam": DB.BuiltInCategory.OST_StructuralFraming,
    "beams": DB.BuiltInCategory.OST_StructuralFraming,
    u"梁": DB.BuiltInCategory.OST_StructuralFraming,
    "slab": DB.BuiltInCategory.OST_Floors,
    "slabs": DB.BuiltInCategory.OST_Floors,
    "floor": DB.BuiltInCategory.OST_Floors,
    "floors": DB.BuiltInCategory.OST_Floors,
    u"板": DB.BuiltInCategory.OST_Floors,
    u"楼板": DB.BuiltInCategory.OST_Floors,
}

_CATEGORY_INFO = {
    DB.BuiltInCategory.OST_StructuralColumns: (u"柱", u"根"),
    DB.BuiltInCategory.OST_StructuralFraming: (u"梁", u"根"),
    DB.BuiltInCategory.OST_Floors: (u"楼板", u"块"),
}


def modify_element(doc, element_id, new_section=None, new_level=None):
    """
    Modify a single element's cross-section or level.

    Args:
        doc: Revit Document
        element_id: Element ElementId / int / str
        new_section: New cross-section, e.g. "600x600"
        new_level: New level; accepts Level / level name / floor number / ElementId
    Returns:
        str: Chinese result message
    """
    if not new_section and new_level is None:
        return u"未提供可修改内容"

    try:
        element = _get_element(doc, element_id)
        if not element:
            return u"未找到 ID 为 {} 的构件".format(_format_id_value(element_id))

        result_parts = []
        error_parts = []

        if new_section:
            try:
                section_text = _change_element_section(doc, element, new_section)
                result_parts.append(u"截面为 {}".format(section_text))
            except Exception as err:
                error_parts.append(u"截面修改失败: {}".format(err))

        if new_level is not None:
            try:
                target_level = _change_element_level(doc, element, new_level)
                result_parts.append(u"标高为 {}".format(target_level.Name))
            except Exception as err:
                error_parts.append(u"标高修改失败: {}".format(err))

        label = _get_element_label(element)
        elem_id = element.Id.IntegerValue

        if result_parts and not error_parts:
            return u"已修改{}(ID: {})，{}".format(
                label, elem_id, u"，".join(result_parts)
            )
        if result_parts and error_parts:
            return u"已部分修改{}(ID: {})，{}；{}".format(
                label, elem_id, u"，".join(result_parts), u"；".join(error_parts)
            )
        return u"修改{}(ID: {})失败：{}".format(
            label, elem_id, u"；".join(error_parts)
        )
    except Exception as err:
        return u"修改失败: {}".format(err)


def delete_element(doc, element_id):
    """
    Delete a single element.

    Args:
        doc: Revit Document
        element_id: Element ElementId / int / str
    Returns:
        str: Chinese result message
    """
    try:
        element = _get_element(doc, element_id)
        if not element:
            return u"未找到 ID 为 {} 的构件".format(_format_id_value(element_id))

        label = _get_element_label(element)
        elem_id = element.Id.IntegerValue
        doc.Delete(element.Id)
        return u"已删除{}(ID: {})".format(label, elem_id)
    except Exception as err:
        return u"删除失败: {}".format(err)


def batch_modify_by_filter(doc, category, floor_level, old_section, new_section):
    """
    Batch modify elements by category + floor + cross-section.

    Args:
        doc: Revit Document
        category: Element category, e.g. "column" / "beam"
        floor_level: Level object / level name / floor number
        old_section: Old cross-section
        new_section: New cross-section
    Returns:
        str: Chinese result message
    """
    try:
        old_section_text = _normalize_section(old_section)
        new_section_text = _normalize_section(new_section)

        cat = _resolve_category(category)
        if cat not in (
            DB.BuiltInCategory.OST_StructuralColumns,
            DB.BuiltInCategory.OST_StructuralFraming,
        ):
            return u"{}不支持批量截面修改".format(_get_category_label(cat, category))

        level = _resolve_filter_level(doc, cat, floor_level)
        if not level:
            return u"未找到标高: {}".format(floor_level)

        collector = DB.FilteredElementCollector(doc) \
            .OfCategory(cat) \
            .WhereElementIsNotElementType()

        elements = []
        for element in collector:
            if not _is_same_level(element, level.Id):
                continue
            if not _matches_section(element, old_section_text):
                continue
            elements.append(element)

        if not elements:
            return u"未找到符合条件的{}（标高：{}，截面：{}）".format(
                _get_category_label(cat), level.Name, old_section_text
            )

        success = 0
        failed = 0
        for element in elements:
            try:
                _change_element_section(doc, element, new_section_text)
                success += 1
            except Exception:
                failed += 1

        if success == 0 and failed:
            return u"未成功修改任何{}，目标截面：{}，失败 {} 个".format(
                _get_category_label(cat), new_section_text, failed
            )

        result = u"已修改 {} 截面为 {}".format(
            _format_count(cat, success), new_section_text
        )
        if floor_level is not None:
            result += u"，标高：{}".format(level.Name)
        if failed:
            result += u"，失败 {} 个".format(failed)
        return result
    except Exception as err:
        return u"批量修改失败: {}".format(err)


def batch_delete_by_filter(doc, category, floor_level=None):
    """
    Batch delete elements by category / floor.

    Args:
        doc: Revit Document
        category: Element category, e.g. "column" / "beam" / "slab"
        floor_level: Level object / level name / floor number, can be None
    Returns:
        str: Chinese result message
    """
    try:
        cat = _resolve_category(category)
        collector = DB.FilteredElementCollector(doc) \
            .OfCategory(cat) \
            .WhereElementIsNotElementType()

        level = None
        if floor_level is not None:
            level = _resolve_filter_level(doc, cat, floor_level)
            if not level:
                return u"未找到标高: {}".format(floor_level)

        element_ids = []
        for element in collector:
            if level and not _is_same_level(element, level.Id):
                continue
            element_ids.append(element.Id)

        if not element_ids:
            if level:
                return u"未找到可删除的{}（标高：{}）".format(
                    _get_category_label(cat), level.Name
                )
            return u"未找到可删除的{}".format(_get_category_label(cat))

        success = 0
        failed = 0
        for elem_id in element_ids:
            try:
                doc.Delete(elem_id)
                success += 1
            except Exception:
                failed += 1

        if success == 0 and failed:
            return u"未成功删除任何{}，失败 {} 个".format(
                _get_category_label(cat), failed
            )

        result = u"已删除 {}".format(_format_count(cat, success))
        if level:
            result += u"，标高：{}".format(level.Name)
        if failed:
            result += u"，失败 {} 个".format(failed)
        return result
    except Exception as err:
        return u"批量删除失败: {}".format(err)


def _change_element_section(doc, element, new_section):
    cat = _get_element_category(element)
    section_text = _normalize_section(new_section)

    if cat == DB.BuiltInCategory.OST_StructuralColumns:
        from utils import get_or_create_column_type
        target_type = get_or_create_column_type(doc, section_text)
    elif cat == DB.BuiltInCategory.OST_StructuralFraming:
        from utils import get_or_create_beam_type
        target_type = get_or_create_beam_type(doc, section_text)
    else:
        raise ValueError(u"{}不支持截面修改".format(_get_element_label(element)))

    if hasattr(element, "Symbol") and element.Symbol \
            and element.Symbol.Id.IntegerValue == target_type.Id.IntegerValue:
        return section_text

    if not target_type.IsActive:
        target_type.Activate()
        doc.Regenerate()

    element.ChangeTypeId(target_type.Id)
    return section_text


def _change_element_level(doc, element, new_level):
    level = _resolve_level(doc, new_level)
    if not level:
        raise ValueError(u"未找到目标标高: {}".format(new_level))

    cat = _get_element_category(element)
    if cat == DB.BuiltInCategory.OST_StructuralColumns:
        _set_column_level(doc, element, level)
    elif cat == DB.BuiltInCategory.OST_StructuralFraming:
        _set_element_level_param(
            element,
            [DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM,
             DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM,
             DB.BuiltInParameter.LEVEL_PARAM],
            level.Id
        )
        _reset_offsets(
            element,
            [DB.BuiltInParameter.Z_OFFSET_VALUE]
        )
    elif cat == DB.BuiltInCategory.OST_Floors:
        _set_element_level_param(
            element,
            [DB.BuiltInParameter.LEVEL_PARAM],
            level.Id
        )
        _reset_offsets(
            element,
            [DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM]
        )
    else:
        raise ValueError(u"{}不支持标高修改".format(_get_element_label(element)))

    return level


def _set_column_level(doc, element, level):
    top_level = _shift_column_top_level(doc, element, level)

    _set_element_level_param(
        element,
        [DB.BuiltInParameter.FAMILY_BASE_LEVEL_PARAM,
         DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM,
         DB.BuiltInParameter.LEVEL_PARAM],
        level.Id
    )
    _reset_offsets(
        element,
        [DB.BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM]
    )

    if top_level:
        _reset_offsets(
            element,
            [DB.BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM]
        )


def _shift_column_top_level(doc, element, new_base_level):
    base_param = element.get_Parameter(DB.BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)
    top_param = element.get_Parameter(DB.BuiltInParameter.FAMILY_TOP_LEVEL_PARAM)
    if not base_param or not top_param or top_param.IsReadOnly:
        return None

    current_base_id = base_param.AsElementId()
    current_top_id = top_param.AsElementId()
    if not _is_valid_element_id(current_base_id) or not _is_valid_element_id(current_top_id):
        return None

    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level))
    levels.sort(key=lambda item: item.Elevation)

    id_to_index = {}
    for index, item in enumerate(levels):
        id_to_index[item.Id.IntegerValue] = index

    base_index = id_to_index.get(current_base_id.IntegerValue)
    top_index = id_to_index.get(current_top_id.IntegerValue)
    new_base_index = id_to_index.get(new_base_level.Id.IntegerValue)
    if base_index is None or top_index is None or new_base_index is None:
        return None

    span = top_index - base_index
    new_top_index = new_base_index + span
    if new_top_index < 0 or new_top_index >= len(levels):
        return None

    new_top_level = levels[new_top_index]
    top_param.Set(new_top_level.Id)
    return new_top_level


def _set_element_level_param(element, builtins, level_id):
    for builtin in builtins:
        param = element.get_Parameter(builtin)
        if not param or param.IsReadOnly:
            continue
        if param.StorageType != DB.StorageType.ElementId:
            continue
        param.Set(level_id)
        return
    raise ValueError(u"{}缺少可写的标高参数".format(_get_element_label(element)))


def _reset_offsets(element, builtins):
    for builtin in builtins:
        param = element.get_Parameter(builtin)
        if not param or param.IsReadOnly:
            continue
        if param.StorageType == DB.StorageType.Double:
            param.Set(0.0)


def _matches_section(element, target_section):
    current_section = _get_element_section(element)
    if not current_section:
        return False
    return current_section == _normalize_section(target_section)


def _get_element_section(element):
    elem_type = None
    if hasattr(element, "Symbol") and element.Symbol:
        elem_type = element.Symbol
    elif hasattr(element, "GetTypeId"):
        type_id = element.GetTypeId()
        if _is_valid_element_id(type_id):
            elem_type = element.Document.GetElement(type_id)

    if not elem_type:
        return None

    name = getattr(elem_type, "Name", None)
    if name:
        parsed = _try_parse_section_text(name)
        if parsed:
            return parsed

    width_mm = _get_type_dimension_mm(elem_type, ["b", "B", "Width", u"宽度"])
    height_mm = _get_type_dimension_mm(elem_type, ["h", "H", "Depth", "Height", u"高度"])
    if width_mm is None or height_mm is None:
        return None

    return _normalize_section("{}x{}".format(
        _format_number(width_mm), _format_number(height_mm)
    ))


def _get_type_dimension_mm(elem_type, param_names):
    feet_per_mm = mm_to_feet(1.0)
    for name in param_names:
        param = elem_type.LookupParameter(name)
        if not param:
            continue
        if param.StorageType != DB.StorageType.Double:
            continue
        return param.AsDouble() / feet_per_mm
    return None


def _get_element(doc, element_id):
    if hasattr(element_id, "Document") and hasattr(element_id, "Id"):
        return element_id

    elem_id = _to_element_id(element_id)
    return doc.GetElement(elem_id)


def _to_element_id(value):
    if isinstance(value, DB.ElementId):
        return value
    if isinstance(value, integer_types):
        return DB.ElementId(value)
    if isinstance(value, string_types):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return DB.ElementId(int(text))
    raise ValueError(u"无效构件 ID: {}".format(value))


def _resolve_category(category):
    if category in _CATEGORY_INFO:
        return category

    if isinstance(category, string_types):
        text = category.strip()
        mapped = _CATEGORY_MAP.get(text)
        if mapped:
            return mapped

        lower_text = text.lower()
        mapped = _CATEGORY_MAP.get(lower_text)
        if mapped:
            return mapped

        if hasattr(DB.BuiltInCategory, text):
            return getattr(DB.BuiltInCategory, text)

    raise ValueError(u"不支持的构件类别: {}".format(category))


def _resolve_level(doc, level_value):
    from utils import find_level_by_name

    if isinstance(level_value, DB.Level):
        return level_value

    if isinstance(level_value, DB.ElementId):
        level = doc.GetElement(level_value)
        if isinstance(level, DB.Level):
            return level

    if isinstance(level_value, integer_types):
        level = doc.GetElement(DB.ElementId(level_value))
        if isinstance(level, DB.Level):
            return level
        return _get_level_by_index(doc, level_value)

    if isinstance(level_value, string_types):
        text = level_value.strip()
        if not text:
            return None

        level = find_level_by_name(doc, text)
        if level:
            return level

        if text.lstrip("-").isdigit():
            return _get_level_by_index(doc, int(text))

    return None


def _resolve_filter_level(doc, category, floor_level):
    floor_index = normalize_floor_number(floor_level)
    if floor_index is not None:
        levels = get_sorted_levels(doc)
        return resolve_story_level_by_category(levels, category, floor_index)

    return _resolve_level(doc, floor_level)


def _get_level_by_index(doc, floor_index):
    if floor_index <= 0:
        return None

    levels = get_sorted_levels(doc)
    if floor_index > len(levels):
        return None
    return levels[floor_index - 1]


def _is_same_level(element, level_id):
    element_level_id = _get_element_level_id(element)
    if not _is_valid_element_id(element_level_id):
        return False
    return element_level_id.IntegerValue == level_id.IntegerValue


def _get_element_level_id(element):
    level_id = getattr(element, "LevelId", None)
    if _is_valid_element_id(level_id):
        return level_id

    for builtin in [
        DB.BuiltInParameter.FAMILY_BASE_LEVEL_PARAM,
        DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM,
        DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM,
        DB.BuiltInParameter.LEVEL_PARAM,
    ]:
        param = element.get_Parameter(builtin)
        if not param or param.StorageType != DB.StorageType.ElementId:
            continue
        value = param.AsElementId()
        if _is_valid_element_id(value):
            return value
    return None


def _get_element_category(element):
    if not element or not element.Category:
        return None

    cat_id = element.Category.Id.IntegerValue
    for builtin in _CATEGORY_INFO:
        if int(builtin) == cat_id:
            return builtin
    return None


def _get_element_label(element):
    cat = _get_element_category(element)
    return _get_category_label(cat)


def _get_category_label(category, fallback=None):
    info = _CATEGORY_INFO.get(category)
    if info:
        return info[0]
    return fallback if fallback else u"构件"


def _format_count(category, count):
    info = _CATEGORY_INFO.get(category)
    if not info:
        return u"{} 个构件".format(count)
    return "{} {}{}".format(count, info[1], info[0])


def _normalize_section(section_text):
    text = _to_text(section_text).replace(" ", "").replace("mm", "").replace("MM", "")
    width, height = parse_section(text)
    return "{}x{}".format(_format_number(width), _format_number(height))


def _try_parse_section_text(text):
    cleaned = _to_text(text).replace(" ", "").replace("mm", "").replace("MM", "")
    try:
        return _normalize_section(cleaned)
    except Exception:
        return None


def _format_number(value):
    rounded = round(float(value), 3)
    if abs(rounded - int(rounded)) < 0.001:
        return str(int(rounded))
    return str(rounded).rstrip("0").rstrip(".")


def _is_valid_element_id(elem_id):
    return elem_id is not None and getattr(elem_id, "IntegerValue", -1) > 0


def _format_id_value(value):
    if hasattr(value, "IntegerValue"):
        return value.IntegerValue
    return value


def _to_text(value):
    if isinstance(value, string_types):
        return value
    return "{}".format(value)
