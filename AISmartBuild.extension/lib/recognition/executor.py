# -*- coding: utf-8 -*-
"""Execute a recognition build plan against the Revit modeling engine."""


def execute_build_plan(doc, plan, base_level=None, progress_callback=None):
    """Execute a sequenced build plan in Revit.

    Imports engine modules at call time so the module can be loaded
    in both IronPython (Revit) and CPython (pytest) environments.

    Args:
        doc: Revit Document object.
        plan: list of command dicts from ``generate_build_plan()``.
        base_level: Fallback Level object for walls/doors/windows.
            If the plan creates levels, the first created level is used.
        progress_callback: Optional ``fn(step, total, description)`` for
            progress reporting.

    Returns:
        dict with keys ``grids``, ``levels``, ``walls``, ``doors``,
        ``windows`` (int counts) and ``errors`` (list of str).
    """
    from engine.grid import create_grid_system
    from engine.level import create_level
    from engine.wall import create_wall
    from engine.door import place_door
    from engine.window import place_window

    result = {
        "grids": 0,
        "levels": 0,
        "walls": 0,
        "doors": 0,
        "windows": 0,
        "errors": [],
    }
    wall_map = {}           # wall id str -> Wall object
    created_levels = []     # Level objects created by the plan

    total = len(plan)
    for i, cmd in enumerate(plan):
        action = cmd["action"]
        params = cmd["params"]
        desc = cmd.get("description", action)

        if progress_callback:
            progress_callback(i + 1, total, desc)

        try:
            if action == "create_grid_system":
                x_grids, y_grids = create_grid_system(
                    doc,
                    params["x_coords_mm"],
                    params["y_coords_mm"],
                    x_labels=params.get("x_labels"),
                    y_labels=params.get("y_labels"),
                )
                result["grids"] = len(x_grids) + len(y_grids)

            elif action == "create_levels":
                for lv in params["levels"]:
                    elevation_mm = lv["elevation_m"] * 1000
                    level_obj = create_level(doc, lv["name"], elevation_mm)
                    created_levels.append(level_obj)
                result["levels"] = len(params["levels"])

            elif action == "create_wall":
                level = created_levels[0] if created_levels else base_level
                if level is None:
                    result["errors"].append(
                        u"跳过墙体 {}: 无可用标高".format(params.get("id", "?")))
                    continue
                wall = create_wall(
                    doc,
                    params["start_x"], params["start_y"],
                    params["end_x"], params["end_y"],
                    level=level,
                    height_mm=params.get("height", 3000),
                )
                wall_id = params.get("id", "")
                if wall_id and wall is not None:
                    wall_map[wall_id] = wall
                result["walls"] += 1

            elif action == "place_door":
                host_id = params.get("host_wall", "")
                host = wall_map.get(host_id)
                if host is None:
                    result["errors"].append(
                        u"门 {} 找不到宿主墙 {}".format(
                            params.get("code", "?"), host_id))
                    continue
                level = created_levels[0] if created_levels else base_level
                place_door(
                    doc, host,
                    params.get("position_x", 0),
                    params.get("position_y", 0),
                    level=level,
                    door_type=None,
                )
                result["doors"] += 1

            elif action == "place_window":
                host_id = params.get("host_wall", "")
                host = wall_map.get(host_id)
                if host is None:
                    result["errors"].append(
                        u"窗 {} 找不到宿主墙 {}".format(
                            params.get("code", "?"), host_id))
                    continue
                level = created_levels[0] if created_levels else base_level
                place_window(
                    doc, host,
                    params.get("position_x", 0),
                    params.get("position_y", 0),
                    level=level,
                    sill_height_mm=params.get("sill_height", 900),
                    window_type=None,
                )
                result["windows"] += 1

            else:
                result["errors"].append(
                    u"未知动作: {}".format(action))

        except Exception as e:
            result["errors"].append(
                u"步骤 {} ({}): {}".format(i + 1, action, str(e)))

    return result


def format_result(result):
    """Return a human-readable Chinese summary of execution results.

    Args:
        result: dict returned by ``execute_build_plan()``.

    Returns:
        str: Multi-line summary.
    """
    lines = [u"=== 执行结果 ==="]

    counts = [
        (u"轴网", result.get("grids", 0)),
        (u"标高", result.get("levels", 0)),
        (u"墙体", result.get("walls", 0)),
        (u"门", result.get("doors", 0)),
        (u"窗", result.get("windows", 0)),
    ]
    total = sum(c for _, c in counts)
    lines.append(u"成功创建 {} 个构件:".format(total))
    for label, count in counts:
        if count:
            lines.append(u"  {} \u00d7 {}".format(label, count))

    errors = result.get("errors", [])
    if errors:
        lines.append(u"")
        lines.append(u"警告 ({} 项):".format(len(errors)))
        for err in errors:
            lines.append(u"  - {}".format(err))

    return "\n".join(lines)
