# -*- coding: utf-8 -*-
"""轴网创建"""

from pyrevit import DB
from utils import mm_to_feet


def create_grid(doc, name, start_x_mm, start_y_mm, end_x_mm, end_y_mm):
    """
    创建一根轴线
    Args:
        doc: Revit Document
        name: 轴号，如 "1" 或 "A"
        start_x/y_mm, end_x/y_mm: 起止点坐标 (mm)
    Returns:
        Grid 对象
    """
    start = DB.XYZ(mm_to_feet(start_x_mm), mm_to_feet(start_y_mm), 0)
    end = DB.XYZ(mm_to_feet(end_x_mm), mm_to_feet(end_y_mm), 0)
    line = DB.Line.CreateBound(start, end)

    grid = DB.Grid.Create(doc, line)
    grid.Name = name
    return grid


def create_grid_system(doc, x_coords_mm, y_coords_mm,
                       x_labels=None, y_labels=None, extension_mm=1500):
    """
    创建完整的轴网系统
    Args:
        doc: Revit Document
        x_coords_mm: X 方向各轴线的 X 坐标列表 [0, 6000, 12000, ...]
        y_coords_mm: Y 方向各轴线的 Y 坐标列表 [0, 6000, 12000, ...]
        x_labels: X 向轴号列表 ["1","2","3",...]，默认自动编号
        y_labels: Y 向轴号列表 ["A","B","C",...]，默认自动编号
        extension_mm: 轴线超出边界的延伸长度
    Returns:
        (x_grids, y_grids) 两个列表
    """
    from config import GRID_LABELS_X, GRID_LABELS_Y

    if x_labels is None:
        x_labels = GRID_LABELS_X[:len(x_coords_mm)]
    if y_labels is None:
        y_labels = GRID_LABELS_Y[:len(y_coords_mm)]

    y_min = min(y_coords_mm) - extension_mm
    y_max = max(y_coords_mm) + extension_mm
    x_min = min(x_coords_mm) - extension_mm
    x_max = max(x_coords_mm) + extension_mm

    x_grids = []
    y_grids = []

    # X 方向轴线（竖线，沿 Y 方向画）
    for i, x in enumerate(x_coords_mm):
        label = x_labels[i] if i < len(x_labels) else str(i + 1)
        grid = create_grid(doc, label, x, y_min, x, y_max)
        x_grids.append(grid)

    # Y 方向轴线（横线，沿 X 方向画）
    for i, y in enumerate(y_coords_mm):
        label = y_labels[i] if i < len(y_labels) else chr(65 + i)
        grid = create_grid(doc, label, x_min, y, x_max, y)
        y_grids.append(grid)

    return x_grids, y_grids
