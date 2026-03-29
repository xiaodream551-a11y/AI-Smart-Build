# UI 优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 AI智建 pyRevit 插件的 UI 界面 — 调整面板顺序、添加双色图标、美化参数表单、新建聊天窗口

**Architecture:** pyRevit 扩展的 UI 通过文件夹命名排序面板、`icon.png` 显示按钮图标、内嵌 XAML 定义 WPF 窗口。本计划通过 Pillow 离线生成双色图标，修改 XAML 美化表单，新建 WPF 聊天窗口替换 `forms.ask_for_string()` 循环。

**Tech Stack:** Python 3, Pillow (图标生成), WPF/XAML (表单), pyRevit bundle.yaml (面板配置)

**配色方案:** 深蓝 #1E3A5F (主色) + 橙色 #FF6D00 (辅色)

---

### Task 1: 面板排序 — 调整面板显示顺序

**Files:**

- Modify: `AISmartBuild.extension/AISmartBuild.tab/AIChat.panel/bundle.yaml`
- Modify: `AISmartBuild.extension/AISmartBuild.tab/FrameModel.panel/bundle.yaml`
- Modify: `AISmartBuild.extension/AISmartBuild.tab/ElementOps.panel/bundle.yaml`
- Modify: `AISmartBuild.extension/AISmartBuild.tab/DataIO.panel/bundle.yaml`
- Modify: `AISmartBuild.extension/AISmartBuild.tab/Help.panel/bundle.yaml`

pyRevit 默认按文件夹字母排序面板。通过在 `bundle.yaml` 中添加 `sort_priority` 字段控制顺序（数字越小越靠前）。

目标顺序：AI对话(1) → 框架建模(2) → 构件操作(3) → 数据导出(4) → 帮助(5)

- [ ] **Step 1: 修改 AIChat.panel/bundle.yaml**

```yaml
title: AI对话
sort_priority: 1
```

- [ ] **Step 2: 修改 FrameModel.panel/bundle.yaml**

```yaml
title: 框架建模
sort_priority: 2
```

- [ ] **Step 3: 修改 ElementOps.panel/bundle.yaml**

```yaml
title: 构件操作
sort_priority: 3
```

- [ ] **Step 4: 修改 DataIO.panel/bundle.yaml**

```yaml
title: 数据导出
sort_priority: 4
```

- [ ] **Step 5: 修改 Help.panel/bundle.yaml**

```yaml
title: 帮助
sort_priority: 5
```

- [ ] **Step 6: Commit**

```bash
git add AISmartBuild.extension/AISmartBuild.tab/*/bundle.yaml
git commit -m "feat(ui): reorder panels — AI对话 first"
```

---

### Task 2: 图标生成 — 用 Pillow 离线生成双色图标

**Files:**

- Create: `scripts/generate_icons.py`
- Create: 7 个 `icon.png` 文件（每个 pushbutton 文件夹各一个）

用 Pillow 的 ImageDraw 绘制 96x96 像素的双色图标。深蓝 #1E3A5F 为主体形状，橙色 #FF6D00 为高亮/装饰元素。透明背景。

每个图标的设计：

| 按钮      | 主体(深蓝)    | 点缀(橙色)     |
| --------- | ------------- | -------------- |
| 智能对话  | 聊天气泡轮廓  | 右上角 AI 星芒 |
| Excel导入 | 表格网格      | 左下角向上箭头 |
| 一键生成  | 建筑/立体方块 | 闪电符号       |
| 修改构件  | 扳手/齿轮     | 铅笔尖         |
| 删除构件  | 垃圾桶轮廓    | X 标记         |
| 导出模型  | 文档轮廓      | 向下箭头       |
| 关于      | 圆圈          | i 字母         |

- [ ] **Step 1: 创建图标生成脚本**

创建 `scripts/generate_icons.py`，包含每个图标的绘制函数：

```python
# -*- coding: utf-8 -*-
"""Generate 96x96 dual-color PNG icons for pyRevit buttons."""

import os
import math
from PIL import Image, ImageDraw, ImageFont

ICON_SIZE = 96
PRIMARY = (30, 58, 95)       # #1E3A5F deep blue
ACCENT = (255, 109, 0)       # #FF6D00 orange
BG = (0, 0, 0, 0)            # transparent

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "AISmartBuild.extension", "AISmartBuild.tab"
)

BUTTONS = {
    "AIChat.panel/SmartChat.pushbutton": "smart_chat",
    "FrameModel.panel/ExcelImport.pushbutton": "excel_import",
    "FrameModel.panel/GenerateFrame.pushbutton": "generate_frame",
    "ElementOps.panel/ModifyElement.pushbutton": "modify_element",
    "ElementOps.panel/DeleteElement.pushbutton": "delete_element",
    "DataIO.panel/ExportModel.pushbutton": "export_model",
    "Help.panel/About.pushbutton": "about",
}


def _new_icon():
    return Image.new("RGBA", (ICON_SIZE, ICON_SIZE), BG)


def draw_smart_chat(img):
    """Chat bubble with AI sparkle."""
    d = ImageDraw.Draw(img)
    # Chat bubble body (deep blue)
    d.rounded_rectangle([12, 16, 72, 60], radius=10, fill=PRIMARY)
    # Bubble tail
    d.polygon([(20, 60), (28, 60), (16, 74)], fill=PRIMARY)
    # Three dots inside bubble
    for cx in [30, 42, 54]:
        d.ellipse([cx-3, 34, cx+3, 40], fill=(255, 255, 255))
    # AI sparkle (orange) — four-pointed star top-right
    _draw_sparkle(d, 78, 20, 12, ACCENT)


def draw_excel_import(img):
    """Spreadsheet grid with upload arrow."""
    d = ImageDraw.Draw(img)
    # Table grid (deep blue)
    d.rectangle([18, 12, 68, 72], outline=PRIMARY, width=3)
    # Horizontal lines
    for y in [32, 52]:
        d.line([(18, y), (68, y)], fill=PRIMARY, width=2)
    # Vertical line
    d.line([(43, 12), (43, 72)], fill=PRIMARY, width=2)
    # Upload arrow (orange) bottom-right
    _draw_arrow_up(d, 76, 58, 14, ACCENT)


def draw_generate_frame(img):
    """3D building block with lightning bolt."""
    d = ImageDraw.Draw(img)
    # Front face
    d.rectangle([16, 30, 56, 78], outline=PRIMARY, width=3, fill=PRIMARY + (60,))
    # Top face (parallelogram)
    d.polygon([(16, 30), (36, 14), (76, 14), (56, 30)], outline=PRIMARY, fill=PRIMARY + (40,))
    d.line([(16, 30), (36, 14)], fill=PRIMARY, width=3)
    d.line([(36, 14), (76, 14)], fill=PRIMARY, width=3)
    d.line([(76, 14), (56, 30)], fill=PRIMARY, width=3)
    # Right face
    d.polygon([(56, 30), (76, 14), (76, 62), (56, 78)], outline=PRIMARY, fill=PRIMARY + (30,))
    d.line([(56, 30), (76, 14)], fill=PRIMARY, width=3)
    d.line([(76, 14), (76, 62)], fill=PRIMARY, width=3)
    d.line([(76, 62), (56, 78)], fill=PRIMARY, width=3)
    # Lightning bolt (orange)
    d.polygon([(34, 36), (44, 36), (38, 52), (48, 52), (30, 72), (36, 54), (28, 54)],
              fill=ACCENT)


def draw_modify_element(img):
    """Wrench with pencil tip accent."""
    d = ImageDraw.Draw(img)
    # Pencil body (deep blue) — diagonal
    d.line([(22, 74), (70, 26)], fill=PRIMARY, width=8)
    # Pencil tip (orange)
    d.polygon([(16, 80), (22, 74), (28, 68), (10, 86)], fill=ACCENT)
    # Eraser end
    d.line([(66, 30), (74, 22)], fill=PRIMARY + (180,), width=8)
    d.line([(70, 26), (76, 20)], fill=(200, 200, 200), width=6)
    # Edit lines (accent)
    for y in [38, 48]:
        d.line([(50, y), (82, y)], fill=ACCENT, width=2)


def draw_delete_element(img):
    """Trash can with X mark."""
    d = ImageDraw.Draw(img)
    # Trash can body (deep blue)
    d.rounded_rectangle([24, 28, 62, 80], radius=4, outline=PRIMARY, width=3)
    # Lid
    d.line([(18, 28), (68, 28)], fill=PRIMARY, width=3)
    # Handle
    d.rounded_rectangle([34, 18, 52, 28], radius=3, outline=PRIMARY, width=3)
    # X mark (orange)
    d.line([(34, 42), (52, 66)], fill=ACCENT, width=4)
    d.line([(52, 42), (34, 66)], fill=ACCENT, width=4)


def draw_export_model(img):
    """Document with download arrow."""
    d = ImageDraw.Draw(img)
    # Document (deep blue)
    d.polygon([(20, 10), (56, 10), (70, 24), (70, 82), (20, 82)],
              outline=PRIMARY, fill=None)
    d.line([(20, 10), (56, 10)], fill=PRIMARY, width=3)
    d.line([(56, 10), (70, 24)], fill=PRIMARY, width=3)
    d.line([(70, 24), (70, 82)], fill=PRIMARY, width=3)
    d.line([(70, 82), (20, 82)], fill=PRIMARY, width=3)
    d.line([(20, 82), (20, 10)], fill=PRIMARY, width=3)
    # Folded corner
    d.polygon([(56, 10), (56, 24), (70, 24)], outline=PRIMARY, fill=PRIMARY + (40,))
    d.line([(56, 10), (56, 24)], fill=PRIMARY, width=2)
    d.line([(56, 24), (70, 24)], fill=PRIMARY, width=2)
    # Text lines
    for y in [40, 52, 64]:
        d.line([(30, y), (60, y)], fill=PRIMARY + (100,), width=2)
    # Download arrow (orange)
    _draw_arrow_down(d, 76, 66, 14, ACCENT)


def draw_about(img):
    """Info circle."""
    d = ImageDraw.Draw(img)
    # Circle (deep blue)
    d.ellipse([14, 14, 82, 82], outline=PRIMARY, width=4)
    # "i" letter (orange)
    d.ellipse([43, 28, 53, 38], fill=ACCENT)
    d.rounded_rectangle([43, 44, 53, 70], radius=2, fill=ACCENT)


# ---- Helper drawing functions ----

def _draw_sparkle(d, cx, cy, size, color):
    """Draw a four-pointed star / AI sparkle."""
    hs = size // 2
    qs = size // 4
    d.polygon([
        (cx, cy - hs),
        (cx + qs, cy - qs),
        (cx + hs, cy),
        (cx + qs, cy + qs),
        (cx, cy + hs),
        (cx - qs, cy + qs),
        (cx - hs, cy),
        (cx - qs, cy - qs),
    ], fill=color)


def _draw_arrow_up(d, cx, cy, size, color):
    """Draw an upward arrow."""
    hs = size // 2
    d.polygon([(cx - hs, cy), (cx, cy - hs), (cx + hs, cy)], fill=color)
    d.rectangle([cx - 3, cy, cx + 3, cy + hs], fill=color)


def _draw_arrow_down(d, cx, cy, size, color):
    """Draw a downward arrow."""
    hs = size // 2
    d.polygon([(cx - hs, cy), (cx, cy + hs), (cx + hs, cy)], fill=color)
    d.rectangle([cx - 3, cy - hs, cx + 3, cy], fill=color)


def main():
    for rel_path, func_name in BUTTONS.items():
        out_dir = os.path.join(OUTPUT_DIR, rel_path)
        out_path = os.path.join(out_dir, "icon.png")

        img = _new_icon()
        draw_fn = globals()["draw_" + func_name]
        draw_fn(img)
        img.save(out_path, "PNG")
        print("Generated: {}".format(out_path))

    print("\nDone! {} icons generated.".format(len(BUTTONS)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行脚本生成图标**

```bash
cd /Users/xiaojunming/Desktop/AI智建
python3 scripts/generate_icons.py
```

Expected: 7 个 `icon.png` 文件被创建到各 `.pushbutton` 目录下。

- [ ] **Step 3: 验证图标文件**

```bash
python3 -c "
from PIL import Image
import os
tab = 'AISmartBuild.extension/AISmartBuild.tab'
for panel in os.listdir(tab):
    panel_path = os.path.join(tab, panel)
    if not panel.endswith('.panel'):
        continue
    for btn in os.listdir(panel_path):
        if not btn.endswith('.pushbutton'):
            continue
        icon = os.path.join(panel_path, btn, 'icon.png')
        if os.path.exists(icon):
            img = Image.open(icon)
            print('{}: {}x{} {}'.format(btn, img.width, img.height, img.mode))
        else:
            print('{}: MISSING'.format(btn))
"
```

Expected: 7 行输出，每个都是 `96x96 RGBA`。

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_icons.py
git add AISmartBuild.extension/AISmartBuild.tab/*/*/icon.png
git commit -m "feat(ui): add dual-color icons for all buttons"
```

---

### Task 3: GenerateFrame 表单美化 — 重写 XAML

**Files:**

- Modify: `AISmartBuild.extension/AISmartBuild.tab/FrameModel.panel/GenerateFrame.pushbutton/script.py:20-118`

将当前的纯白 StackPanel 布局改为带深蓝标题栏、分组卡片、美化按钮的现代风格表单。

- [ ] **Step 1: 替换 XAML 布局**

将 `script.py` 中的 `layout = """..."""` 替换为以下美化版本：

```python
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI 智建 — 框架结构参数" Width="450" Height="580"
            WindowStartupLocation="CenterScreen"
            ResizeMode="NoResize"
            Background="#F0F0F0">

        <Window.Resources>
            <Style x:Key="SectionCard" TargetType="Border">
                <Setter Property="Background" Value="White"/>
                <Setter Property="CornerRadius" Value="8"/>
                <Setter Property="Padding" Value="16"/>
                <Setter Property="Margin" Value="0,0,0,12"/>
                <Setter Property="Effect">
                    <Setter.Value>
                        <DropShadowEffect ShadowDepth="1" Opacity="0.15" BlurRadius="6"/>
                    </Setter.Value>
                </Setter>
            </Style>
            <Style x:Key="FieldLabel" TargetType="TextBlock">
                <Setter Property="VerticalAlignment" Value="Center"/>
                <Setter Property="Foreground" Value="#333333"/>
                <Setter Property="FontSize" Value="13"/>
            </Style>
            <Style x:Key="FieldInput" TargetType="TextBox">
                <Setter Property="Height" Value="30"/>
                <Setter Property="Padding" Value="6,4"/>
                <Setter Property="FontSize" Value="13"/>
                <Setter Property="BorderBrush" Value="#CCCCCC"/>
                <Setter Property="BorderThickness" Value="1"/>
                <Style.Triggers>
                    <Trigger Property="IsFocused" Value="True">
                        <Setter Property="BorderBrush" Value="#FF6D00"/>
                        <Setter Property="BorderThickness" Value="2"/>
                    </Trigger>
                </Style.Triggers>
            </Style>
        </Window.Resources>

        <DockPanel>
            <!-- Title bar -->
            <Border DockPanel.Dock="Top" Background="#1E3A5F" Padding="20,14">
                <StackPanel>
                    <TextBlock Text="AI 智建" FontSize="20" FontWeight="Bold"
                               Foreground="White"/>
                    <TextBlock Text="框架结构参数配置" FontSize="12"
                               Foreground="#B0C4DE" Margin="0,2,0,0"/>
                </StackPanel>
            </Border>

            <!-- Main content -->
            <ScrollViewer DockPanel.Dock="Top" VerticalScrollBarVisibility="Auto"
                          Padding="20,16,20,0">
                <StackPanel>

                    <!-- Section 1: Structure parameters -->
                    <TextBlock Text="结构参数" FontSize="14" FontWeight="SemiBold"
                               Foreground="#1E3A5F" Margin="4,0,0,8"/>
                    <Border Style="{StaticResource SectionCard}">
                        <StackPanel>
                            <Grid Margin="0,0,0,8">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="120"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="X 向跨距 (mm)" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_x_spans" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"
                                         Text="6000, 6000, 6000"
                                         ToolTip="逗号分隔，如 6000, 7200, 6000"/>
                            </Grid>

                            <Grid Margin="0,0,0,8">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="120"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="Y 向跨距 (mm)" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_y_spans" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"
                                         Text="6000, 6000"
                                         ToolTip="逗号分隔，如 6000, 6000"/>
                            </Grid>

                            <Grid Margin="0,0,0,8">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="120"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="层数" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_floors" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"
                                         Text="5"/>
                            </Grid>

                            <Grid Margin="0,0,0,8">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="120"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="标准层高 (mm)" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_floor_height" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"
                                         Text="3600"/>
                            </Grid>

                            <Grid Margin="0,0,0,0">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="120"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="首层层高 (mm)" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_first_height" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"
                                         Text="4200"
                                         ToolTip="留空则与标准层高相同"/>
                            </Grid>
                        </StackPanel>
                    </Border>

                    <!-- Section 2: Cross-section parameters -->
                    <TextBlock Text="截面参数" FontSize="14" FontWeight="SemiBold"
                               Foreground="#1E3A5F" Margin="4,4,0,8"/>
                    <Border Style="{StaticResource SectionCard}">
                        <StackPanel>
                            <Grid Margin="0,0,0,8">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="120"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="柱截面 (mm)" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_col_section" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"
                                         Text="500x500"/>
                            </Grid>

                            <Grid Margin="0,0,0,8">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="120"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="X 向梁截面" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_beam_x" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"
                                         Text="300x600"/>
                            </Grid>

                            <Grid Margin="0,0,0,0">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="120"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="Y 向梁截面" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_beam_y" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"
                                         Text="300x600"/>
                            </Grid>
                        </StackPanel>
                    </Border>

                </StackPanel>
            </ScrollViewer>

            <!-- Bottom button -->
            <Border DockPanel.Dock="Bottom" Padding="20,12" Background="#F0F0F0">
                <Button Content="生 成 框 架" FontSize="15" FontWeight="Bold"
                        Height="42" Foreground="White" Background="#1E3A5F"
                        BorderThickness="0" Cursor="Hand"
                        Click="on_generate">
                    <Button.Style>
                        <Style TargetType="Button">
                            <Setter Property="Template">
                                <Setter.Value>
                                    <ControlTemplate TargetType="Button">
                                        <Border x:Name="border" Background="#1E3A5F"
                                                CornerRadius="6" Padding="0">
                                            <ContentPresenter HorizontalAlignment="Center"
                                                              VerticalAlignment="Center"/>
                                        </Border>
                                        <ControlTemplate.Triggers>
                                            <Trigger Property="IsMouseOver" Value="True">
                                                <Setter TargetName="border"
                                                        Property="Background" Value="#FF6D00"/>
                                            </Trigger>
                                            <Trigger Property="IsPressed" Value="True">
                                                <Setter TargetName="border"
                                                        Property="Background" Value="#E65100"/>
                                            </Trigger>
                                        </ControlTemplate.Triggers>
                                    </ControlTemplate>
                                </Setter.Value>
                            </Setter>
                        </Style>
                    </Button.Style>
                </Button>
            </Border>
        </DockPanel>
    </Window>
    """
```

- [ ] **Step 2: 验证 Python 语法**

```bash
python3 -c "
import ast
with open('AISmartBuild.extension/AISmartBuild.tab/FrameModel.panel/GenerateFrame.pushbutton/script.py') as f:
    ast.parse(f.read())
print('Syntax OK')
"
```

Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add AISmartBuild.extension/AISmartBuild.tab/FrameModel.panel/GenerateFrame.pushbutton/script.py
git commit -m "feat(ui): beautify GenerateFrame form with card layout and themed colors"
```

---

### Task 4: SmartChat 聊天窗口 — 替换 ask_for_string 为 WPF 窗口

**Files:**

- Modify: `AISmartBuild.extension/AISmartBuild.tab/AIChat.panel/SmartChat.pushbutton/script.py`

将当前的 `while True: forms.ask_for_string()` 循环替换为一个独立的 WPF 聊天窗口，包含：上方多行输出区域（深色背景）、下方输入框 + 发送按钮。

- [ ] **Step 1: 创建 ChatWindow 类**

在 `script.py` 中，在 `import` 块之后、`main()` 函数之前，添加 `ChatWindow` 类：

```python
import clr
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
from System.Windows import Window, SizeToContent, WindowStartupLocation as WSL
from System.Windows.Threading import DispatcherPriority
from System.Windows.Input import Key


class ChatWindow(forms.WPFWindow):
    """AI chat window with output area and input box."""

    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI 智建 — 智能对话" Width="550" Height="650"
            WindowStartupLocation="CenterScreen"
            MinWidth="400" MinHeight="400"
            Background="#F0F0F0">

        <Window.Resources>
            <Style x:Key="SendButton" TargetType="Button">
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="Button">
                            <Border x:Name="border" Background="#1E3A5F"
                                    CornerRadius="4" Padding="16,6">
                                <ContentPresenter HorizontalAlignment="Center"
                                                  VerticalAlignment="Center"/>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsMouseOver" Value="True">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#FF6D00"/>
                                </Trigger>
                                <Trigger Property="IsPressed" Value="True">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#E65100"/>
                                </Trigger>
                                <Trigger Property="IsEnabled" Value="False">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#999999"/>
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>
        </Window.Resources>

        <DockPanel>
            <!-- Title bar -->
            <Border DockPanel.Dock="Top" Background="#1E3A5F" Padding="16,10">
                <StackPanel Orientation="Horizontal">
                    <TextBlock Text="AI 智建" FontSize="16" FontWeight="Bold"
                               Foreground="White"/>
                    <TextBlock Text=" — 智能对话建模" FontSize="13"
                               Foreground="#B0C4DE" VerticalAlignment="Bottom"
                               Margin="4,0,0,1"/>
                </StackPanel>
            </Border>

            <!-- Hint bar -->
            <Border DockPanel.Dock="Top" Background="#E8EDF2" Padding="16,6">
                <TextBlock Text="输入中文指令，如"在(6000,0)处创建500x500柱子" | /help 查看帮助 | /reset 重置会话"
                           FontSize="11" Foreground="#666666" TextWrapping="Wrap"/>
            </Border>

            <!-- Input area (bottom) -->
            <Border DockPanel.Dock="Bottom" Background="White" Padding="12,10"
                    BorderBrush="#DDDDDD" BorderThickness="0,1,0,0">
                <Grid>
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/>
                        <ColumnDefinition Width="Auto"/>
                    </Grid.ColumnDefinitions>
                    <TextBox x:Name="tb_input" Grid.Column="0"
                             FontSize="14" Padding="8,6"
                             BorderBrush="#CCCCCC" BorderThickness="1"
                             AcceptsReturn="False"
                             KeyDown="on_key_down"
                             VerticalContentAlignment="Center"/>
                    <Button x:Name="btn_send" Grid.Column="1"
                            Content="发送" FontSize="13" Foreground="White"
                            Margin="8,0,0,0" Height="34"
                            Style="{StaticResource SendButton}"
                            Click="on_send"/>
                </Grid>
            </Border>

            <!-- Chat output area (center, fills remaining space) -->
            <TextBox x:Name="tb_output"
                     Background="#1E1E2E" Foreground="#D4D4D4"
                     FontFamily="Consolas, Microsoft YaHei"
                     FontSize="13" Padding="12,8"
                     IsReadOnly="True" TextWrapping="Wrap"
                     VerticalScrollBarVisibility="Auto"
                     BorderThickness="0"/>
        </DockPanel>
    </Window>
    """

    def __init__(self):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)
        self._pending_input = None
        self._closed = False
        self.Closed += self._on_closed

    def _on_closed(self, sender, args):
        self._closed = True
        self._pending_input = None

    def append_output(self, text, prefix=None):
        """Append text to output area."""
        if prefix:
            self.tb_output.Text += u"{} {}\n".format(prefix, text)
        else:
            self.tb_output.Text += text + u"\n"
        self.tb_output.ScrollToEnd()

    def append_user(self, text):
        self.append_output(text, prefix=u"[你]")

    def append_ai(self, text):
        self.append_output(text, prefix=u"[AI]")

    def append_system(self, text):
        self.append_output(text, prefix=u"[系统]")

    def wait_for_input(self):
        """Block until user submits input. Returns None if window closed."""
        self._pending_input = None
        self.tb_input.Text = ""
        self.tb_input.Focus()

        # Pump WPF message loop until we get input
        import System.Windows.Threading as swt
        frame = swt.DispatcherFrame()
        self._frame = frame

        def check_input(sender, args):
            if self._pending_input is not None or self._closed:
                frame.Continue = False

        self.tb_input.TextChanged += check_input
        swt.Dispatcher.PushFrame(frame)
        self.tb_input.TextChanged -= check_input

        return self._pending_input

    def on_send(self, sender, args):
        text = self.tb_input.Text.strip()
        if text:
            self._pending_input = text

    def on_key_down(self, sender, args):
        if args.Key == Key.Return:
            self.on_send(sender, args)
            args.Handled = True
```

- [ ] **Step 2: 重写 main() 函数使用 ChatWindow**

替换 `script.py` 中的 `main()` 函数：

```python
def main():
    doc = revit.doc
    output = script.get_output()
    operation_log = OperationLog()
    conversation_log = ConversationLog()

    if not DEEPSEEK_API_KEY:
        forms.alert(
            "请先配置 DeepSeek API Key\n\n"
            "可用方式：\n"
            "1. 环境变量 DEEPSEEK_API_KEY 或 AI_SMART_BUILD_DEEPSEEK_API_KEY\n"
            "2. 用户配置文件：{}\n\n"
            "申请地址: https://platform.deepseek.com".format(USER_CONFIG_PATH),
            title="AI 智建 — 配置缺失"
        )
        script.exit()

    client = DeepSeekClient()
    levels = get_all_levels(doc)
    chat_state = build_chat_state()

    chat = ChatWindow()
    chat.Show()
    chat.append_system(u"欢迎使用 AI 智建智能对话建模！")
    chat.append_system(u"输入中文指令开始建模，输入 q 退出。")

    output.print_md("## AI 智建 — 智能对话建模")

    while True:
        user_input = chat.wait_for_input()

        if not user_input or user_input.strip().lower() == "q":
            break

        chat.append_user(user_input)

        handled, levels = handle_local_command(
            user_input,
            output,
            client,
            doc=doc,
            levels=levels,
            operation_log=operation_log,
            conversation_log=conversation_log,
            chat_state=chat_state,
        )
        if handled:
            chat.append_system(u"指令已执行。")
            continue

        levels = run_ai_turn(
            doc,
            output,
            client,
            levels,
            user_input,
            operation_log,
            conversation_log,
            chat_state,
        )
        # Display AI response in chat window
        if chat_state.get("last_reply"):
            chat.append_ai(chat_state["last_reply"])
        else:
            chat.append_ai(u"指令已执行，请查看 Revit 模型。")

    chat.Close()
    output.print_md("对话结束。")
    conversation_path = export_conversation_log(conversation_log, u"AI对话会话")
    if operation_log.logs:
        log_path = export_operation_log(operation_log, u"AI对话")
        output.print_md("### " + operation_log.get_summary())
        if log_path:
            output.print_md("- 日志已导出：`{}`".format(log_path))
    if conversation_path:
        output.print_md("- 会话记录已导出：`{}`".format(conversation_path))
```

- [ ] **Step 3: 验证 Python 语法**

```bash
python3 -c "
import ast
with open('AISmartBuild.extension/AISmartBuild.tab/AIChat.panel/SmartChat.pushbutton/script.py') as f:
    ast.parse(f.read())
print('Syntax OK')
"
```

Expected: `Syntax OK`

- [ ] **Step 4: Commit**

```bash
git add AISmartBuild.extension/AISmartBuild.tab/AIChat.panel/SmartChat.pushbutton/script.py
git commit -m "feat(ui): add WPF chat window for SmartChat"
```

---

### Task 5: 运行现有测试 — 确保无回归

**Files:**

- Read: `tests/` (existing test suite)

- [ ] **Step 1: 运行全部测试**

```bash
cd /Users/xiaojunming/Desktop/AI智建
python3 -m pytest tests/ -v --tb=short
```

Expected: 所有现有测试通过（271 tests）。UI 修改不应影响引擎逻辑。

- [ ] **Step 2: 如有失败，修复后重跑**

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(ui): complete UI optimization — icons, forms, chat window, panel order"
```
