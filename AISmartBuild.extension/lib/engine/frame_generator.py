# -*- coding: utf-8 -*-
"""
Frame structure one-click generator.
Orchestrates the full generation pipeline: grids -> levels -> per-story (columns -> beams -> slabs).
"""

from engine.grid import create_grid_system
from engine.level import create_level_system
from engine.column import create_columns_on_grid
from engine.beam import create_beams_on_grid
from engine.floor import create_floors_on_grid
from utils import parse_section


def generate_frame(doc, params, progress_callback=None):
    """
    Generate a complete frame structure in one step.

    Args:
        doc: Revit Document
        params: dict with the following fields:
            x_spans:       X-direction span distances [6000, 6000, 6000] (mm)
            y_spans:       Y-direction span distances [6000, 6000] (mm)
            num_floors:    Number of stories (int)
            floor_height:  Standard story height (mm)
            first_floor_height: First floor height (mm), optional, defaults to standard
            column_section: Column cross-section, e.g. "500x500"
            beam_section_x: X-direction beam cross-section, e.g. "300x600"
            beam_section_y: Y-direction beam cross-section, e.g. "300x600", optional, defaults to X
        progress_callback: Progress callback function fn(msg), optional
    Returns:
        dict with statistics
    """
    def log(msg):
        if progress_callback:
            progress_callback(msg)

    # ---------- Parse parameters ----------
    x_spans = params["x_spans"]
    y_spans = params["y_spans"]
    num_floors = params["num_floors"]
    floor_height = params["floor_height"]
    first_floor_height = params.get("first_floor_height", floor_height)
    col_section = params.get("column_section", "500x500")
    beam_section_x = params.get("beam_section_x", "300x600")
    beam_section_y = params.get("beam_section_y", beam_section_x)

    if not x_spans:
        raise ValueError(u"X 向跨距不能为空")
    if not y_spans:
        raise ValueError(u"Y 向跨距不能为空")
    if any(span <= 0 for span in x_spans):
        raise ValueError(u"X 向跨距必须全部大于 0")
    if any(span <= 0 for span in y_spans):
        raise ValueError(u"Y 向跨距必须全部大于 0")
    if num_floors <= 0:
        raise ValueError(u"层数必须大于 0")
    if floor_height <= 0:
        raise ValueError(u"标准层高必须大于 0")
    if first_floor_height <= 0:
        raise ValueError(u"首层层高必须大于 0")
    _validate_section(col_section, u"柱截面")
    _validate_section(beam_section_x, u"X 向梁截面")
    _validate_section(beam_section_y, u"Y 向梁截面")

    # ---------- Calculate grid coordinates ----------
    x_coords = [0]
    for span in x_spans:
        x_coords.append(x_coords[-1] + span)

    y_coords = [0]
    for span in y_spans:
        y_coords.append(y_coords[-1] + span)

    stats = {
        "grids": 0, "levels": 0,
        "columns": 0, "beams": 0, "floors": 0,
    }

    # ---------- 1. Create grids ----------
    log(u"正在创建轴网...")
    x_grids, y_grids = create_grid_system(doc, x_coords, y_coords)
    stats["grids"] = len(x_grids) + len(y_grids)

    # ---------- 2. Create levels ----------
    log(u"正在创建标高...")
    levels = create_level_system(
        doc, num_floors, floor_height, first_floor_height
    )
    stats["levels"] = len(levels)

    # ---------- 3. Create elements per story ----------
    for floor_idx in range(num_floors):
        base_level = levels[floor_idx]       # Base level for this story
        top_level = levels[floor_idx + 1]    # Top level for this story
        floor_num = floor_idx + 1

        # 3a. Columns (from base level to top level)
        log(u"正在生成第 {} 层柱...".format(floor_num))
        cols = create_columns_on_grid(
            doc, x_coords, y_coords,
            base_level, top_level, col_section
        )
        stats["columns"] += len(cols)

        # 3b. Beams (placed at top level)
        log(u"正在生成第 {} 层梁...".format(floor_num))
        bms = create_beams_on_grid(
            doc, x_coords, y_coords,
            top_level, beam_section_x, beam_section_y
        )
        stats["beams"] += len(bms)

        # 3c. Floor slabs (placed at top level)
        log(u"正在生成第 {} 层板...".format(floor_num))
        slab = create_floors_on_grid(doc, x_coords, y_coords, top_level)
        stats["floors"] += 1

    log(u"框架生成完成！")
    return stats


def format_stats(stats):
    """Format statistics into a Chinese summary string."""
    return (
        u"生成完成：\n"
        u"  轴线 {grids} 根\n"
        u"  标高 {levels} 个\n"
        u"  柱   {columns} 根\n"
        u"  梁   {beams} 根\n"
        u"  板   {floors} 块"
    ).format(**stats)


def _validate_section(section_text, label):
    try:
        parse_section(section_text)
    except ValueError as err:
        raise ValueError(u"{}无效：{}".format(label, err))
