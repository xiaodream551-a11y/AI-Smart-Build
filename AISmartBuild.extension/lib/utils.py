# -*- coding: utf-8 -*-
"""AI SmartBuild -- Utility functions (unit conversion, family type lookup)."""

from pyrevit import DB

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


def _get_name(element):
    """Get element name, compatible with Revit 2018-2024 IronPython."""
    try:
        return element.Name
    except AttributeError:
        return element.GetType().GetProperty("Name").GetValue(element, None)


def _set_name(element, name):
    """Set element name, compatible with Revit 2018-2024 IronPython."""
    try:
        element.Name = name
    except AttributeError:
        element.GetType().GetProperty("Name").SetValue(element, name, None)


_CHINESE_DIGIT_MAP = {
    u"零": 0,
    u"一": 1,
    u"二": 2,
    u"两": 2,
    u"三": 3,
    u"四": 4,
    u"五": 5,
    u"六": 6,
    u"七": 7,
    u"八": 8,
    u"九": 9,
}

# ============================================================
# Unit conversion (Revit internal unit = feet)
# ============================================================
_MM_PER_FOOT = 304.8

def mm_to_feet(mm):
    """Millimeters to feet."""
    return mm / _MM_PER_FOOT

def m_to_feet(m):
    """Meters to feet."""
    return m / 0.3048

def feet_to_mm(feet):
    """Feet to millimeters."""
    return feet * _MM_PER_FOOT

def parse_section(section_str):
    """
    Parse a cross-section string '400x500' -> (400.0, 500.0) in mm.
    Supports 'x' and 'x' (multiplication sign) separators.
    """
    for sep in ("x", "X", "\u00d7"):  # × = \u00d7
        if sep in section_str:
            parts = section_str.split(sep)
            if len(parts) != 2:
                break

            width = float(parts[0].strip())
            height = float(parts[1].strip())
            if width <= 0 or height <= 0:
                raise ValueError(
                    u"截面尺寸必须为正数，当前值: {}".format(section_str)
                )
            return width, height
    raise ValueError(u"截面格式错误，应为 '宽x高'，如 '400x500'，当前值: {}".format(section_str))


# ============================================================
# Family type lookup / creation
# ============================================================

def find_family_symbol(doc, category_id, family_name=None, type_name=None):
    """
    Find a family type (FamilySymbol) in the document.

    Args:
        doc: Revit Document
        category_id: BuiltInCategory enum value
        family_name: Family name (fuzzy match), None to skip filtering
        type_name: Type name (fuzzy match), None to skip filtering
    Returns:
        First matching FamilySymbol, or None if not found
    """
    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.FamilySymbol) \
        .OfCategory(category_id)

    for symbol in collector:
        if family_name and family_name not in _get_name(symbol.Family):
            continue
        if type_name and type_name not in _get_name(symbol):
            continue
        return symbol
    return None


def get_or_create_column_type(doc, section_str):
    """
    Get the column type for a given cross-section, duplicating an existing type if needed.

    Args:
        section_str: e.g. '500x500'
    Returns:
        FamilySymbol
    """
    from config import COLUMN_FAMILY_NAME, COLUMN_FAMILY_NAME_EN

    w, h = parse_section(section_str)
    target_name = "{}x{}".format(int(w), int(h))

    # First look for an exact match
    cat = DB.BuiltInCategory.OST_StructuralColumns
    existing = find_family_symbol(doc, cat, type_name=target_name)
    if existing:
        return existing

    # Find an available column family as a template
    template = find_family_symbol(doc, cat, family_name=COLUMN_FAMILY_NAME)
    if not template:
        template = find_family_symbol(doc, cat, family_name=COLUMN_FAMILY_NAME_EN)
    if not template:
        # Fallback: pick any symbol in this category
        template = find_family_symbol(doc, cat)
    if not template:
        raise Exception(u"未找到结构柱族，请先加载矩形柱族到项目中")

    # Duplicate type and modify dimensions
    try:
        new_type = template.Duplicate(target_name)
    except Exception:
        existing = find_family_symbol(doc, cat, type_name=target_name)
        if existing:
            return existing
        raise
    _set_section_params(new_type, w, h)
    return new_type


def get_or_create_beam_type(doc, section_str):
    """Get the beam type for a given cross-section, duplicating an existing type if needed."""
    from config import BEAM_FAMILY_NAME, BEAM_FAMILY_NAME_EN

    w, h = parse_section(section_str)
    target_name = "{}x{}".format(int(w), int(h))

    cat = DB.BuiltInCategory.OST_StructuralFraming
    existing = find_family_symbol(doc, cat, type_name=target_name)
    if existing:
        return existing

    template = find_family_symbol(doc, cat, family_name=BEAM_FAMILY_NAME)
    if not template:
        template = find_family_symbol(doc, cat, family_name=BEAM_FAMILY_NAME_EN)
    if not template:
        template = find_family_symbol(doc, cat)
    if not template:
        raise Exception(u"未找到结构梁族，请先加载矩形梁族到项目中")

    try:
        new_type = template.Duplicate(target_name)
    except Exception:
        existing = find_family_symbol(doc, cat, type_name=target_name)
        if existing:
            return existing
        raise
    _set_section_params(new_type, w, h)
    return new_type


def get_floor_type(doc, type_name=None):
    """Get a floor type."""
    from config import FLOOR_TYPE_NAME, FLOOR_TYPE_NAME_EN

    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.FloorType)

    # Look up by name
    for name in [type_name, FLOOR_TYPE_NAME, FLOOR_TYPE_NAME_EN]:
        if name:
            for ft in collector:
                if name in _get_name(ft):
                    return ft

    # Fallback: return the first available
    for ft in collector:
        return ft
    raise Exception(u"未找到楼板类型")


def find_level_by_name(doc, name):
    """Find a level by name."""
    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.Level)
    for level in collector:
        if _get_name(level) == name:
            return level
    return None


def find_level_by_elevation(doc, elevation_feet, tolerance=0.01):
    """Find a level by elevation (in feet)."""
    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.Level)
    for level in collector:
        if abs(level.Elevation - elevation_feet) < tolerance:
            return level
    return None


def get_sorted_levels(doc):
    """Get all levels sorted by elevation."""
    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level))
    levels.sort(key=lambda level: level.Elevation)
    return levels


def get_story_count(levels):
    """Calculate the number of usable stories from the level list."""
    return max(len(levels) - 1, 0)


def normalize_floor_number(value):
    """Normalize a floor number value to a positive integer; returns None on failure."""
    if isinstance(value, string_types):
        text = value.strip()
        if not text:
            return None
        normalized_text = text
        if normalized_text.startswith(u"第"):
            normalized_text = normalized_text[1:]
        for suffix in (u"层楼", u"楼层", u"层", u"楼"):
            if normalized_text.endswith(suffix):
                normalized_text = normalized_text[:-len(suffix)]
                break
        normalized_text = normalized_text.strip()

        special_floors = {
            u"首层": 1,
            u"首": 1,
            u"底层": 1,
            u"首层楼": 1,
        }
        if normalized_text in special_floors:
            return special_floors[normalized_text]

        chinese_number = _parse_simple_chinese_number(normalized_text)
        if chinese_number is not None:
            return chinese_number

        value = normalized_text

    try:
        number = int(value)
    except (TypeError, ValueError):
        return None

    if number <= 0:
        return None
    return number


def _parse_simple_chinese_number(text):
    normalized_text = (text or "").strip()
    if not normalized_text:
        return None

    if normalized_text in _CHINESE_DIGIT_MAP:
        return _CHINESE_DIGIT_MAP[normalized_text]

    if normalized_text == u"十":
        return 10

    if u"十" not in normalized_text:
        return None

    tens_text, ones_text = normalized_text.split(u"十", 1)
    if tens_text:
        tens = _CHINESE_DIGIT_MAP.get(tens_text)
        if tens is None:
            return None
    else:
        tens = 1

    if ones_text:
        ones = _CHINESE_DIGIT_MAP.get(ones_text)
        if ones is None:
            return None
    else:
        ones = 0

    return tens * 10 + ones


def resolve_floor_boundary_level(levels, floor_number):
    """
    Resolve a level by floor boundary number.
    1 -> +-0.000, 2 -> F1, 3 -> F2 ...
    """
    floor_index = normalize_floor_number(floor_number)
    if floor_index is None or floor_index > len(levels):
        return None
    return levels[floor_index - 1]


def resolve_story_base_level(levels, floor_number):
    """
    Resolve the column base level by story number.
    1 -> +-0.000, 2 -> F1 ...
    """
    floor_index = normalize_floor_number(floor_number)
    story_count = get_story_count(levels)
    if floor_index is None or floor_index > story_count:
        return None
    return levels[floor_index - 1]


def resolve_story_framing_level(levels, floor_number):
    """
    Resolve the beam/slab level by story number.
    1 -> F1, 2 -> F2 ...
    """
    floor_index = normalize_floor_number(floor_number)
    story_count = get_story_count(levels)
    if floor_index is None or floor_index > story_count:
        return None
    return levels[floor_index]


def is_column_category(category):
    """Check whether the category is a column category."""
    if category == DB.BuiltInCategory.OST_StructuralColumns:
        return True

    if isinstance(category, string_types):
        return category.strip().lower() in ("column", "columns", u"柱")

    return False


def resolve_story_level_by_category(levels, category, floor_number):
    """Resolve the level for a story based on element category semantics."""
    if is_column_category(category):
        return resolve_story_base_level(levels, floor_number)
    return resolve_story_framing_level(levels, floor_number)


def list_story_floor_choices(levels, category):
    """Return a list of available story choices as (floor_number, level) tuples."""
    choices = []
    for floor_number in range(1, get_story_count(levels) + 1):
        level = resolve_story_level_by_category(levels, category, floor_number)
        if level:
            choices.append((floor_number, level))
    return choices


# ============================================================
# Internal helpers
# ============================================================

def _set_section_params(symbol, width_mm, height_mm):
    """Set cross-section width and height parameters on a family type (tries common parameter names)."""
    w_feet = mm_to_feet(width_mm)
    h_feet = mm_to_feet(height_mm)

    # Common width parameter names
    width_names = ["b", "B", "Width", u"宽度"]
    # Common height parameter names
    height_names = ["h", "H", "Depth", "Height", u"高度"]

    for name in width_names:
        p = symbol.LookupParameter(name)
        if p and not p.IsReadOnly:
            p.Set(w_feet)
            break

    for name in height_names:
        p = symbol.LookupParameter(name)
        if p and not p.IsReadOnly:
            p.Set(h_feet)
            break
