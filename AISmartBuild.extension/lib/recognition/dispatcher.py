# -*- coding: utf-8 -*-
"""Bridge layer: convert recognition results to engine command plans."""

import json


def generate_build_plan(recognition_data):
    """Convert recognition output (absolute coords) to a sequenced build plan.

    Args:
        recognition_data: Dict from ``RecognitionResult.to_dict()`` with
            absolute coordinates (output of ``coordinator.convert_all``).

    Returns:
        list[dict]: Ordered list of build commands. Each command has:
            step, action, params, description.
    """
    plan = []
    step = 0

    # --- Step group 1: Grids ---
    grids = recognition_data.get("grids", {})
    x_grids = grids.get("x", [])
    y_grids = grids.get("y", [])

    if x_grids or y_grids:
        x_coords = [g["distance"] for g in x_grids]
        y_coords = [g["distance"] for g in y_grids]
        x_labels = [str(g["name"]) for g in x_grids]
        y_labels = [str(g["name"]) for g in y_grids]

        step += 1
        plan.append({
            "step": step,
            "action": "create_grid_system",
            "params": {
                "x_coords_mm": x_coords,
                "y_coords_mm": y_coords,
                "x_labels": x_labels,
                "y_labels": y_labels,
            },
            "description": u"创建轴网 ({}条X轴 + {}条Y轴)".format(
                len(x_grids), len(y_grids)
            ),
        })

    # --- Step group 2: Levels ---
    levels = recognition_data.get("levels", [])
    if levels:
        step += 1
        plan.append({
            "step": step,
            "action": "create_levels",
            "params": {
                "levels": [
                    {"name": lv["name"], "elevation_m": lv["elevation"]}
                    for lv in levels
                ],
            },
            "description": u"创建标高 ({}层)".format(len(levels)),
        })

    # --- Step group 3: Walls ---
    walls = recognition_data.get("walls", [])
    for w in walls:
        step += 1
        plan.append({
            "step": step,
            "action": "create_wall",
            "params": {
                "id": w.get("id", ""),
                "start_x": w["start_x"],
                "start_y": w["start_y"],
                "end_x": w["end_x"],
                "end_y": w["end_y"],
                "thickness": w.get("thickness", 240),
                "wall_type": w.get("type", "exterior"),
            },
            "description": u"创建{}墙 {} ({},{})→({},{})".format(
                u"外" if w.get("type") == "exterior" else u"内",
                w.get("id", ""),
                w["start_x"], w["start_y"],
                w["end_x"], w["end_y"],
            ),
        })

    # --- Step group 4: Doors ---
    doors = recognition_data.get("doors", [])
    for d in doors:
        step += 1
        plan.append({
            "step": step,
            "action": "place_door",
            "params": {
                "code": d.get("code", ""),
                "width": d.get("width", 900),
                "height": d.get("height", 2100),
                "position_x": d.get("position_x", 0),
                "position_y": d.get("position_y", 0),
                "host_wall": d.get("host_wall", ""),
            },
            "description": u"放置门 {} ({}×{})".format(
                d.get("code", ""), d.get("width", "?"), d.get("height", "?")
            ),
        })

    # --- Step group 5: Windows ---
    windows = recognition_data.get("windows", [])
    for win in windows:
        step += 1
        plan.append({
            "step": step,
            "action": "place_window",
            "params": {
                "code": win.get("code", ""),
                "width": win.get("width", 900),
                "height": win.get("height", 1800),
                "sill_height": win.get("sill_height", 900),
                "position_x": win.get("position_x", 0),
                "position_y": win.get("position_y", 0),
                "host_wall": win.get("host_wall", ""),
            },
            "description": u"放置窗 {} ({}×{})".format(
                win.get("code", ""), win.get("width", "?"), win.get("height", "?")
            ),
        })

    return plan


def preview_build_plan(plan):
    """Return a human-readable summary of the build plan.

    Args:
        plan: List from ``generate_build_plan()``.

    Returns:
        str: Multi-line summary in Chinese.
    """
    if not plan:
        return u"空计划，无操作"

    lines = [u"=== 建模计划 ({} 步) ===".format(len(plan))]

    action_counts = {}
    for cmd in plan:
        action = cmd["action"]
        action_counts[action] = action_counts.get(action, 0) + 1

    lines.append(u"")
    for action, count in action_counts.items():
        label = _ACTION_LABELS.get(action, action)
        lines.append(u"  {} × {}".format(label, count))

    lines.append(u"")
    lines.append(u"--- 详细步骤 ---")
    for cmd in plan:
        lines.append(u"  [{}] {}".format(cmd["step"], cmd["description"]))

    return "\n".join(lines)


def plan_to_json(plan, indent=2):
    """Serialize a build plan to JSON string."""
    return json.dumps(plan, ensure_ascii=False, indent=indent)


# Display labels for actions
_ACTION_LABELS = {
    "create_grid_system": u"创建轴网",
    "create_levels": u"创建标高",
    "create_wall": u"创建墙体",
    "place_door": u"放置门",
    "place_window": u"放置窗",
}
