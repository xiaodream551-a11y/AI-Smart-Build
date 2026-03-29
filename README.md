# AI-Smart-Build

[![Tests](https://github.com/xiaodream551-a11y/AI-Smart-Build/actions/workflows/test.yml/badge.svg)](https://github.com/xiaodream551-a11y/AI-Smart-Build/actions/workflows/test.yml)

AI SmartBuild — A natural-language-driven intelligent modeling system for Revit.

## 1. Introduction

AI SmartBuild is a Revit intelligent modeling plugin built on pyRevit, targeting structural frame scenarios. It supports parametric modeling, natural language modeling, Excel batch import, as well as element modification and deletion. The project follows a "multiple entry points + shared modeling engine" design, making it suitable for course demonstrations, portfolio presentations, and interview demos.

## 2. Features

- Parametric One-Click Generation: Enter parameters such as number of spans, stories, story height, and cross-sections to automatically generate grids, levels, columns, beams, and slabs.
- AI Chat Modeling: Use Chinese commands to drive LLM-generated JSON, which is then executed by the shared modeling engine.
- Excel Batch Import: Maintain an element list using a template and batch-import columns and beams.
- Element Modification & Deletion: Supports single modification, batch modification, and deletion by category/floor.
- Element Query: Supports count queries (`query_count`), detail/item listing (`query_detail`), and aggregate model summary (`query_summary`) via natural language.
- Model Data Export: One-click export of all columns, beams, and slabs to JSON and Excel files via the DataIO panel (`ExportModel` button).

## 3. System Architecture

```text
+--------------------------------------------------------------+
|                        Revit + pyRevit                       |
+--------------------------------------------------------------+
                |                  |                   |
                v                  v                   v
      +----------------+  +----------------+  +----------------+
      | Parametric      |  | AI Chat        |  | Operations     |
      | Entry           |  | Entry          |  | Entry          |
      | One-Click Gen   |  | Smart Chat     |  | Excel/Mod/Del  |
      +----------------+  +----------------+  +----------------+
                \               |               /
                 \              v              /
                  +---------------------------+
                  | Shared Modeling Dispatch   |
                  | & Parsing Layer            |
                  | ai/client.py              |
                  | ai/prompt.py              |
                  | ai/parser.py              |
                  +---------------------------+
                               |
                               v
                  +---------------------------+
                  |    Modeling Engine Layer   |
                  | engine/grid.py            |
                  | engine/level.py           |
                  | engine/column.py          |
                  | engine/beam.py            |
                  | engine/floor.py           |
                  | engine/modify.py          |
                  | engine/frame_generator.py |
                  | engine/element_utils.py   |
                  | engine/export.py          |
                  +---------------------------+
                               |
                               v
                  +---------------------------+
                  |     Revit API / DB        |
                  +---------------------------+
```

Core design principle: The parametric panel, AI chat, Excel import, modification/deletion, and data export entry points all share the same set of modeling engine functions and element utilities, reducing duplicate implementation and ensuring consistent behavior.

## 4. Requirements

- Revit 2024
- pyRevit 4.8+
- An OpenAI-compatible LLM API Key (DeepSeek, Zhipu GLM, Doubao, etc.)

## 5. Installation

For detailed installation instructions, see:

```text
docs/安装指南.md
```

1. Clone the repository:

   ```bash
   git clone <your-repo-url> AI-Smart-Build
   cd AI-Smart-Build
   ```

2. Quick install on Windows:
   On Windows, you can run:

   ```bash
   scripts\install_windows.bat
   ```

3. Register the pyRevit extension path:
   Add the directory containing `AISmartBuild.extension` to pyRevit's custom extension search path. You can do this through the pyRevit settings UI or via the pyRevit CLI installed on your machine.

4. Reload pyRevit:
   Execute pyRevit Reload in Revit, or restart Revit, so the new extension is recognized and loaded.

5. Configure the LLM API Key:
   Use one of the following methods instead of modifying the repository source code directly:
   - Environment variable: `DEEPSEEK_API_KEY` or `AI_SMART_BUILD_DEEPSEEK_API_KEY`
   - User configuration file: `~/.ai-smart-build/config.json`

   If the directory does not exist, create `~/.ai-smart-build/` first.

   Both `DEEPSEEK_*` and `LLM_*` key names are supported. For example, `LLM_API_KEY`, `LLM_MODEL`, and `LLM_API_URL` work as aliases for `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, and `DEEPSEEK_API_URL` respectively. This makes it easy to switch to any OpenAI-compatible API (e.g. Zhipu GLM, Doubao) by simply changing the URL, model name, and key.

   Example configuration file (DeepSeek):

   ```json
   {
     "DEEPSEEK_API_KEY": "your-api-key",
     "DEEPSEEK_MODEL": "deepseek-chat",
     "DEEPSEEK_API_URL": "https://api.deepseek.com/v1/chat/completions"
   }
   ```

   Example configuration file (Zhipu GLM, using LLM\_\* aliases):

   ```json
   {
     "LLM_API_KEY": "your-zhipu-api-key",
     "LLM_MODEL": "glm-4",
     "LLM_API_URL": "https://open.bigmodel.cn/api/paas/v4/chat/completions"
   }
   ```

   A sample file is also provided in the repository:

   ```text
   examples/config.example.json
   ```

## 5.1 Offline Local Verification

Without Revit / Windows, you can first run the offline tests and debug scripts:

```bash
python3 scripts/check_environment.py
python3 -m pytest
python3 tools/debug_ai_floor.py
python3 tools/run_ai_regression.py
```

For integration testing steps and checklist, see:

```text
docs/联调检查清单.md
```

## 6. Usage

### One-Click Generation

Enter span lengths, number of stories, story height, cross-sections, and other parameters to automatically generate a complete frame structure model.

![One-Click Generation](docs/screenshots/generate.png)

### Excel Import

Select `AISmartBuild.extension/templates/构件导入模板.xlsx` or a file with the same format to batch-import columns and beams.

![Excel Import](docs/screenshots/excel-import.png)

### Smart Chat

Enter modeling intent in Chinese, and the LLM converts it to standard JSON commands for execution.

Floor conventions:

- For beams, slabs, and floor-filtered modification/deletion/statistics, `1` refers to the first floor.
- For columns, `base_floor/top_floor` uses floor boundary numbers, e.g., `1 -> 2` means a first-floor column, `2 -> 3` means a second-floor column.

Chat shortcut commands:

- Enter `/help` to view example commands
- Enter `/reset` to reset the current conversation context
- Enter `/retry` to retry the last natural language input
- Enter `/replay` to directly replay the last normalized command
- Enter `/replaylog` to replay the last normalized command from the most recent session file
- Enter `/replayfail` to filter failed records from the most recent session file and replay; the list supports source filtering, action filtering, and previous/next navigation
- Enter `q` to exit the chat

Failed turns are additionally recorded with recovery suggestions in both the session Markdown and the companion JSON file, making it easy to decide whether to retry, replay, or rewrite the input during integration testing.
Even if the execution phase only returns a Chinese failure message without raising an exception, it will still be recorded as a failed turn and will not be mixed into the success log.
The failure replay list now directly shows the error summary and recovery suggestion summary, so you no longer need to open the session Markdown first during integration testing.
`/replayfail` will first filter by action when there is more than one type of failed action, then select the specific turn.
Failed actions and turns are now shown most-recent-first by default, with Chinese action names.
`/replayfail` will also first filter by source when there is more than one failure source, distinguishing between regular AI failures, `/replaylog` failures, and `/replayfail` secondary failures.
`/replayfail keyword` will first filter by failure reason summary and recovery suggestion summary based on the keyword, then proceed to the subsequent replay selection.
In the `/replayfail` failure list, additional "previous" and "next" navigation items are provided for sequential troubleshooting within the current filter results.

![Smart Chat](docs/screenshots/chat.png)

### Modify Elements

Supports single element cross-section modification, as well as batch modification of columns and beams by floor and cross-section criteria.

![Modify Elements](docs/screenshots/modify.png)

### Delete Elements

Supports deleting a single selected element, or batch-deleting columns, beams, and slabs by category and floor criteria.

![Delete Elements](docs/screenshots/delete.png)

### Export Model

Click the "Export Model" button in the DataIO panel to export all columns, beams, and slabs from the current model. Both JSON and Excel (.xlsx) files are generated, including per-element data and an aggregate summary sheet.

### Operation Logs

One-click generation, AI chat, Excel import, element modification, and element deletion all automatically generate operation logs, exported by default to `~/Documents/AI智建日志/`, facilitating demos, troubleshooting, and process documentation.

AI chat also exports an additional Markdown session record containing user input, raw model replies, normalized JSON commands, and execution results, useful for replaying integration testing sessions.
The session record also includes a summary of action types per turn, success/failure counts, and AI request timing statistics.

## 7. AI Chat Examples

### Example 1

User command:

```text
在 6000,0 位置创建一根 500x500 的柱，从 1 层到 2 层
```

JSON output:

```json
{
  "action": "create_column",
  "params": {
    "x": 6000,
    "y": 0,
    "base_floor": 1,
    "top_floor": 2,
    "section": "500x500"
  }
}
```

### Example 2

User command:

```text
在第 2 层从 0,0 到 6000,0 创建一根 300x600 的梁
```

JSON output:

```json
{
  "action": "create_beam",
  "params": {
    "start_x": 0,
    "start_y": 0,
    "end_x": 6000,
    "end_y": 0,
    "floor": 2,
    "section": "300x600"
  }
}
```

### Example 3

User command:

```text
把第 2 层所有 400x400 的柱改成 500x500
```

JSON output:

```json
{
  "action": "modify_section",
  "params": {
    "element_type": "column",
    "floor": 2,
    "old_section": "400x400",
    "new_section": "500x500"
  }
}
```

### Example 4

User command:

```text
删除第 1 层所有梁
```

JSON output:

```json
{
  "action": "delete_element",
  "params": {
    "element_type": "beam",
    "floor": 1
  }
}
```

### Example 5

User command:

```text
列出第 3 层所有柱子的详细信息
```

JSON output:

```json
{
  "action": "query_detail",
  "params": {
    "element_type": "column",
    "floor": 3
  }
}
```

### Example 6

User command:

```text
汇总一下整个模型的构件数量
```

JSON output:

```json
{
  "action": "query_summary",
  "params": {}
}
```

## 8. Project Structure

```text
AI-Smart-Build/
├── .github/
│   └── workflows/
│       └── test.yml
├── README.md
├── CLAUDE.md
├── create_template.py
├── requirements.txt
├── requirements-dev.txt
├── AI智建_项目方案书.docx
├── docs/
│   └── screenshots/
│       ├── .gitkeep
│       └── README.md
├── tests/
│   ├── conftest.py
│   ├── test_parser.py
│   ├── test_ai_client.py
│   └── ... (13 test files)
├── tools/
│   ├── offline_runtime.py
│   ├── debug_ai_floor.py
│   └── run_ai_regression.py
└── AISmartBuild.extension/
    ├── startup.py
    ├── AISmartBuild.tab/
    │   ├── FrameModel.panel/
    │   │   ├── GenerateFrame.pushbutton/
    │   │   └── ExcelImport.pushbutton/
    │   ├── AIChat.panel/
    │   │   └── SmartChat.pushbutton/
    │   ├── ElementOps.panel/
    │   │   ├── ModifyElement.pushbutton/
    │   │   └── DeleteElement.pushbutton/
    │   ├── DataIO.panel/
    │   │   └── ExportModel.pushbutton/
    │   └── Help.panel/
    │       └── About.pushbutton/
    ├── lib/
    │   ├── ai/
    │   │   ├── __init__.py
    │   │   ├── client.py
    │   │   ├── prompt.py
    │   │   ├── parser.py
    │   │   ├── chat_common.py
    │   │   ├── chat_controller.py
    │   │   ├── conversation_parser.py
    │   │   ├── recovery.py
    │   │   └── replay.py
    │   ├── engine/
    │   │   ├── __init__.py
    │   │   ├── grid.py
    │   │   ├── level.py
    │   │   ├── column.py
    │   │   ├── beam.py
    │   │   ├── floor.py
    │   │   ├── frame_generator.py
    │   │   ├── modify.py
    │   │   ├── element_utils.py
    │   │   ├── export.py
    │   │   └── logger.py
    │   ├── config.py
    │   └── utils.py
    └── templates/
        └── 构件导入模板.xlsx
```

Directory descriptions:

- `AISmartBuild.extension/AISmartBuild.tab/`: pyRevit Ribbon button entry points.
- `AISmartBuild.extension/AISmartBuild.tab/DataIO.panel/`: Data export panel (JSON + Excel model export).
- `AISmartBuild.extension/lib/engine/`: Shared modeling engine wrapping Revit API operations.
- `AISmartBuild.extension/lib/engine/frame_generator.py`: Orchestrates the full frame generation pipeline (grids, levels, columns, beams, slabs).
- `AISmartBuild.extension/lib/engine/element_utils.py`: Shared element-property helper functions used by both the parser and the export module.
- `AISmartBuild.extension/lib/engine/export.py`: Model data export to JSON and Excel (used by the DataIO panel).
- `AISmartBuild.extension/lib/ai/`: AI integration, prompt templates, and command dispatch.
- `AISmartBuild.extension/templates/`: Excel import templates.
- `AISmartBuild.extension/startup.py`: Outputs version and runtime environment info when the extension loads.
- `create_template.py`: Helper script to generate the Excel import template.

## 9. Tech Stack

- pyRevit
- Revit API
- DeepSeek / Any OpenAI-compatible LLM API
- openpyxl
- WPF

## 10. License

MIT
