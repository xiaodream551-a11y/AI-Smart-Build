# -*- coding: utf-8 -*-
"""AI 智建 — 工具函数（单位转换、族类型查找）"""

from pyrevit import DB

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
