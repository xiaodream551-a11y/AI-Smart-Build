# -*- coding: utf-8 -*-
"""Grid creation."""

from pyrevit import DB
from utils import mm_to_feet, _set_name


def create_grid(doc, name, start_x_mm, start_y_mm, end_x_mm, end_y_mm):
    """
    Create a single grid line.

    Args:
        doc: Revit Document
        name: Grid label, e.g. "1" or "A"
        start_x/y_mm, end_x/y_mm: Start and end point coordinates (mm)
    Returns:
        Grid object
    """
    start = DB.XYZ(mm_to_feet(start_x_mm), mm_to_feet(start_y_mm), 0)
    end = DB.XYZ(mm_to_feet(end_x_mm), mm_to_feet(end_y_mm), 0)
    line = DB.Line.CreateBound(start, end)

    grid = DB.Grid.Create(doc, line)
    _set_name(grid, name)
    return grid


def create_grid_system(doc, x_coords_mm, y_coords_mm,
                       x_labels=None, y_labels=None, extension_mm=1500):
    """
    Create a complete grid system.

    Args:
        doc: Revit Document
        x_coords_mm: X-direction grid line X coordinates [0, 6000, 12000, ...]
        y_coords_mm: Y-direction grid line Y coordinates [0, 6000, 12000, ...]
        x_labels: X-direction grid labels ["1","2","3",...], auto-numbered by default
        y_labels: Y-direction grid labels ["A","B","C",...], auto-numbered by default
        extension_mm: Extension length beyond the grid boundary
    Returns:
        (x_grids, y_grids) two lists
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

    # X-direction grid lines (vertical lines, drawn along Y-axis)
    for i, x in enumerate(x_coords_mm):
        label = x_labels[i] if i < len(x_labels) else str(i + 1)
        grid = create_grid(doc, label, x, y_min, x, y_max)
        x_grids.append(grid)

    # Y-direction grid lines (horizontal lines, drawn along X-axis)
    for i, y in enumerate(y_coords_mm):
        label = y_labels[i] if i < len(y_labels) else chr(65 + i)
        grid = create_grid(doc, label, x_min, y, x_max, y)
        y_grids.append(grid)

    return x_grids, y_grids
