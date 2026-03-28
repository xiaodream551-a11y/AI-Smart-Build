# AI 智建 — 自然语言驱动的 Revit 智能建模系统

## 项目概述

基于 pyRevit 的 Revit 插件，包含两大核心功能：

1. **参数化框架结构一键建模**：输入结构参数（层数、层高、跨数、跨距、截面），自动生成完整框架结构模型（轴网、标高、柱、梁、板）
2. **自然语言智能建模**：通过中文对话控制 Revit 建模，大语言模型将自然语言解析为结构化 JSON 指令，调用共享的建模引擎执行

## 技术栈

- **BIM 平台**：Revit 2024（教育版）
- **开发框架**：pyRevit（Python）
- **大模型 API**：DeepSeek（中文优秀、成本低）
- **数据处理**：openpyxl（Excel）、json（指令解析）
- **UI**：pyRevit forms / WPF

## 架构设计

```
表现层 → 参数化面板（表单） / AI 对话面板（自然语言）
            ↓                      ↓
                              大模型 API → JSON 指令
            ↓                      ↓
         建模引擎（共享核心函数）
            ↓
        Revit API (pyRevit)
```

关键设计：两个入口共享同一套建模引擎（create_column/create_beam/create_slab 等）。

## 核心函数清单

- `create_column(x, y, base_level, top_level, section)`
- `create_beam(start_point, end_point, level, section)`
- `create_floor(boundary_curves, level, floor_type)`
- `create_grid(name, start_point, end_point)`
- `modify_element()` — 修改构件属性
- `delete_element()` — 删除构件

## AI 对话 JSON 指令格式

```json
{
  "action": "create_beam",
  "params": {
    "start_grid": "A",
    "end_grid": "B",
    "section": "300x700",
    "elevation": 3.6,
    "floor": 1
  }
}
```

支持的 action：create_column, create_beam, create_slab, modify_section, delete_element, generate_frame, query_count

## 开发规范

- 所有自然语言输出使用简体中文
- 代码注释可以用中文
- 变量名、函数名使用英文（snake_case）
- Revit API 操作必须在 Transaction 内执行

## 项目文件

- `AI智建_项目方案书.docx` — 完整方案书（含架构、功能设计、12 周计划）
