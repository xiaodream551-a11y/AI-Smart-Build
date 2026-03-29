# -*- coding: utf-8 -*-
"""AI 智建 — 工具函数（单位转换、族类型查找）"""

from pyrevit import DB

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


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
# 单位转换  (Revit 内部单位 = 英尺)
# ============================================================
_MM_PER_FOOT = 304.8

def mm_to_feet(mm):
    """毫米 → 英尺"""
    return mm / _MM_PER_FOOT

def m_to_feet(m):
    """米 → 英尺"""
    return m / 0.3048

def feet_to_mm(feet):
    """英尺 → 毫米"""
    return feet * _MM_PER_FOOT

def parse_section(section_str):
    """
    解析截面字符串 '400x500' → (400.0, 500.0)  单位 mm
    支持 'x' 和 '×' 分隔符
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
                    "截面尺寸必须为正数，当前值: {}".format(section_str)
                )
            return width, height
    raise ValueError("截面格式错误，应为 '宽x高'，如 '400x500'，当前值: {}".format(section_str))


# ============================================================
# 族类型查找 / 创建
# ============================================================

def find_family_symbol(doc, category_id, family_name=None, type_name=None):
    """
    在文档中查找族类型 (FamilySymbol)
    Args:
        doc: Revit Document
        category_id: BuiltInCategory 枚举值
        family_name: 族名称（模糊匹配），为 None 则不筛选
        type_name: 类型名称（模糊匹配），为 None 则不筛选
    Returns:
        匹配的第一个 FamilySymbol，找不到返回 None
    """
    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.FamilySymbol) \
        .OfCategory(category_id)

    for symbol in collector:
        if family_name and family_name not in symbol.Family.Name:
            continue
        if type_name and type_name not in symbol.Name:
            continue
        return symbol
    return None


def get_or_create_column_type(doc, section_str):
    """
    获取指定截面的柱类型，不存在则复制已有类型并修改尺寸
    Args:
        section_str: 如 '500x500'
    Returns:
        FamilySymbol
    """
    from config import COLUMN_FAMILY_NAME, COLUMN_FAMILY_NAME_EN

    w, h = parse_section(section_str)
    target_name = "{}x{}".format(int(w), int(h))

    # 先找完全匹配的类型
    cat = DB.BuiltInCategory.OST_StructuralColumns
    existing = find_family_symbol(doc, cat, type_name=target_name)
    if existing:
        return existing

    # 找一个可用的柱族作为模板
    template = find_family_symbol(doc, cat, family_name=COLUMN_FAMILY_NAME)
    if not template:
        template = find_family_symbol(doc, cat, family_name=COLUMN_FAMILY_NAME_EN)
    if not template:
        # 兜底：取该类别下任意一个
        template = find_family_symbol(doc, cat)
    if not template:
        raise Exception("未找到结构柱族，请先加载矩形柱族到项目中")

    # 复制类型并修改尺寸
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
    """获取指定截面的梁类型"""
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
        raise Exception("未找到结构梁族，请先加载矩形梁族到项目中")

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
    """获取楼板类型"""
    from config import FLOOR_TYPE_NAME, FLOOR_TYPE_NAME_EN

    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.FloorType)

    # 按名称查找
    for name in [type_name, FLOOR_TYPE_NAME, FLOOR_TYPE_NAME_EN]:
        if name:
            for ft in collector:
                if name in ft.Name:
                    return ft

    # 兜底：返回第一个
    for ft in collector:
        return ft
    raise Exception("未找到楼板类型")


def find_level_by_name(doc, name):
    """按名称查找标高"""
    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.Level)
    for level in collector:
        if level.Name == name:
            return level
    return None


def find_level_by_elevation(doc, elevation_feet, tolerance=0.01):
    """按高程查找标高（英尺）"""
    collector = DB.FilteredElementCollector(doc) \
        .OfClass(DB.Level)
    for level in collector:
        if abs(level.Elevation - elevation_feet) < tolerance:
            return level
    return None


def get_sorted_levels(doc):
    """获取按高程排序后的所有标高"""
    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level))
    levels.sort(key=lambda level: level.Elevation)
    return levels


def get_story_count(levels):
    """根据标高列表计算可用层数"""
    return max(len(levels) - 1, 0)


def normalize_floor_number(value):
    """将楼层值标准化为正整数，失败返回 None"""
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
    按楼层边界编号解析标高
    1 -> ±0.000, 2 -> F1, 3 -> F2 ...
    """
    floor_index = normalize_floor_number(floor_number)
    if floor_index is None or floor_index > len(levels):
        return None
    return levels[floor_index - 1]


def resolve_story_base_level(levels, floor_number):
    """
    按故事层号解析柱底标高
    1 -> ±0.000, 2 -> F1 ...
    """
    floor_index = normalize_floor_number(floor_number)
    story_count = get_story_count(levels)
    if floor_index is None or floor_index > story_count:
        return None
    return levels[floor_index - 1]


def resolve_story_framing_level(levels, floor_number):
    """
    按故事层号解析梁板所在标高
    1 -> F1, 2 -> F2 ...
    """
    floor_index = normalize_floor_number(floor_number)
    story_count = get_story_count(levels)
    if floor_index is None or floor_index > story_count:
        return None
    return levels[floor_index]


def is_column_category(category):
    """判断类别是否属于柱。"""
    if category == DB.BuiltInCategory.OST_StructuralColumns:
        return True

    if isinstance(category, string_types):
        return category.strip().lower() in ("column", "columns", "柱")

    return False


def resolve_story_level_by_category(levels, category, floor_number):
    """按类别语义解析故事层对应标高。"""
    if is_column_category(category):
        return resolve_story_base_level(levels, floor_number)
    return resolve_story_framing_level(levels, floor_number)


def list_story_floor_choices(levels, category):
    """返回可选故事层列表，元素为 (floor_number, level)。"""
    choices = []
    for floor_number in range(1, get_story_count(levels) + 1):
        level = resolve_story_level_by_category(levels, category, floor_number)
        if level:
            choices.append((floor_number, level))
    return choices


# ============================================================
# 内部辅助
# ============================================================

def _set_section_params(symbol, width_mm, height_mm):
    """设置族类型的截面宽高参数（尝试常见参数名）"""
    w_feet = mm_to_feet(width_mm)
    h_feet = mm_to_feet(height_mm)

    # 常见的宽度参数名
    width_names = ["b", "B", "Width", "宽度"]
    # 常见的高度参数名
    height_names = ["h", "H", "Depth", "Height", "高度"]

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
