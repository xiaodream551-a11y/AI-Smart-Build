# -*- coding: utf-8 -*-
"""Convert grid-relative references to absolute coordinates (mm)."""


def _build_grid_lookup(grids):
    """Build name→distance lookup dicts for X and Y grids.

    Args:
        grids: {"x": [{"name": ..., "distance": ...}], "y": [...]}

    Returns:
        (x_lookup, y_lookup): Two dicts mapping grid name to distance.
    """
    x_lookup = {str(g["name"]): g["distance"] for g in grids.get("x", [])}
    y_lookup = {str(g["name"]): g["distance"] for g in grids.get("y", [])}
    return x_lookup, y_lookup


def grid_ref_to_absolute(grids, ref):
    """Convert a single grid reference to absolute (x, y) in mm.

    Args:
        grids: Grid data from step 1 ({"x": [...], "y": [...]}).
        ref: {"grid_x": "1", "grid_y": "A", "offset_x": 0, "offset_y": 0}

    Returns:
        (x_mm, y_mm): Absolute coordinates.

    Raises:
        ValueError: If the referenced grid name is not found.
    """
    x_lookup, y_lookup = _build_grid_lookup(grids)

    gx = str(ref.get("grid_x", ""))
    gy = str(ref.get("grid_y", ""))

    if gx not in x_lookup:
        raise ValueError(u"未知 X 轴号: '{}'".format(gx))
    if gy not in y_lookup:
        raise ValueError(u"未知 Y 轴号: '{}'".format(gy))

    x_mm = x_lookup[gx] + ref.get("offset_x", 0)
    y_mm = y_lookup[gy] + ref.get("offset_y", 0)
    return (x_mm, y_mm)


def wall_to_absolute(grids, wall):
    """Convert a wall dict from grid references to absolute coordinates.

    Args:
        grids: Grid data from step 1.
        wall: Wall dict from step 2 (with "start"/"end" grid refs).

    Returns:
        dict with absolute coordinates:
            id, start_x, start_y, end_x, end_y, thickness, type
    """
    sx, sy = grid_ref_to_absolute(grids, wall["start"])
    ex, ey = grid_ref_to_absolute(grids, wall["end"])
    return {
        "id": wall["id"],
        "start_x": sx,
        "start_y": sy,
        "end_x": ex,
        "end_y": ey,
        "thickness": wall["thickness"],
        "type": wall.get("type", "exterior"),
    }


def opening_to_absolute(grids, opening):
    """Convert a door/window dict from grid references to absolute coordinates.

    Args:
        grids: Grid data from step 1.
        opening: Door or window dict from step 3 (with "position" grid ref).

    Returns:
        dict with absolute position added (position_x, position_y).
    """
    pos = opening.get("position", {})
    if "grid_x" in pos and "grid_y" in pos:
        px, py = grid_ref_to_absolute(grids, pos)
    else:
        px, py = 0, 0

    result = dict(opening)
    result["position_x"] = px
    result["position_y"] = py
    return result


def convert_all(recognition_data):
    """Convert a full recognition result to absolute coordinates.

    Args:
        recognition_data: Merged dict from all 3 steps.

    Returns:
        dict with absolute coordinates for walls, doors, windows.
              Grids and levels are passed through unchanged.
    """
    grids = recognition_data.get("grids", {})

    abs_walls = []
    for w in recognition_data.get("walls", []):
        try:
            abs_walls.append(wall_to_absolute(grids, w))
        except ValueError:
            abs_walls.append(w)

    abs_doors = []
    for d in recognition_data.get("doors", []):
        try:
            abs_doors.append(opening_to_absolute(grids, d))
        except ValueError:
            abs_doors.append(d)

    abs_windows = []
    for win in recognition_data.get("windows", []):
        try:
            abs_windows.append(opening_to_absolute(grids, win))
        except ValueError:
            abs_windows.append(win)

    return {
        "drawing_info": recognition_data.get("drawing_info", {}),
        "grids": grids,
        "levels": recognition_data.get("levels", []),
        "walls": abs_walls,
        "doors": abs_doors,
        "windows": abs_windows,
        "rooms": recognition_data.get("rooms", []),
    }
