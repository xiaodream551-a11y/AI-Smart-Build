# -*- coding: utf-8 -*-
"""AI 智建 — 全局配置"""

# ============================================================
# DeepSeek API 配置（第三阶段启用）
# ============================================================
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = ""  # 在此填入你的 API Key
DEEPSEEK_MODEL = "deepseek-chat"

# ============================================================
# Revit 默认参数
# ============================================================
# 族名称（中文 Revit 2024 模板）
COLUMN_FAMILY_NAME = "混凝土-矩形-柱"
BEAM_FAMILY_NAME = "混凝土-矩形梁"
FLOOR_TYPE_NAME = "常规 - 150mm"

# 族名称备选（英文模板）
COLUMN_FAMILY_NAME_EN = "Concrete-Rectangular-Column"
BEAM_FAMILY_NAME_EN = "Concrete-Rectangular Beam"
FLOOR_TYPE_NAME_EN = "Generic - 150mm"

# 默认截面尺寸 (mm)
DEFAULT_COLUMN_SECTION = "500x500"
DEFAULT_BEAM_SECTION = "300x600"
DEFAULT_SLAB_THICKNESS = 120

# 默认结构参数
DEFAULT_FLOOR_COUNT = 5
DEFAULT_FLOOR_HEIGHT = 3600      # mm
DEFAULT_FIRST_FLOOR_HEIGHT = 4200  # mm（首层层高可不同）

# 轴网编号
GRID_LABELS_X = [str(i) for i in range(1, 20)]           # 1, 2, 3, ...
GRID_LABELS_Y = [chr(i) for i in range(65, 91)]          # A, B, C, ...

# 轴网超出柱中心的延伸长度 (mm)
GRID_EXTENSION = 1500
