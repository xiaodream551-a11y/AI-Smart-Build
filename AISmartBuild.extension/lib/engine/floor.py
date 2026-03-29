# -*- coding: utf-8 -*-
"""楼板创建"""

import clr
clr.AddReference('System')
from System.Collections.Generic import List

from pyrevit import DB
from utils import mm_to_feet, get_floor_type


def create_floor(doc, boundary_points_mm, level, floor_type_name=None):
    """
    创建楼板
    Args:
        doc: Revit Document
        boundary_points_mm: 边界点列表 [(x1,y1), (x2,y2), ...] (mm)，按顺序围合
        level: 楼板标高 (Level 对象)
        floor_type_name: 楼板类型名称，为 None 则使用默认
    Returns:
        Floor 对象
    """
    if level is None:
        raise ValueError("楼板标高不能为空")
    if not boundary_points_mm or len(boundary_points_mm) < 3:
        raise ValueError("楼板边界至少需要 3 个点")
    if _polygon_area(boundary_points_mm) == 0:
        raise ValueError("楼板边界不能共线或面积为 0")

    floor_type = get_floor_type(doc, floor_type_name)

    # 构建边界曲线环
    curve_loop = DB.CurveLoop()
    n = len(boundary_points_mm)
    for i in range(n):
        x1, y1 = boundary_points_mm[i]
        x2, y2 = boundary_points_mm[(i + 1) % n]
        p1 = DB.XYZ(mm_to_feet(x1), mm_to_feet(y1), level.Elevation)
        p2 = DB.XYZ(mm_to_feet(x2), mm_to_feet(y2), level.Elevation)
        line = DB.Line.CreateBound(p1, p2)
        curve_loop.Append(line)

    # Revit 2022+ 使用 Floor.Create，旧版本使用 NewFloor
    try:
        curve_loops = List[DB.CurveLoop]()
        curve_loops.Add(curve_loop)
        floor = DB.Floor.Create(doc, curve_loops, floor_type.Id, level.Id)
    except AttributeError:
        # Revit 2021 及更早版本：使用 doc.Create.NewFloor
        curve_array = DB.CurveArray()
        for curve in curve_loop:
            curve_array.Append(curve)
        floor = doc.Create.NewFloor(curve_array, floor_type, level, False)
    return floor


def _polygon_area(boundary_points_mm):
    area = 0.0
    count = len(boundary_points_mm or [])
    for index in range(count):
        x1, y1 = boundary_points_mm[index]
        x2, y2 = boundary_points_mm[(index + 1) % count]
        area += (x1 * y2) - (x2 * y1)
    return abs(area) / 2.0


def create_floors_on_grid(doc, x_coords_mm, y_coords_mm, level,
                          floor_type_name=None):
    """
    在每个轴网格子中创建楼板
    一般框架结构中，每层只创建一整块大板（外轮廓围合）
    Args:
        x_coords_mm: X 向坐标列表
        y_coords_mm: Y 向坐标列表
        level: 楼板标高
    Returns:
        Floor 对象
    """
    # 整层一块板：取最外轮廓
    x_min, x_max = min(x_coords_mm), max(x_coords_mm)
    y_min, y_max = min(y_coords_mm), max(y_coords_mm)

    boundary = [
        (x_min, y_min),
        (x_max, y_min),
        (x_max, y_max),
        (x_min, y_max),
    ]
    return create_floor(doc, boundary, level, floor_type_name)
