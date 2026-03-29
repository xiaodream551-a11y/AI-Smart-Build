# -*- coding: utf-8 -*-
"""Structural column creation."""

from pyrevit import DB
from utils import mm_to_feet, get_or_create_column_type, parse_section


def create_column(doc, x_mm, y_mm, base_level, top_level, section="500x500"):
    """
    Create a structural column at the specified location.

    Args:
        doc: Revit Document
        x_mm, y_mm: Column center coordinates (mm)
        base_level: Base level (Level object)
        top_level: Top level (Level object)
        section: Cross-section dimension string, e.g. "500x500" (mm)
    Returns:
        FamilyInstance column instance
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

    # Column insertion point
    point = DB.XYZ(mm_to_feet(x_mm), mm_to_feet(y_mm), base_level.Elevation)

    # Create structural column
    column = doc.Create.NewFamilyInstance(
        point,
        col_type,
        base_level,
        DB.Structure.StructuralType.Column
    )

    # Set top constraint to the upper level
    top_param = column.get_Parameter(
        DB.BuiltInParameter.FAMILY_TOP_LEVEL_PARAM
    )
    if top_param:
        top_param.Set(top_level.Id)

    # Reset top offset to zero
    top_offset = column.get_Parameter(
        DB.BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM
    )
    if top_offset:
        top_offset.Set(0.0)

    return column


def create_columns_on_grid(doc, x_coords_mm, y_coords_mm,
                           base_level, top_level, section="500x500"):
    """
    Create columns at all grid intersections.

    Args:
        x_coords_mm: X-direction coordinate list [0, 6000, 12000, ...]
        y_coords_mm: Y-direction coordinate list [0, 6000, ...]
        base_level, top_level: Base and top levels
        section: Column cross-section
    Returns:
        List of all column instances
    """
    columns = []
    for x in x_coords_mm:
        for y in y_coords_mm:
            col = create_column(doc, x, y, base_level, top_level, section)
            columns.append(col)
    return columns
