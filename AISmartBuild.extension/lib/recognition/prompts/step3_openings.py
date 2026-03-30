# -*- coding: utf-8 -*-
"""Step 3: Recognize doors, windows, and rooms."""

import json

PROMPT_TEMPLATE = u"""\
你是建筑施工图识别专家。以下是已识别的轴网和墙体信息：

轴网：
{grids_json}

墙体：
{walls_json}

请识别图中的所有门、窗和房间。

## 门窗编号规则（中国建筑制图标准）
- M 开头 = 门，如 M0924 表示宽 900mm 高 2400mm
- C 开头 = 窗，如 C0918 表示宽 900mm 高 1800mm
- MLC 开头 = 门联窗
- 编号前两位×100 = 宽度(mm)，后两位×100 = 高度(mm)

## 门的图形特征
- 平面图中门用扇形弧线表示开启方向
- 推拉门用平行线表示

## 窗的图形特征
- 平面图中窗用墙上的三条平行线表示

请严格按以下 JSON 格式输出：

{{
  "doors": [
    {{
      "code": "M0924",
      "width": 900,
      "height": 2400,
      "host_wall": "W3",
      "position": {{"grid_x": "3", "grid_y": "C", "offset_x": 200, "offset_y": 0}}
    }}
  ],
  "windows": [
    {{
      "code": "C0918",
      "width": 900,
      "height": 1800,
      "sill_height": 900,
      "host_wall": "W1",
      "position": {{"grid_x": "2", "grid_y": "A", "offset_x": 0, "offset_y": 0}}
    }}
  ],
  "rooms": [
    {{"name": "客厅", "floor": 1}},
    {{"name": "卧室", "floor": 1}}
  ]
}}

关键规则：
- 从图中的门窗编号标注读取 code，根据编号规则计算 width 和 height
- host_wall 填写该门窗所在墙体的 id（对应上面的墙体列表）
- sill_height（窗台高度）如果图中未标注，住宅默认 900mm
- rooms 只需列出图中用文字标注的房间名称
- 只输出 JSON，不要解释"""


def format_prompt(grids_data, walls_data):
    """Format step-3 prompt with grid and wall context.

    Args:
        grids_data: dict with "grids" key from step 1.
        walls_data: dict with "walls" key from step 2.
    """
    grids_json = json.dumps(grids_data.get("grids", {}), ensure_ascii=False, indent=2)
    walls_json = json.dumps(walls_data.get("walls", []), ensure_ascii=False, indent=2)
    return PROMPT_TEMPLATE.format(grids_json=grids_json, walls_json=walls_json)
