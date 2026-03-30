# -*- coding: utf-8 -*-
"""Step 2: Recognize walls based on grid system from step 1."""

import json

PROMPT_TEMPLATE = u"""\
你是建筑施工图识别专家。以下是已识别的轴网信息：

{grids_json}

请基于这个轴网坐标系，识别图中的所有墙体。

## 墙体识别方法
1. 外墙：沿建筑外轮廓的粗实线
2. 内墙：分隔房间的粗实线
3. 墙体厚度：从平面图尺寸标注读取（常见值：120、200、240mm）
4. 墙体位置：用轴线交点 + 偏移量表达

## 位置表达方式
- grid_x / grid_y：最近的轴线编号
- offset_x / offset_y：相对于该轴线的偏移量(mm)，轴线上则为 0

请严格按以下 JSON 格式输出：

{{
  "walls": [
    {{
      "id": "W1",
      "start": {{"grid_x": "1", "grid_y": "A", "offset_x": 0, "offset_y": 0}},
      "end": {{"grid_x": "5", "grid_y": "A", "offset_x": 0, "offset_y": 0}},
      "thickness": 240,
      "type": "exterior"
    }},
    {{
      "id": "W2",
      "start": {{"grid_x": "1", "grid_y": "A", "offset_x": 0, "offset_y": 0}},
      "end": {{"grid_x": "1", "grid_y": "E", "offset_x": 0, "offset_y": 0}},
      "thickness": 240,
      "type": "exterior"
    }}
  ]
}}

关键规则：
- 每段墙用起点和终点描述，墙线沿轴线方向（水平或垂直）
- type 只能是 "exterior"（外墙）或 "interior"（内墙）
- 如果墙不在轴线上，用 offset 表示偏移
- 墙体 id 从 W1 开始递增
- 只输出 JSON，不要解释"""


def format_prompt(grids_data):
    """Format step-2 prompt with grid context from step 1.

    Args:
        grids_data: dict with "grids" key from step 1 output.
    """
    grids_json = json.dumps(grids_data.get("grids", {}), ensure_ascii=False, indent=2)
    return PROMPT_TEMPLATE.format(grids_json=grids_json)
