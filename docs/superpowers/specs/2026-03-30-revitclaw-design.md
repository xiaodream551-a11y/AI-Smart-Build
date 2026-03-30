# RevitClaw 设计文档

## 概述

手机浏览器远程控制 Revit 建模。用户在手机输入中文指令，经 LLM 解析为 JSON 命令，在 Revit 中执行，返回文字结果 + 截图。

## 使用场景

个人演示/毕设展示，单用户，局域网访问，无需认证。

## 架构

```
手机浏览器 ──HTTP──> RevitClaw Server ──> 智谱 GLM API
                           │                    │
                           │              JSON 命令
                           │                    │
                     Idling 事件回调 <───────────┘
                           │
                    AI SmartBuild Engine
                     (create_column 等)
                           │
                     截图 -> 返回手机
```

两套 server 实现，同一套 API 接口：

|             | Mac 离线          | Revit 实机                     |
| ----------- | ----------------- | ------------------------------ |
| 运行环境    | CPython 3         | IronPython 2.7（Revit 进程内） |
| HTTP server | Flask             | .NET HttpListener              |
| LLM 调用    | urllib            | .NET WebClient                 |
| 命令执行    | 不执行，返回 JSON | Idling 回调 -> engine          |
| 截图        | 无                | Revit ExportImage              |

## Revit 端组件

```
AISmartBuild.extension/
├── RevitClaw.pushbutton/
│   └── script.py          # pushbutton：启动/停止 server
│
└── lib/
    └── revitclaw/
        ├── http_server.py  # HttpListener 封装，路由分发
        ├── llm_client.py   # .NET WebClient 调智谱 API
        ├── handler.py      # Idling 回调，执行命令 + 截图
        └── screenshot.py   # Revit 视图导出为图片
```

职责划分：

- **http_server.py** -- 后台线程跑 HttpListener，收到请求后调 llm_client，得到命令后塞进队列
- **handler.py** -- 注册 Idling 事件，每次回调检查队列，有命令就执行（调现有 engine），执行完截图，结果写回响应队列。唯一接触 Revit API 的文件。
- **llm_client.py** -- 用 .NET System.Net.WebClient 发 HTTPS 请求（避免 IronPython urllib SSL 问题）
- **screenshot.py** -- 调 Document.ExportImage / ImageExportOptions 导出当前 3D 视图为 PNG

## 通信流程

一次完整请求：

1. 手机发 POST /api/chat `{"message": "在1-A创建柱子"}`
2. http_server 收到请求，调 llm_client
3. llm_client 调智谱 API -> 返回 JSON 命令 `{"action": "create_column", "params": {...}}`
4. http_server 把命令塞进 command_queue，阻塞等待结果
5. Revit 主线程 Idling 回调触发（约每 100ms），handler 从 command_queue 取出命令
6. handler 调 engine.create_column() 执行
7. handler 调 screenshot.capture() 截图 -> 保存为临时 PNG
8. handler 把结果写入 result_queue `{"success": true, "message": "已创建柱子", "screenshot": "/tmp/xxx.png"}`
9. http_server 拿到结果，返回给手机 `{"reply": "...", "action": "create_column", "screenshot_url": "/api/screenshot/xxx.png"}`
10. 手机端 chat.html 显示文字回复 + 截图

请求线程阻塞等 Idling 执行完（超时 30s），一次请求拿到结果+截图，不需要轮询。

## chat.html 改动

- 截图展示：收到 screenshot_url 时在消息气泡里插入 img，点击可放大
- 加载状态：发送后显示"执行中..."动画
- 连接状态细化：区分"已连接(离线)" / "已连接(Revit)" / "未连接"

## API 路由

所有路由两套 server 保持一致：

| 方法 | 路由                   | 说明                         |
| ---- | ---------------------- | ---------------------------- |
| GET  | /                      | 返回 chat.html               |
| GET  | /api/health            | 健康检查 + 模式              |
| POST | /api/chat              | 发送消息，返回回复+命令+截图 |
| GET  | /api/screenshot/<name> | 返回截图文件                 |

## 新增文件

| 文件                                                  | 说明                     |
| ----------------------------------------------------- | ------------------------ |
| AISmartBuild.extension/lib/revitclaw/http_server.py   | HttpListener HTTP server |
| AISmartBuild.extension/lib/revitclaw/llm_client.py    | .NET WebClient LLM 调用  |
| AISmartBuild.extension/lib/revitclaw/handler.py       | Idling 回调 + 命令执行   |
| AISmartBuild.extension/lib/revitclaw/screenshot.py    | Revit 截图导出           |
| AISmartBuild.extension/RevitClaw.pushbutton/script.py | 启动/停止按钮            |

## 修改文件

| 文件                | 改动                                   |
| ------------------- | -------------------------------------- |
| revitclaw/chat.html | 截图展示 + 加载动画                    |
| revitclaw/server.py | 加 /api/screenshot/<name> 静态文件路由 |

## 测试策略

所有测试在 Mac 上用 pytest 跑，不依赖 Revit：

- **http_server.py** -- mock HttpListener，测路由分发、请求解析、超时处理
- **llm_client.py** -- mock WebClient，测请求构建、响应解析、错误处理
- **handler.py** -- mock DB + engine，测命令分发、队列消费、截图调用
- **screenshot.py** -- mock Revit Document，测导出参数设置
- **chat.html** -- 现有 server.py 测试已覆盖 API，前端手动验证
