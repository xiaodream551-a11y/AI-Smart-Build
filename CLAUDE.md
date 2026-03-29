# AI SmartBuild — Natural-Language-Driven Intelligent Modeling System for Revit

## Project Overview

A Revit plugin built on pyRevit with two core capabilities:

1. **Parametric Frame Structure One-Click Generation**: Enter structural parameters (number of stories, story height, number of spans, span lengths, cross-sections) to automatically generate a complete frame structure model (grids, levels, columns, beams, slabs).
2. **Natural Language Intelligent Modeling**: Control Revit modeling through Chinese dialogue; a large language model parses natural language into structured JSON commands, which are then executed by the shared modeling engine.

## Tech Stack

- **BIM Platform**: Revit 2024 (Education Edition)
- **Development Framework**: pyRevit (Python)
- **LLM API**: DeepSeek (excellent Chinese support, low cost)
- **Data Processing**: openpyxl (Excel), json (command parsing)
- **UI**: pyRevit forms / WPF

## Architecture

```
Presentation Layer -> Parametric Panel (Form) / AI Chat Panel (Natural Language)
                        |                          |
                                            LLM API -> JSON Commands
                        |                          |
                     Modeling Engine (Shared Core Functions)
                        |
                    Revit API (pyRevit)
```

Key design: Both entry points share the same modeling engine (create_column/create_beam/create_slab, etc.).

## Core Function List

- `create_column(x, y, base_level, top_level, section)`
- `create_beam(start_point, end_point, level, section)`
- `create_floor(boundary_curves, level, floor_type)`
- `create_grid(name, start_point, end_point)`
- `modify_element()` — Modify element properties
- `delete_element()` — Delete an element

## AI Chat JSON Command Format

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

Supported actions: create_column, create_beam, create_slab, modify_section, delete_element, generate_frame, query_count, query_detail, query_summary

## Development Conventions

- All natural-language output uses Simplified Chinese
- Code comments may be in Chinese
- Variable and function names use English (snake_case)
- Revit API operations must be executed within a Transaction

## Development Constraints

- Every new feature must have an offline test (runnable with `pytest` on Mac, no Revit dependency)
- New actions must be updated in all 6 locations: parser alias, recovery, logger, prompt, regression cases, dispatch test
- Functions under `engine/` must not directly `from pyrevit import DB`; DB is passed in as a parameter (to ensure offline testability)
- Shared element-property functions used by both `parser.py` and `export.py` belong in `engine/element_utils.py`; duplicate implementations are prohibited
- Regression case file: `examples/ai_reply_regression_cases.json`; new actions must include corresponding test cases

## Project Files

- `AI智建_项目方案书.docx` — Full project proposal (architecture, feature design, 12-week plan)
