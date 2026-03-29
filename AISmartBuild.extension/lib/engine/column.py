# -*- coding: utf-8 -*-
"""结构柱创建"""

from pyrevit import DB
from utils import mm_to_feet, get_or_create_column_type, parse_section


def create_column(doc, x_mm, y_mm, base_level, top_level, section="500x500"):
    """
    在指定位置创建一根结构柱
    Args:
        doc: Revit Document
        x_mm, y_mm: 柱中心坐标 (mm)
        base_level: 底部标高 (Level 对象)
        top_level: 顶部标高 (Level 对象)
        section: 截面尺寸字符串，如 "500x500" (mm)
    Returns:
        FamilyInstance 柱实例
    """
    parse_section(section)
    if base_level is None:
        raise ValueError("柱底标高不能为空")
    if top_level is None:
        raise ValueError("柱顶标高不能为空")
    if base_level.Elevation >= top_level.Elevation:
        raise ValueError("柱底标高必须低于柱顶标高")

    col_type = get_or_create_column_type(doc, section)
    if not col_type.IsActive:
        col_type.Activate()
        doc.Regenerate()

    # 柱定位点
    point = DB.XYZ(mm_to_feet(x_mm), mm_to_feet(y_mm), base_level.Elevation)

    # 创建结构柱
    column = doc.Create.NewFamilyInstance(
        point,
        col_type,
        base_level,
        DB.Structure.StructuralType.Column
    )

    # 设置顶部约束到上一层标高
    top_param = column.get_Parameter(
        DB.BuiltInParameter.FAMILY_TOP_LEVEL_PARAM
    )
    if top_param:
        top_param.Set(top_level.Id)

    # 顶部偏移归零
    top_offset = column.get_Parameter(
        DB.BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM
    )
    if top_offset:
        top_offset.Set(0.0)

    return column


def create_columns_on_grid(doc, x_coords_mm, y_coords_mm,
                           base_level, top_level, section="500x500"):
    """
    在所有轴线交点处创建柱子
    Args:
        x_coords_mm: X 向坐标列表 [0, 6000, 12000, ...]
        y_coords_mm: Y 向坐标列表 [0, 6000, ...]
        base_level, top_level: 底部和顶部标高
        section: 柱截面
    Returns:
        所有柱实例的列表
    """
    columns = []
    for x in x_coords_mm:
        for y in y_coords_mm:
            col = create_column(doc, x, y, base_level, top_level, section)
            columns.append(col)
    return columns
