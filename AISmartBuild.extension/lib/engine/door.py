# -*- coding: utf-8 -*-
"""Door placement."""

from pyrevit import DB
from utils import mm_to_feet, find_family_symbol, _get_name


# Common Chinese door family names
DOOR_FAMILY_NAMES = [u"单扇门", u"门", "Door", "Single-Flush"]


def get_door_type(doc, family_name=None, type_name=None):
    """Find a door family type.

    Args:
        doc: Revit Document
        family_name: Family name substring to match
        type_name: Type name substring to match
    Returns:
        FamilySymbol or None
    """
    cat = DB.BuiltInCategory.OST_Doors
    if family_name:
        result = find_family_symbol(doc, cat, family_name=family_name, type_name=type_name)
        if result:
            return result

    for name in DOOR_FAMILY_NAMES:
        result = find_family_symbol(doc, cat, family_name=name, type_name=type_name)
        if result:
            return result

    return find_family_symbol(doc, cat)


def place_door(doc, host_wall, position_x_mm, position_y_mm,
               level, door_type=None):
    """Place a door on a host wall.

    Args:
        doc: Revit Document
        host_wall: Wall instance to host the door
        position_x/y_mm: Door location (mm)
        level: Level object
        door_type: FamilySymbol (auto-detected if None)
    Returns:
        FamilyInstance (door)
    """
    if host_wall is None:
        raise ValueError(u"门的宿主墙不能为空")
    if level is None:
        raise ValueError(u"门的标高不能为空")

    if door_type is None:
        door_type = get_door_type(doc)
    if door_type is None:
        raise ValueError(u"未找到门族，请先在项目中加载门族")

    if not door_type.IsActive:
        door_type.Activate()
        doc.Regenerate()

    point = DB.XYZ(mm_to_feet(position_x_mm), mm_to_feet(position_y_mm), 0)

    door = doc.Create.NewFamilyInstance(
        point, door_type, host_wall, level,
        DB.Structure.StructuralType.NonStructural,
    )
    return door
