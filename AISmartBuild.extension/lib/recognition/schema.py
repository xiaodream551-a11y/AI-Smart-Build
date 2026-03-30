# -*- coding: utf-8 -*-
"""JSON schema validation for recognition outputs."""


def validate_step1(data):
    """Validate step 1 output (grids + levels + drawing info).

    Returns:
        list[str]: Validation errors. Empty list means valid.
    """
    errors = []

    # drawing_info
    info = data.get("drawing_info")
    if not isinstance(info, dict):
        errors.append("missing or invalid 'drawing_info'")
    else:
        if "floor" not in info:
            errors.append("drawing_info: missing 'floor'")

    # grids
    grids = data.get("grids")
    if not isinstance(grids, dict):
        errors.append("missing or invalid 'grids'")
    else:
        for axis in ("x", "y"):
            items = grids.get(axis)
            if not isinstance(items, list) or len(items) < 2:
                errors.append("grids.{}: need at least 2 grid lines".format(axis))
                continue
            for i, g in enumerate(items):
                if "name" not in g:
                    errors.append("grids.{}[{}]: missing 'name'".format(axis, i))
                if "distance" not in g:
                    errors.append("grids.{}[{}]: missing 'distance'".format(axis, i))
                elif not isinstance(g["distance"], (int, float)):
                    errors.append("grids.{}[{}]: 'distance' must be a number".format(axis, i))

    # levels (optional but must be a list if present)
    levels = data.get("levels")
    if levels is not None and not isinstance(levels, list):
        errors.append("'levels' must be a list")

    return errors


def validate_step2(data):
    """Validate step 2 output (walls).

    Returns:
        list[str]: Validation errors.
    """
    errors = []
    walls = data.get("walls")
    if not isinstance(walls, list):
        errors.append("missing or invalid 'walls'")
        return errors

    if len(walls) == 0:
        errors.append("walls: empty list, expected at least 1 wall")

    for i, w in enumerate(walls):
        prefix = "walls[{}]".format(i)
        if "id" not in w:
            errors.append("{}: missing 'id'".format(prefix))
        for endpoint in ("start", "end"):
            ep = w.get(endpoint)
            if not isinstance(ep, dict):
                errors.append("{}: missing '{}'".format(prefix, endpoint))
            else:
                if "grid_x" not in ep:
                    errors.append("{}.{}: missing 'grid_x'".format(prefix, endpoint))
                if "grid_y" not in ep:
                    errors.append("{}.{}: missing 'grid_y'".format(prefix, endpoint))
        if "thickness" not in w:
            errors.append("{}: missing 'thickness'".format(prefix))
        if w.get("type") not in ("exterior", "interior"):
            errors.append("{}: 'type' must be 'exterior' or 'interior'".format(prefix))

    return errors


def validate_step3(data):
    """Validate step 3 output (doors + windows + rooms).

    Returns:
        list[str]: Validation errors.
    """
    errors = []

    for category in ("doors", "windows"):
        items = data.get(category)
        if not isinstance(items, list):
            errors.append("missing or invalid '{}'".format(category))
            continue
        for i, item in enumerate(items):
            prefix = "{}[{}]".format(category, i)
            if "code" not in item:
                errors.append("{}: missing 'code'".format(prefix))
            if "width" not in item:
                errors.append("{}: missing 'width'".format(prefix))
            if "height" not in item:
                errors.append("{}: missing 'height'".format(prefix))
            if "host_wall" not in item:
                errors.append("{}: missing 'host_wall'".format(prefix))

    rooms = data.get("rooms")
    if not isinstance(rooms, list):
        errors.append("missing or invalid 'rooms'")
    else:
        for i, r in enumerate(rooms):
            if "name" not in r:
                errors.append("rooms[{}]: missing 'name'".format(i))

    return errors


def validate_full(data):
    """Validate a merged recognition result (all 3 steps combined).

    Returns:
        list[str]: Validation errors.
    """
    errors = []
    errors.extend(validate_step1(data))
    errors.extend(validate_step2(data))
    errors.extend(validate_step3(data))
    return errors
