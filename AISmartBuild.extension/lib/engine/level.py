# -*- coding: utf-8 -*-
"""Level creation."""

from pyrevit import DB
from utils import mm_to_feet, find_level_by_name, find_level_by_elevation


def create_level(doc, name, elevation_mm):
    """
    Create a level.

    Args:
        doc: Revit Document
        name: Level name, e.g. "F1", "F2"
        elevation_mm: Level elevation (mm)
    Returns:
        Level object
    """
    elevation_feet = mm_to_feet(elevation_mm)

    # Check if a level with the same name already exists
    existing_by_name = find_level_by_name(doc, name)
    if existing_by_name:
        return existing_by_name

    # Check if a level with the same elevation already exists
    existing = find_level_by_elevation(doc, elevation_feet)
    if existing:
        return existing

    level = DB.Level.Create(doc, elevation_feet)
    level.Name = name
    return level


def create_level_system(doc, num_floors, floor_height_mm,
                        first_floor_height_mm=None, base_elevation_mm=0):
    """
    Create a complete level system.

    Args:
        doc: Revit Document
        num_floors: Number of stories
        floor_height_mm: Standard story height (mm)
        first_floor_height_mm: First floor height (mm), defaults to standard if None
        base_elevation_mm: Base elevation (mm), typically 0
    Returns:
        List of levels from bottom to top [base, F1, F2, ..., roof]
    """
    if first_floor_height_mm is None:
        first_floor_height_mm = floor_height_mm

    levels = []
    elevations = [base_elevation_mm]  # Base (+-0.000)

    # Calculate elevation for each floor
    for floor in range(1, num_floors + 1):
        if floor == 1:
            elevations.append(elevations[-1] + first_floor_height_mm)
        else:
            elevations.append(elevations[-1] + floor_height_mm)

    # Create levels
    level_names = ["F{}".format(i) for i in range(len(elevations))]
    level_names[0] = "\u00b10.000"   # +-0.000 base level
    level_names[-1] = u"屋面"          # Top level is the roof

    for i, (name, elev) in enumerate(zip(level_names, elevations)):
        level = create_level(doc, name, elev)
        levels.append(level)

    return levels
