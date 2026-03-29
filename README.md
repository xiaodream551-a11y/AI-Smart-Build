# AI-Smart-Build

AI 智建 — 自然语言驱动的 Revit 智能建模系统。

## 1. 项目简介

AI 智建是一个基于 pyRevit 的 Revit 智能建模插件，面向结构框架场景，支持参数化建模、自然语言建模、Excel 批量导入，以及构件的修改与删除操作。项目采用“多入口 + 共享建模引擎”的设计，适合课程展示、作品集呈现和面试演示。

## 2. 功能特性

- 参数化一键建模：输入层数、层高、跨距、截面等参数，自动生成轴网、标高、柱、梁、板。
- AI 对话建模：通过中文指令驱动大模型输出 JSON，再由共享建模引擎执行具体建模动作。
- Excel 批量导入：按模板维护构件清单，批量导入柱、梁等构件。
- 构件修改删除：支持单个修改、批量修改，以及按类别/楼层删除构件。

## 3. 系统架构

```text
+--------------------------------------------------------------+
|                        Revit + pyRevit                       |
+--------------------------------------------------------------+
                |                  |                   |
                v                  v                   v
      +----------------+  +----------------+  +----------------+
      | 参数化按钮入口 |  | AI 对话入口    |  | 运维入口       |
      | 一键生成       |  | 智能对话       |  | Excel/修改/删除 |
      +----------------+  +----------------+  +----------------+
                \               |               /
                 \              v              /
                  +---------------------------+
                  |   共享建模调度与解析层    |
                  | ai/client.py              |
                  | ai/prompt.py              |
                  | ai/parser.py              |
                  +---------------------------+
                               |
                               v
                  +---------------------------+
                  |      建模引擎层           |
                  | engine/grid.py            |
                  | engine/level.py           |
                  | engine/column.py          |
                  | engine/beam.py            |
                  | engine/floor.py           |
                  | engine/modify.py          |
                  +---------------------------+
                               |
                               v
                  +---------------------------+
                  |     Revit API / DB        |
                  +---------------------------+
```

核心设计原则：参数面板、AI 对话、Excel 导入、修改删除四类入口，共享同一套建模引擎函数，降低重复实现成本，保证行为一致性。

## 4. 环境要求

- Revit 2024
- pyRevit 4.8+
- DeepSeek API Key

## 5. 安装步骤

1. 克隆仓库到本地：

   ```bash
   git clone <your-repo-url> AI-Smart-Build
   cd AI-Smart-Build
   ```

2. 注册 pyRevit 扩展路径：
   将包含 `AI智建.extension` 的目录加入 pyRevit 的自定义扩展搜索路径。可通过 pyRevit 设置界面添加，也可使用你本机已安装的 pyRevit CLI 完成配置。

3. 重载 pyRevit：
   在 Revit 中执行 pyRevit Reload，或重启 Revit，使新扩展被识别并加载。

4. 配置 DeepSeek API Key：
   推荐使用以下两种方式之一，而不是直接修改仓库源码：

   - 环境变量：`DEEPSEEK_API_KEY` 或 `AI_SMART_BUILD_DEEPSEEK_API_KEY`
   - 用户配置文件：`~/.ai-smart-build/config.json`

   如果目录不存在，请先创建 `~/.ai-smart-build/`。

   配置文件示例：

   ```json
   {
     "DEEPSEEK_API_KEY": "你的 API Key",
     "DEEPSEEK_MODEL": "deepseek-chat",
     "DEEPSEEK_API_URL": "https://api.deepseek.com/v1/chat/completions"
   }
   ```

   仓库内也提供了示例文件：

   ```text
   examples/config.example.json
   ```

## 5.1 本地离线检查

在没有 Revit / Windows 的环境下，可以先运行离线测试与调试脚本：

```bash
python3 -m pytest
python3 tools/debug_ai_floor.py
python3 tools/run_ai_regression.py
```

联调步骤与检查项见：

```text
docs/联调检查清单.md
```

## 6. 使用说明

### 一键生成

输入跨距、层数、层高、截面等参数后，自动生成完整框架结构模型。

![一键生成](docs/screenshots/generate.png)

### Excel 导入

选择 `AI智建.extension/templates/构件导入模板.xlsx` 或同格式清单文件，批量导入柱、梁构件。

![Excel导入](docs/screenshots/excel-import.png)

### 智能对话

通过中文输入建模意图，由大模型转换为标准 JSON 指令并执行。

楼层约定：
- 梁、板以及按楼层筛选的修改/删除/统计中，`1` 表示首层。
- 柱的 `base_floor/top_floor` 使用楼层边界编号，例如 `1 -> 2` 表示首层柱，`2 -> 3` 表示二层柱。

对话快捷命令：
- 输入 `/help` 查看示例指令
- 输入 `/reset` 重置当前对话上下文
- 输入 `/retry` 重试上一条自然语言输入
- 输入 `/replay` 直接重放上一条归一化指令
- 输入 `/replaylog` 从最近一次会话文件重放上一条归一化指令
- 输入 `/replayfail` 从最近一次会话文件筛选失败记录并重放，列表支持来源筛选、动作筛选和上一条/下一条导航
- 输入 `q` 退出对话

失败轮次会在会话 Markdown 和同名 JSON 中额外记录恢复建议，便于联调时快速判断下一步该重试、重放还是改写输入。
即使执行阶段只是返回中文失败文本而没有抛异常，也会按失败轮次记录，不再混入成功日志。
失败回放列表现在会直接显示错误摘要和恢复建议摘要，联调时不用再先翻会话 Markdown。
`/replayfail` 在失败动作不止一种时，会先按动作筛选，再选择具体轮次。
失败动作和轮次现在默认按最近失败优先显示，并带中文动作名。
`/replayfail` 在失败来源不止一种时，也会先按来源筛选，能区分普通 AI 失败、`/replaylog` 失败和 `/replayfail` 二次失败。
`/replayfail 关键字` 会基于失败原因摘要和恢复建议摘要先做关键字筛选，再进入后续回放选择。
在 `/replayfail` 的失败列表中，会额外提供“上一条”“下一条”导航项，便于沿着当前筛选结果连续排查。

![智能对话](docs/screenshots/chat.png)

### 修改构件

支持单个构件截面修改，也支持按楼层和截面条件批量修改柱、梁。

![修改构件](docs/screenshots/modify.png)

### 删除构件

支持删除单个选中构件，或按类别和楼层条件批量删除柱、梁、板。

![删除构件](docs/screenshots/delete.png)

### 操作日志

一键生成、AI 对话、Excel 导入、修改构件、删除构件都会自动生成操作日志，默认导出到 `~/Documents/AI智建日志/`，便于演示、排错和过程留档。

AI 对话还会额外导出一份 Markdown 会话记录，包含用户输入、模型原始回复、归一化后的 JSON 指令以及执行结果，便于回放联调过程。
该会话记录还会汇总每轮动作类型、成功/失败数量，以及 AI 请求耗时统计。

## 7. AI 对话示例

### 示例 1

用户指令：

```text
在 6000,0 位置创建一根 500x500 的柱，从 1 层到 2 层
```

JSON 输出：

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

### 示例 2

用户指令：

```text
在第 2 层从 0,0 到 6000,0 创建一根 300x600 的梁
```

JSON 输出：

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

### 示例 3

用户指令：

```text
把第 2 层所有 400x400 的柱改成 500x500
```

JSON 输出：

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

### 示例 4

用户指令：

```text
删除第 1 层所有梁
```

JSON 输出：

```json
{
  "action": "delete_element",
  "params": {
    "element_type": "beam",
    "floor": 1
  }
}
```

## 8. 项目结构

```text
AI-Smart-Build/
├── README.md
├── CLAUDE.md
├── create_template.py
├── AI智建_项目方案书.docx
└── AI智建.extension/
    ├── AI智建.tab/
    │   ├── 框架建模.panel/
    │   │   ├── 一键生成.pushbutton/
    │   │   └── Excel导入.pushbutton/
    │   ├── AI对话.panel/
    │   │   └── 智能对话.pushbutton/
    │   └── 构件操作.panel/
    │       ├── 修改构件.pushbutton/
    │       └── 删除构件.pushbutton/
    ├── lib/
    │   ├── ai/
    │   │   ├── client.py
    │   │   ├── prompt.py
    │   │   └── parser.py
    │   ├── engine/
    │   │   ├── grid.py
    │   │   ├── level.py
    │   │   ├── column.py
    │   │   ├── beam.py
    │   │   ├── floor.py
    │   │   ├── frame_generator.py
    │   │   └── modify.py
    │   ├── config.py
    │   └── utils.py
    └── templates/
        └── 构件导入模板.xlsx
```

目录说明：

- `AI智建.extension/AI智建.tab/`：pyRevit Ribbon 按钮入口。
- `AI智建.extension/lib/engine/`：共享建模引擎，封装 Revit API 操作。
- `AI智建.extension/lib/ai/`：AI 能力接入、Prompt 模板与指令分发。
- `AI智建.extension/templates/`：Excel 导入模板。
- `create_template.py`：生成 Excel 导入模板的辅助脚本。

## 9. 技术栈

- pyRevit
- Revit API
- DeepSeek
- openpyxl
- WPF

## 10. License

MIT
