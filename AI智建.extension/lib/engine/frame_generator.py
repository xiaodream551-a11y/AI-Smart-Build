# -*- coding: utf-8 -*-
"""
框架结构一键生成器
编排：轴网 → 标高 → 逐层(柱 → 梁 → 板) 的完整生成流程
"""

from engine.grid import create_grid_system
from engine.level import create_level_system
from engine.column import create_columns_on_grid
from engine.beam import create_beams_on_grid
from engine.floor import create_floors_on_grid


def generate_frame(doc, params, progress_callback=None):
    """
    一键生成完整框架结构
    Args:
        doc: Revit Document
        params: dict，包含以下字段:
            x_spans:       X 向各跨跨距列表 [6000, 6000, 6000] (mm)
            y_spans:       Y 向各跨跨距列表 [6000, 6000] (mm)
            num_floors:    层数 (int)
            floor_height:  标准层高 (mm)
            first_floor_height: 首层层高 (mm)，可选，默认同标准层高
            column_section: 柱截面，如 "500x500"
            beam_section_x: X 向梁截面，如 "300x600"
            beam_section_y: Y 向梁截面，如 "300x600"，可选，默认同 X 向
        progress_callback: 进度回调函数 fn(msg)，可选
    Returns:
        dict 统计信息
    """
    def log(msg):
        if progress_callback:
            progress_callback(msg)

    # ---------- 解析参数 ----------
    x_spans = params["x_spans"]
    y_spans = params["y_spans"]
    num_floors = params["num_floors"]
    floor_height = params["floor_height"]
    first_floor_height = params.get("first_floor_height", floor_height)
    col_section = params.get("column_section", "500x500")
    beam_section_x = params.get("beam_section_x", "300x600")
    beam_section_y = params.get("beam_section_y", beam_section_x)

    if not x_spans:
        raise ValueError("X 向跨距不能为空")
    if not y_spans:
        raise ValueError("Y 向跨距不能为空")
    if any(span <= 0 for span in x_spans):
        raise ValueError("X 向跨距必须全部大于 0")
    if any(span <= 0 for span in y_spans):
        raise ValueError("Y 向跨距必须全部大于 0")
    if num_floors <= 0:
        raise ValueError("层数必须大于 0")
    if floor_height <= 0:
        raise ValueError("标准层高必须大于 0")
    if first_floor_height <= 0:
        raise ValueError("首层层高必须大于 0")

    # ---------- 计算轴线坐标 ----------
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

    # ---------- 1. 创建轴网 ----------
    log("正在创建轴网...")
    x_grids, y_grids = create_grid_system(doc, x_coords, y_coords)
    stats["grids"] = len(x_grids) + len(y_grids)

    # ---------- 2. 创建标高 ----------
    log("正在创建标高...")
    levels = create_level_system(
        doc, num_floors, floor_height, first_floor_height
    )
    stats["levels"] = len(levels)

    # ---------- 3. 逐层创建构件 ----------
    for floor_idx in range(num_floors):
        base_level = levels[floor_idx]       # 本层底标高
        top_level = levels[floor_idx + 1]    # 本层顶标高
        floor_num = floor_idx + 1

        # 3a. 柱（从底标高到顶标高）
        log("正在生成第 {} 层柱...".format(floor_num))
        cols = create_columns_on_grid(
            doc, x_coords, y_coords,
            base_level, top_level, col_section
        )
        stats["columns"] += len(cols)

        # 3b. 梁（放在顶标高）
        log("正在生成第 {} 层梁...".format(floor_num))
        bms = create_beams_on_grid(
            doc, x_coords, y_coords,
            top_level, beam_section_x, beam_section_y
        )
        stats["beams"] += len(bms)

        # 3c. 楼板（放在顶标高）
        log("正在生成第 {} 层板...".format(floor_num))
        slab = create_floors_on_grid(doc, x_coords, y_coords, top_level)
        stats["floors"] += 1

    log("框架生成完成！")
    return stats


def format_stats(stats):
    """将统计信息格式化为中文摘要"""
    return (
        "生成完成：\n"
        "  轴线 {grids} 根\n"
        "  标高 {levels} 个\n"
        "  柱   {columns} 根\n"
        "  梁   {beams} 根\n"
        "  板   {floors} 块"
    ).format(**stats)
