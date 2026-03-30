# -*- coding: utf-8 -*-
"""Wall creation."""

from pyrevit import DB
from utils import mm_to_feet, _get_name


def get_wall_type(doc, thickness_mm=None, type_name=None):
    """Find a wall type, optionally matching thickness or name.

    Args:
        doc: Revit Document
        thickness_mm: Desired wall thickness in mm (approximate match)
        type_name: Type name substring to match
    Returns:
        WallType, or None if not found
    """
    collector = DB.FilteredElementCollector(doc).OfClass(DB.WallType)
    best = None

    for wt in collector:
        if type_name and type_name in _get_name(wt):
            return wt
        if thickness_mm is not None:
            width_param = wt.get_Parameter(DB.BuiltInParameter.WALL_ATTR_WIDTH_PARAM)
            if width_param:
                width_ft = width_param.AsDouble()
                width_mm = width_ft * 304.8
                if abs(width_mm - thickness_mm) < 5:
                    return wt
        if best is None:
            best = wt

    return best


def create_wall(doc, start_x_mm, start_y_mm, end_x_mm, end_y_mm,
                level, height_mm=3000, wall_type=None, is_structural=False):
    """Create a wall between two points.

    Args:
        doc: Revit Document
        start_x/y_mm, end_x/y_mm: Wall endpoints (mm)
        level: Base level (Level object)
        height_mm: Wall height (mm), default 3000
        wall_type: WallType object (auto-detected if None)
        is_structural: Whether the wall is structural
    Returns:
        Wall instance
    """
    if level is None:
        raise ValueError(u"墙体基准标高不能为空")

    start = DB.XYZ(mm_to_feet(start_x_mm), mm_to_feet(start_y_mm), 0)
    end = DB.XYZ(mm_to_feet(end_x_mm), mm_to_feet(end_y_mm), 0)
    line = DB.Line.CreateBound(start, end)

    if wall_type is None:
        wall_type = get_wall_type(doc)
    if wall_type is None:
        raise ValueError(u"未找到墙体类型，请先在项目中加载墙体族")

    height_ft = mm_to_feet(height_mm)

    wall = DB.Wall.Create(
        doc, line, wall_type.Id, level.Id,
        height_ft, 0.0, False, is_structural,
    )
    return wall


def create_walls_from_list(doc, wall_data_list, level, height_mm=3000,
                           wall_type=None, is_structural=False):
    """Create multiple walls from a list of coordinate dicts.

    Args:
        wall_data_list: List of dicts with start_x, start_y, end_x, end_y, thickness, type.
        level: Base level
        height_mm: Default wall height
        wall_type: Default wall type (auto if None)
        is_structural: Default structural flag
    Returns:
        List of (wall_id, wall_instance) tuples
    """
    results = []
    for wd in wall_data_list:
        wt = wall_type
        if wt is None and "thickness" in wd:
            wt = get_wall_type(doc, thickness_mm=wd["thickness"])
        wall = create_wall(
            doc,
            wd["start_x"], wd["start_y"],
            wd["end_x"], wd["end_y"],
            level, height_mm, wt, is_structural,
        )
        results.append((wd.get("id", ""), wall))
    return results
