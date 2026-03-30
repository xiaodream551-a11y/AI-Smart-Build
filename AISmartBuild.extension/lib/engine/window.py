# -*- coding: utf-8 -*-
"""Window placement."""

from pyrevit import DB
from utils import mm_to_feet, find_family_symbol, _get_name


# Common Chinese window family names
WINDOW_FAMILY_NAMES = [u"固定窗", u"窗", "Window", "Fixed"]


def get_window_type(doc, family_name=None, type_name=None):
    """Find a window family type.

    Args:
        doc: Revit Document
        family_name: Family name substring to match
        type_name: Type name substring to match
    Returns:
        FamilySymbol or None
    """
    cat = DB.BuiltInCategory.OST_Windows
    if family_name:
        result = find_family_symbol(doc, cat, family_name=family_name, type_name=type_name)
        if result:
            return result

    for name in WINDOW_FAMILY_NAMES:
        result = find_family_symbol(doc, cat, family_name=name, type_name=type_name)
        if result:
            return result

    return find_family_symbol(doc, cat)


def place_window(doc, host_wall, position_x_mm, position_y_mm,
                 level, sill_height_mm=900, window_type=None):
    """Place a window on a host wall.

    Args:
        doc: Revit Document
        host_wall: Wall instance to host the window
        position_x/y_mm: Window location (mm)
        level: Level object
        sill_height_mm: Sill height above floor (mm), default 900
        window_type: FamilySymbol (auto-detected if None)
    Returns:
        FamilyInstance (window)
    """
    if host_wall is None:
        raise ValueError(u"窗的宿主墙不能为空")
    if level is None:
        raise ValueError(u"窗的标高不能为空")

    if window_type is None:
        window_type = get_window_type(doc)
    if window_type is None:
        raise ValueError(u"未找到窗族，请先在项目中加载窗族")

    if not window_type.IsActive:
        window_type.Activate()
        doc.Regenerate()

    point = DB.XYZ(
        mm_to_feet(position_x_mm),
        mm_to_feet(position_y_mm),
        mm_to_feet(sill_height_mm),
    )

    window = doc.Create.NewFamilyInstance(
        point, window_type, host_wall, level,
        DB.Structure.StructuralType.NonStructural,
    )

    # Set sill height parameter if available
    sill_param = window.get_Parameter(DB.BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
    if sill_param and not sill_param.IsReadOnly:
        sill_param.Set(mm_to_feet(sill_height_mm))

    return window
