# -*- coding: utf-8 -*-
"""标高创建"""

from pyrevit import DB
from utils import mm_to_feet, find_level_by_name, find_level_by_elevation


def create_level(doc, name, elevation_mm):
    """
    创建标高
    Args:
        doc: Revit Document
        name: 标高名称，如 "F1", "F2"
        elevation_mm: 标高高程 (mm)
    Returns:
        Level 对象
    """
    elevation_feet = mm_to_feet(elevation_mm)

    # 检查是否已存在同名标高
    existing_by_name = find_level_by_name(doc, name)
    if existing_by_name:
        return existing_by_name

    # 检查是否已存在相同高程的标高
    existing = find_level_by_elevation(doc, elevation_feet)
    if existing:
        return existing

    level = DB.Level.Create(doc, elevation_feet)
    level.Name = name
    return level


def create_level_system(doc, num_floors, floor_height_mm,
                        first_floor_height_mm=None, base_elevation_mm=0):
    """
    创建完整的标高系统
    Args:
        doc: Revit Document
        num_floors: 层数
        floor_height_mm: 标准层高 (mm)
        first_floor_height_mm: 首层层高 (mm)，为 None 则与标准层高相同
        base_elevation_mm: 基础标高 (mm)，通常为 0
    Returns:
        levels 列表，从下到上 [基础, F1, F2, ..., 屋面]
    """
    if first_floor_height_mm is None:
        first_floor_height_mm = floor_height_mm

    levels = []
    elevations = [base_elevation_mm]  # 基础 (±0.000)

    # 逐层计算标高
    for floor in range(1, num_floors + 1):
        if floor == 1:
            elevations.append(elevations[-1] + first_floor_height_mm)
        else:
            elevations.append(elevations[-1] + floor_height_mm)

    # 创建标高
    level_names = ["F{}".format(i) for i in range(len(elevations))]
    level_names[0] = "\u00b10.000"   # ±0.000 基础层
    level_names[-1] = "屋面"          # 最顶层为屋面

    for i, (name, elev) in enumerate(zip(level_names, elevations)):
        level = create_level(doc, name, elev)
        levels.append(level)

    return levels
