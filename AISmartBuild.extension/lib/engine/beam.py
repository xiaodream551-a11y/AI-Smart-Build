# -*- coding: utf-8 -*-
"""结构梁创建"""

from pyrevit import DB
from utils import mm_to_feet, get_or_create_beam_type, parse_section


def create_beam(doc, start_x_mm, start_y_mm, end_x_mm, end_y_mm,
                level, section="300x600"):
    """
    创建一根结构梁
    Args:
        doc: Revit Document
        start_x/y_mm, end_x/y_mm: 梁起止点坐标 (mm)
        level: 梁所在标高 (Level 对象)
        section: 截面尺寸字符串，如 "300x600" (mm)
    Returns:
        FamilyInstance 梁实例
    """
    if level is None:
        raise ValueError("梁所在标高不能为空")
    if start_x_mm == end_x_mm and start_y_mm == end_y_mm:
        raise ValueError("梁的起点和终点不能相同，不能创建零长度梁")
    parse_section(section)

    beam_type = get_or_create_beam_type(doc, section)
    if not beam_type.IsActive:
        beam_type.Activate()
        doc.Regenerate()

    z = level.Elevation  # 梁顶标高

    start = DB.XYZ(mm_to_feet(start_x_mm), mm_to_feet(start_y_mm), z)
    end = DB.XYZ(mm_to_feet(end_x_mm), mm_to_feet(end_y_mm), z)
    line = DB.Line.CreateBound(start, end)

    beam = doc.Create.NewFamilyInstance(
        line,
        beam_type,
        level,
        DB.Structure.StructuralType.Beam
    )
    return beam


def create_beams_on_grid(doc, x_coords_mm, y_coords_mm, level,
                         section_x="300x600", section_y="300x600"):
    """
    沿所有轴线创建梁
    Args:
        x_coords_mm: X 向坐标列表
        y_coords_mm: Y 向坐标列表
        level: 梁所在标高
        section_x: X 向梁截面（沿 X 方向的梁）
        section_y: Y 向梁截面（沿 Y 方向的梁）
    Returns:
        所有梁实例的列表
    """
    beams = []

    # X 向梁（横向，沿每条 Y 轴线）
    for y in y_coords_mm:
        for i in range(len(x_coords_mm) - 1):
            beam = create_beam(
                doc,
                x_coords_mm[i], y,
                x_coords_mm[i + 1], y,
                level, section_x
            )
            beams.append(beam)

    # Y 向梁（纵向，沿每条 X 轴线）
    for x in x_coords_mm:
        for i in range(len(y_coords_mm) - 1):
            beam = create_beam(
                doc,
                x, y_coords_mm[i],
                x, y_coords_mm[i + 1],
                level, section_y
            )
            beams.append(beam)

    return beams
