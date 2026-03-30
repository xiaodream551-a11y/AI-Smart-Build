# -*- coding: utf-8 -*-
"""Step 1: Recognize grids, levels, and drawing metadata."""

PROMPT = u"""\
你是一个建筑施工图识别专家。请仔细分析这张建筑平面图，提取以下信息：

## 1. 轴网 (Grid System)
- 横向轴号（通常为数字 1 2 3 ...，图中用圆圈标注）及其间距
- 纵向轴号（通常为字母 A B C ...，图中用圆圈标注）及其间距
- 间距从图中的尺寸标注线读取，单位为毫米(mm)

## 2. 图纸信息
- 图名（如"一层平面图"）
- 比例（如"1:100"）
- 楼层编号（一层=1，二层=2...）

## 3. 标高
- 从图中的标高符号（三角形+数字）读取
- 单位为米(m)

请严格按以下 JSON 格式输出，不要输出任何其他文字：

{
  "drawing_info": {
    "title": "图名",
    "scale": "比例",
    "floor": 1
  },
  "grids": {
    "x": [
      {"name": "1", "distance": 0},
      {"name": "2", "distance": 1500}
    ],
    "y": [
      {"name": "A", "distance": 0},
      {"name": "B", "distance": 1500}
    ]
  },
  "levels": [
    {"name": "1F", "elevation": 0.0},
    {"name": "2F", "elevation": 3.4}
  ]
}

关键规则：
- distance 是从第一根轴线算起的累计距离(mm)，第一根轴线 distance=0
- 第二根轴线的 distance = 第一个间距值，第三根 = 前两个间距之和，以此类推
- 轴网间距必须从尺寸标注线读取，不要猜测
- 标高单位为米(m)，如 ±0.000、3.400
- 如果图中没有标高标注，levels 数组留空 []
- 只输出 JSON，不要解释"""


def format_prompt():
    """Return the step-1 prompt."""
    return PROMPT
