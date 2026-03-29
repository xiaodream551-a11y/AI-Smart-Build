# -*- coding: utf-8 -*-
"""Structural beam creation."""

from pyrevit import DB
from utils import mm_to_feet, get_or_create_beam_type, parse_section


def create_beam(doc, start_x_mm, start_y_mm, end_x_mm, end_y_mm,
                level, section="300x600"):
    """
    Create a structural beam.

    Args:
        doc: Revit Document
        start_x/y_mm, end_x/y_mm: Beam start and end point coordinates (mm)
        level: Beam level (Level object)
        section: Cross-section dimension string, e.g. "300x600" (mm)
    Returns:
        FamilyInstance beam instance
    """
    if level is None:
        raise ValueError(u"梁所在标高不能为空")
    if start_x_mm == end_x_mm and start_y_mm == end_y_mm:
        raise ValueError(u"梁的起点和终点不能相同，不能创建零长度梁")
    parse_section(section)

    beam_type = get_or_create_beam_type(doc, section)
    if not beam_type.IsActive:
        beam_type.Activate()
        doc.Regenerate()

    z = level.Elevation  # Beam top elevation

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
    Create beams along all grid lines.

    Args:
        x_coords_mm: X-direction coordinate list
        y_coords_mm: Y-direction coordinate list
        level: Beam level
        section_x: X-direction beam cross-section (beams running along X-axis)
        section_y: Y-direction beam cross-section (beams running along Y-axis)
    Returns:
        List of all beam instances
    """
    beams = []

    # X-direction beams (horizontal, along each Y-axis grid line)
    for y in y_coords_mm:
        for i in range(len(x_coords_mm) - 1):
            beam = create_beam(
                doc,
                x_coords_mm[i], y,
                x_coords_mm[i + 1], y,
                level, section_x
            )
            beams.append(beam)

    # Y-direction beams (longitudinal, along each X-axis grid line)
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
