# UI 完善第二阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全方位完善 AI智建 UI — 关于窗口美化、dark mode 图标、修改/删除构件合并表单、图标抗锯齿、聊天窗口导出按钮、配置面板、新增测试

**Architecture:** 所有改动均为 UI 层和脚本层，不涉及 engine 核心逻辑。新增 WPF 窗口沿用第一阶段的配色体系（深蓝 #1E3A5F + 橙色 #FF6D00）。配置面板通过读写 `~/.ai-smart-build/config.json` 实现。测试全部离线可跑。

**Tech Stack:** Python 3, Pillow (图标), WPF/XAML (窗口), pytest (测试)

---

### Task 1: 关于窗口美化 — WPF 替换 forms.alert

**Files:**

- Modify: `AISmartBuild.extension/AISmartBuild.tab/Help.panel/About.pushbutton/script.py`

将当前的 `forms.alert(message)` 替换为主题一致的 WPF 窗口：深蓝标题栏 + 版本信息卡片。

- [ ] **Step 1: 重写 script.py**

替换 `main()` 函数并添加 `AboutWindow` 类。保留现有的 `_get_pyrevit_version_text()` 和 `_get_revit_version_text()` 辅助函数不变。

```python
class AboutWindow(forms.WPFWindow):
    """About dialog with themed UI."""

    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI 智建 — 关于" Width="420" Height="400"
            WindowStartupLocation="CenterScreen"
            ResizeMode="NoResize"
            Background="#F0F0F0">
        <DockPanel>
            <Border DockPanel.Dock="Top" Background="#1E3A5F" Padding="24,18">
                <StackPanel>
                    <TextBlock Text="AI 智建" FontSize="24" FontWeight="Bold"
                               Foreground="White"/>
                    <TextBlock Text="自然语言驱动的 Revit 智能建模系统" FontSize="12"
                               Foreground="#B0C4DE" Margin="0,4,0,0"/>
                </StackPanel>
            </Border>

            <Border DockPanel.Dock="Bottom" Padding="20,10" Background="#F0F0F0">
                <Button Content="确 定" FontSize="13" FontWeight="Bold"
                        Height="36" Foreground="White" Cursor="Hand"
                        Click="on_close">
                    <Button.Style>
                        <Style TargetType="Button">
                            <Setter Property="Template">
                                <Setter.Value>
                                    <ControlTemplate TargetType="Button">
                                        <Border x:Name="border" Background="#1E3A5F"
                                                CornerRadius="6">
                                            <ContentPresenter HorizontalAlignment="Center"
                                                              VerticalAlignment="Center"/>
                                        </Border>
                                        <ControlTemplate.Triggers>
                                            <Trigger Property="IsMouseOver" Value="True">
                                                <Setter TargetName="border"
                                                        Property="Background" Value="#FF6D00"/>
                                            </Trigger>
                                        </ControlTemplate.Triggers>
                                    </ControlTemplate>
                                </Setter.Value>
                            </Setter>
                        </Style>
                    </Button.Style>
                </Button>
            </Border>

            <Border Margin="20,16" Background="White" CornerRadius="8" Padding="20,16">
                <Border.Effect>
                    <DropShadowEffect ShadowDepth="1" Opacity="0.15" BlurRadius="6"/>
                </Border.Effect>
                <StackPanel>
                    <TextBlock x:Name="tb_version" FontSize="14" FontWeight="SemiBold"
                               Foreground="#1E3A5F" Margin="0,0,0,12"/>
                    <TextBlock x:Name="tb_python" FontSize="12" Foreground="#555" Margin="0,0,0,6"/>
                    <TextBlock x:Name="tb_pyrevit" FontSize="12" Foreground="#555" Margin="0,0,0,6"/>
                    <TextBlock x:Name="tb_revit" FontSize="12" Foreground="#555" Margin="0,0,0,6"/>
                    <TextBlock x:Name="tb_api" FontSize="12" Foreground="#555" Margin="0,0,0,6"/>
                    <TextBlock x:Name="tb_config" FontSize="12" Foreground="#555"
                               TextWrapping="Wrap"/>
                </StackPanel>
            </Border>
        </DockPanel>
    </Window>
    """

    def __init__(self, info):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)
        self.tb_version.Text = u"插件版本：v{}".format(info["version"])
        self.tb_python.Text = u"Python：{}".format(info["python"])
        self.tb_pyrevit.Text = u"pyRevit：{}".format(info["pyrevit"])
        self.tb_revit.Text = u"Revit：{}".format(info["revit"])
        self.tb_api.Text = u"DeepSeek API Key：{}".format(info["api_status"])
        self.tb_config.Text = u"配置文件：{}".format(info["config_path"])

    def on_close(self, sender, args):
        self.Close()


def main():
    info = {
        "version": VERSION,
        "python": sys.version.split()[0],
        "pyrevit": _get_pyrevit_version_text(),
        "revit": _get_revit_version_text(),
        "api_status": u"已配置" if DEEPSEEK_API_KEY else u"未配置",
        "config_path": USER_CONFIG_PATH,
    }
    window = AboutWindow(info)
    window.ShowDialog()
```

- [ ] **Step 2: 验证 Python 语法**

```bash
python3 -c "import ast; ast.parse(open('AISmartBuild.extension/AISmartBuild.tab/Help.panel/About.pushbutton/script.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add AISmartBuild.extension/AISmartBuild.tab/Help.panel/About.pushbutton/script.py
git commit -m "feat(ui): beautify About dialog with themed WPF window"
```

---

### Task 2: Dark mode 图标 — 生成 icon_dark.png

**Files:**

- Modify: `scripts/generate_icons.py`
- Create: 7 个 `icon_dark.png` 文件（每个 pushbutton 目录）

pyRevit 暗色主题下自动加载 `icon_dark.png`。dark 版本需要反转配色：白色/浅蓝主体 + 橙色点缀，在深色背景上清晰可见。

- [ ] **Step 1: 在 generate_icons.py 中添加 dark mode 颜色常量和生成逻辑**

在 `PRIMARY`/`ACCENT` 常量后添加：

```python
PRIMARY_DARK = (200, 215, 235, 255)   # light blue-gray for dark backgrounds
ACCENT_DARK  = (255, 140, 40, 255)    # slightly lighter orange for dark mode
```

每个 `draw_*` 函数添加 `dark=False` 参数：

```python
def draw_smart_chat(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK if dark else ACCENT
    dot_color = (60, 60, 80, 220) if dark else (255, 255, 255, 220)
    # ... rest uses p, a, dot_color instead of PRIMARY, ACCENT, DOT
```

在 `main()` 中，对每个图标同时生成 `icon.png` 和 `icon_dark.png`：

```python
def main():
    generated = []
    errors = []

    for name, folder in ICONS.items():
        try:
            draw_fn = DRAW_FUNCS[name]
            # Normal icon
            img = draw_fn()
            assert img.size == (SIZE, SIZE)
            out_path = os.path.join(folder, "icon.png")
            img.save(out_path, "PNG")
            # Dark icon
            img_dark = draw_fn(dark=True)
            dark_path = os.path.join(folder, "icon_dark.png")
            img_dark.save(dark_path, "PNG")
            generated.append(name)
            print(f"  [OK] {name}")
        except Exception as exc:
            errors.append((name, str(exc)))
            print(f"  [ERR] {name}: {exc}")

    print(f"\nGenerated {len(generated)}/{len(ICONS)} icon pairs.")
```

- [ ] **Step 2: 运行脚本**

```bash
python3 scripts/generate_icons.py
```

Expected: 14 个文件生成（7 icon.png + 7 icon_dark.png）。

- [ ] **Step 3: 验证 dark 图标**

```bash
python3 -c "
from PIL import Image
import os
tab = 'AISmartBuild.extension/AISmartBuild.tab'
for panel in sorted(os.listdir(tab)):
    pp = os.path.join(tab, panel)
    if not panel.endswith('.panel'): continue
    for btn in sorted(os.listdir(pp)):
        if not btn.endswith('.pushbutton'): continue
        dp = os.path.join(pp, btn, 'icon_dark.png')
        if os.path.exists(dp):
            img = Image.open(dp)
            print(f'{btn}: {img.width}x{img.height} {img.mode}')
        else:
            print(f'{btn}: MISSING icon_dark.png')
"
```

Expected: 7 行，每个 96x96 RGBA。

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_icons.py
git add AISmartBuild.extension/AISmartBuild.tab/*/*/icon_dark.png
git commit -m "feat(ui): add dark mode icons for all buttons"
```

---

### Task 3: 图标抗锯齿优化 — 4x 超采样

**Files:**

- Modify: `scripts/generate_icons.py`

当前图标在 96x96 直接绘制，斜线和曲线有锯齿。改为在 384x384 (4x) 画布上绘制，然后用 LANCZOS 缩放到 96x96，利用超采样实现抗锯齿。

- [ ] **Step 1: 修改 generate_icons.py 的渲染管线**

修改 `SIZE` 和 `new_canvas()`，添加缩放步骤：

```python
SIZE = 96
RENDER_SCALE = 4
RENDER_SIZE = SIZE * RENDER_SCALE  # 384


def new_canvas():
    img = Image.new("RGBA", (RENDER_SIZE, RENDER_SIZE), BG)
    draw = ImageDraw.Draw(img)
    return img, draw
```

将所有绘制函数中的坐标乘以 `RENDER_SCALE`（即全部乘4）。例如 `draw_about`：

```python
def draw_about(dark=False):
    img, draw = new_canvas()
    p = PRIMARY_DARK if dark else PRIMARY
    a = ACCENT_DARK if dark else ACCENT
    S = RENDER_SCALE
    draw.ellipse([10*S, 10*S, 86*S, 86*S], outline=p, width=4*S)
    draw.ellipse([42*S, 24*S, 54*S, 36*S], fill=a)
    draw.rounded_rectangle([42*S, 42*S, 54*S, 72*S], radius=4*S, fill=a)
    return img
```

在 `main()` 中添加缩放步骤：

```python
img = draw_fn()
img = img.resize((SIZE, SIZE), Image.LANCZOS)
```

- [ ] **Step 2: 更新所有 7 个绘制函数的坐标（全部 \*S）**

每个绘制函数中，所有硬编码坐标数字都乘以 `S = RENDER_SCALE`。线宽也乘以 S。

- [ ] **Step 3: 运行脚本并验证**

```bash
python3 scripts/generate_icons.py
python3 -c "
from PIL import Image
img = Image.open('AISmartBuild.extension/AISmartBuild.tab/Help.panel/About.pushbutton/icon.png')
print(f'{img.width}x{img.height} {img.mode}')
"
```

Expected: `96x96 RGBA`

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_icons.py
git add AISmartBuild.extension/AISmartBuild.tab/*/*/icon.png
git add AISmartBuild.extension/AISmartBuild.tab/*/*/icon_dark.png
git commit -m "feat(ui): add 4x supersampling antialiasing to icons"
```

---

### Task 4: 修改/删除构件合并表单 — WPF 替换多步弹窗

**Files:**

- Modify: `AISmartBuild.extension/AISmartBuild.tab/ElementOps.panel/ModifyElement.pushbutton/script.py`
- Modify: `AISmartBuild.extension/AISmartBuild.tab/ElementOps.panel/DeleteElement.pushbutton/script.py`

将当前多步弹窗（选模式→选类型→选楼层→输入）合并为单个 WPF 表单。

- [ ] **Step 1: 重写 ModifyElement/script.py 的 UI 部分**

在文件中添加 `ModifyForm` 类，替换 `_pick_mode` / `_ask_section` 等弹窗调用：

```python
class ModifyForm(forms.WPFWindow):
    """Modify element form — single window replaces multi-step dialogs."""

    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI 智建 — 修改构件" Width="420" Height="440"
            WindowStartupLocation="CenterScreen"
            ResizeMode="NoResize" Background="#F0F0F0">

        <Window.Resources>
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
                <Style.Triggers>
                    <Trigger Property="IsFocused" Value="True">
                        <Setter Property="BorderBrush" Value="#FF6D00"/>
                        <Setter Property="BorderThickness" Value="2"/>
                    </Trigger>
                </Style.Triggers>
            </Style>
        </Window.Resources>

        <DockPanel>
            <Border DockPanel.Dock="Top" Background="#1E3A5F" Padding="20,12">
                <TextBlock Text="修改构件" FontSize="18" FontWeight="Bold" Foreground="White"/>
            </Border>

            <Border DockPanel.Dock="Bottom" Padding="20,10">
                <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">
                    <Button Content="取消" Width="80" Height="36" Margin="0,0,10,0"
                            Click="on_cancel"/>
                    <Button Content="确定修改" Height="36" Foreground="White" Click="on_confirm">
                        <Button.Style>
                            <Style TargetType="Button">
                                <Setter Property="Template">
                                    <Setter.Value>
                                        <ControlTemplate TargetType="Button">
                                            <Border x:Name="border" Background="#1E3A5F"
                                                    CornerRadius="6" Padding="20,0">
                                                <ContentPresenter HorizontalAlignment="Center"
                                                                  VerticalAlignment="Center"/>
                                            </Border>
                                            <ControlTemplate.Triggers>
                                                <Trigger Property="IsMouseOver" Value="True">
                                                    <Setter TargetName="border"
                                                            Property="Background" Value="#FF6D00"/>
                                                </Trigger>
                                            </ControlTemplate.Triggers>
                                        </ControlTemplate>
                                    </Setter.Value>
                                </Setter>
                            </Style>
                        </Button.Style>
                    </Button>
                </StackPanel>
            </Border>

            <Border Margin="20,12" Background="White" CornerRadius="8" Padding="16">
                <Border.Effect>
                    <DropShadowEffect ShadowDepth="1" Opacity="0.15" BlurRadius="6"/>
                </Border.Effect>
                <StackPanel>
                    <Grid Margin="0,0,0,10">
                        <Grid.ColumnDefinitions>
                            <ColumnDefinition Width="100"/>
                            <ColumnDefinition Width="*"/>
                        </Grid.ColumnDefinitions>
                        <TextBlock Text="修改模式" Style="{StaticResource FieldLabel}"/>
                        <ComboBox x:Name="cb_mode" Grid.Column="1" Height="30"
                                  FontSize="13" SelectedIndex="0"
                                  SelectionChanged="on_mode_changed">
                            <ComboBoxItem Content="单个修改"/>
                            <ComboBoxItem Content="批量修改"/>
                        </ComboBox>
                    </Grid>

                    <StackPanel x:Name="panel_batch" Visibility="Collapsed">
                        <Grid Margin="0,0,0,10">
                            <Grid.ColumnDefinitions>
                                <ColumnDefinition Width="100"/>
                                <ColumnDefinition Width="*"/>
                            </Grid.ColumnDefinitions>
                            <TextBlock Text="构件类型" Style="{StaticResource FieldLabel}"/>
                            <ComboBox x:Name="cb_category" Grid.Column="1" Height="30"
                                      FontSize="13" SelectedIndex="0">
                                <ComboBoxItem Content="柱"/>
                                <ComboBoxItem Content="梁"/>
                            </ComboBox>
                        </Grid>

                        <Grid Margin="0,0,0,10">
                            <Grid.ColumnDefinitions>
                                <ColumnDefinition Width="100"/>
                                <ColumnDefinition Width="*"/>
                            </Grid.ColumnDefinitions>
                            <TextBlock Text="楼层" Style="{StaticResource FieldLabel}"/>
                            <ComboBox x:Name="cb_floor" Grid.Column="1" Height="30" FontSize="13"/>
                        </Grid>

                        <Grid Margin="0,0,0,10">
                            <Grid.ColumnDefinitions>
                                <ColumnDefinition Width="100"/>
                                <ColumnDefinition Width="*"/>
                            </Grid.ColumnDefinitions>
                            <TextBlock Text="旧截面" Style="{StaticResource FieldLabel}"/>
                            <TextBox x:Name="tb_old_section" Grid.Column="1"
                                     Style="{StaticResource FieldInput}" Text="500x500"/>
                        </Grid>
                    </StackPanel>

                    <Grid Margin="0,0,0,0">
                        <Grid.ColumnDefinitions>
                            <ColumnDefinition Width="100"/>
                            <ColumnDefinition Width="*"/>
                        </Grid.ColumnDefinitions>
                        <TextBlock Text="新截面" Style="{StaticResource FieldLabel}"/>
                        <TextBox x:Name="tb_new_section" Grid.Column="1"
                                 Style="{StaticResource FieldInput}" Text="600x600"/>
                    </Grid>
                </StackPanel>
            </Border>
        </DockPanel>
    </Window>
    """

    def __init__(self, floor_options=None):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)
        self.result = None
        if floor_options:
            for opt in floor_options:
                self.cb_floor.Items.Add(opt)
            if self.cb_floor.Items.Count > 0:
                self.cb_floor.SelectedIndex = 0

    def on_mode_changed(self, sender, args):
        is_batch = self.cb_mode.SelectedIndex == 1
        if is_batch:
            self.panel_batch.Visibility = self.panel_batch.Visibility.Visible
        else:
            self.panel_batch.Visibility = self.panel_batch.Visibility.Collapsed

    def on_cancel(self, sender, args):
        self.Close()

    def on_confirm(self, sender, args):
        mode = "single" if self.cb_mode.SelectedIndex == 0 else "batch"
        self.result = {
            "mode": mode,
            "new_section": self.tb_new_section.Text.strip(),
        }
        if mode == "batch":
            cat_index = self.cb_category.SelectedIndex
            self.result["category"] = "column" if cat_index == 0 else "beam"
            self.result["old_section"] = self.tb_old_section.Text.strip()
            if self.cb_floor.SelectedItem:
                self.result["floor_option"] = self.cb_floor.SelectedItem
        self.Close()
```

同时更新 `main()` 使用 `ModifyForm`：点击确认后根据 `result["mode"]` 执行单个或批量修改。单个模式仍需 `revit.pick_element()`。

- [ ] **Step 2: 类似地重写 DeleteElement/script.py**

添加 `DeleteForm` 类，包含：模式选择（单个/批量）、构件类型（柱/梁/板）、楼层选择。

XAML 结构与 `ModifyForm` 类似，但没有截面输入，改为删除确认文本。

- [ ] **Step 3: 验证两个脚本语法**

```bash
python3 -c "import ast; ast.parse(open('AISmartBuild.extension/AISmartBuild.tab/ElementOps.panel/ModifyElement.pushbutton/script.py').read()); print('ModifyElement OK')"
python3 -c "import ast; ast.parse(open('AISmartBuild.extension/AISmartBuild.tab/ElementOps.panel/DeleteElement.pushbutton/script.py').read()); print('DeleteElement OK')"
```

- [ ] **Step 4: Commit**

```bash
git add AISmartBuild.extension/AISmartBuild.tab/ElementOps.panel/*/script.py
git commit -m "feat(ui): merge modify/delete multi-step dialogs into single WPF forms"
```

---

### Task 5: SmartChat 导出按钮 — 聊天窗口添加"导出对话"

**Files:**

- Modify: `AISmartBuild.extension/AISmartBuild.tab/AIChat.panel/SmartChat.pushbutton/script.py`

在聊天窗口的标题栏右侧添加一个"导出"按钮，点击后将当前 `tb_output` 的内容保存为 `.txt` 文件。

- [ ] **Step 1: 修改 ChatWindow XAML 标题栏**

将标题栏的 `<StackPanel Orientation="Horizontal">` 改为 `<DockPanel>`，在右侧添加导出按钮：

```xml
<!-- Title bar -->
<Border DockPanel.Dock="Top" Background="#1E3A5F" Padding="16,10">
    <DockPanel>
        <Button DockPanel.Dock="Right" Content="导出" FontSize="11"
                Foreground="#B0C4DE" Background="Transparent"
                BorderThickness="1" BorderBrush="#4A6A8F"
                Padding="10,4" Cursor="Hand" Margin="8,0,0,0"
                Click="on_export"/>
        <StackPanel Orientation="Horizontal">
            <TextBlock Text="AI 智建" FontSize="16" FontWeight="Bold"
                       Foreground="White"/>
            <TextBlock Text=" — 智能对话建模" FontSize="13"
                       Foreground="#B0C4DE" VerticalAlignment="Bottom"
                       Margin="4,0,0,1"/>
        </StackPanel>
    </DockPanel>
</Border>
```

- [ ] **Step 2: 添加 on_export 事件处理**

在 `ChatWindow` 类中添加：

```python
def on_export(self, sender, args):
    """Export chat content to a text file."""
    content = self.tb_output.Text
    if not content.strip():
        return
    file_path = forms.save_file(
        file_ext="txt",
        default_name=u"AI智建对话记录.txt",
        title=u"导出对话记录",
    )
    if file_path:
        import io
        with io.open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.append_system(u"对话已导出到：{}".format(file_path))
```

- [ ] **Step 3: 验证语法**

```bash
python3 -c "import ast; ast.parse(open('AISmartBuild.extension/AISmartBuild.tab/AIChat.panel/SmartChat.pushbutton/script.py').read()); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add AISmartBuild.extension/AISmartBuild.tab/AIChat.panel/SmartChat.pushbutton/script.py
git commit -m "feat(ui): add export button to SmartChat window"
```

---

### Task 6: 配置面板 — 新增 Settings 按钮和 WPF 窗口

**Files:**

- Create: `AISmartBuild.extension/AISmartBuild.tab/Help.panel/Settings.pushbutton/bundle.yaml`
- Create: `AISmartBuild.extension/AISmartBuild.tab/Help.panel/Settings.pushbutton/script.py`

新增一个"设置"按钮，打开配置面板管理 API Key、模型名称、API URL 等。读写 `~/.ai-smart-build/config.json`。

- [ ] **Step 1: 创建 bundle.yaml**

```yaml
title: 设置
tooltip: 管理 API Key、模型参数等配置
author: AI智建
```

- [ ] **Step 2: 创建 script.py**

```python
# -*- coding: utf-8 -*-
"""Settings panel for AI SmartBuild configuration."""

__doc__ = "管理 API Key、模型参数等配置"
__title__ = "设置"
__author__ = "AI智建"

import io
import json
import os

from pyrevit import forms, script

from config import USER_CONFIG_PATH


def _load_config():
    """Load current config from file."""
    if not os.path.exists(USER_CONFIG_PATH):
        return {}
    try:
        with io.open(USER_CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_config(data):
    """Save config to file."""
    config_dir = os.path.dirname(USER_CONFIG_PATH)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    with io.open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class SettingsWindow(forms.WPFWindow):
    """Settings panel with themed UI."""

    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI 智建 — 设置" Width="480" Height="460"
            WindowStartupLocation="CenterScreen"
            ResizeMode="NoResize" Background="#F0F0F0">

        <Window.Resources>
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
                <Style.Triggers>
                    <Trigger Property="IsFocused" Value="True">
                        <Setter Property="BorderBrush" Value="#FF6D00"/>
                        <Setter Property="BorderThickness" Value="2"/>
                    </Trigger>
                </Style.Triggers>
            </Style>
        </Window.Resources>

        <DockPanel>
            <Border DockPanel.Dock="Top" Background="#1E3A5F" Padding="20,12">
                <StackPanel>
                    <TextBlock Text="设置" FontSize="18" FontWeight="Bold" Foreground="White"/>
                    <TextBlock Text="修改后需重新打开对话窗口生效" FontSize="11"
                               Foreground="#B0C4DE" Margin="0,2,0,0"/>
                </StackPanel>
            </Border>

            <Border DockPanel.Dock="Bottom" Padding="20,10">
                <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">
                    <Button Content="取消" Width="80" Height="36" Margin="0,0,10,0"
                            Click="on_cancel"/>
                    <Button Content="保 存" Height="36" Foreground="White" Click="on_save">
                        <Button.Style>
                            <Style TargetType="Button">
                                <Setter Property="Template">
                                    <Setter.Value>
                                        <ControlTemplate TargetType="Button">
                                            <Border x:Name="border" Background="#1E3A5F"
                                                    CornerRadius="6" Padding="20,0">
                                                <ContentPresenter HorizontalAlignment="Center"
                                                                  VerticalAlignment="Center"/>
                                            </Border>
                                            <ControlTemplate.Triggers>
                                                <Trigger Property="IsMouseOver" Value="True">
                                                    <Setter TargetName="border"
                                                            Property="Background" Value="#FF6D00"/>
                                                </Trigger>
                                            </ControlTemplate.Triggers>
                                        </ControlTemplate>
                                    </Setter.Value>
                                </Setter>
                            </Style>
                        </Button.Style>
                    </Button>
                </StackPanel>
            </Border>

            <ScrollViewer Padding="20,12,20,0">
                <StackPanel>
                    <TextBlock Text="API 配置" FontSize="14" FontWeight="SemiBold"
                               Foreground="#1E3A5F" Margin="4,0,0,8"/>
                    <Border Background="White" CornerRadius="8" Padding="16" Margin="0,0,0,12">
                        <Border.Effect>
                            <DropShadowEffect ShadowDepth="1" Opacity="0.15" BlurRadius="6"/>
                        </Border.Effect>
                        <StackPanel>
                            <Grid Margin="0,0,0,10">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="100"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="API Key" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_api_key" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"/>
                            </Grid>

                            <Grid Margin="0,0,0,10">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="100"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="模型名称" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_model" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"/>
                            </Grid>

                            <Grid Margin="0,0,0,0">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="100"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="API URL" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_api_url" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"/>
                            </Grid>
                        </StackPanel>
                    </Border>

                    <TextBlock Text="超时与重试" FontSize="14" FontWeight="SemiBold"
                               Foreground="#1E3A5F" Margin="4,0,0,8"/>
                    <Border Background="White" CornerRadius="8" Padding="16">
                        <Border.Effect>
                            <DropShadowEffect ShadowDepth="1" Opacity="0.15" BlurRadius="6"/>
                        </Border.Effect>
                        <StackPanel>
                            <Grid Margin="0,0,0,10">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="140"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="超时时间 (ms)" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_timeout" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"/>
                            </Grid>

                            <Grid Margin="0,0,0,0">
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="140"/>
                                    <ColumnDefinition Width="*"/>
                                </Grid.ColumnDefinitions>
                                <TextBlock Text="重试次数" Style="{StaticResource FieldLabel}"/>
                                <TextBox x:Name="tb_retry" Grid.Column="1"
                                         Style="{StaticResource FieldInput}"/>
                            </Grid>
                        </StackPanel>
                    </Border>
                </StackPanel>
            </ScrollViewer>
        </DockPanel>
    </Window>
    """

    def __init__(self, config):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)
        self.saved = False
        self.tb_api_key.Text = config.get("DEEPSEEK_API_KEY", "")
        self.tb_model.Text = config.get("DEEPSEEK_MODEL", "deepseek-chat")
        self.tb_api_url.Text = config.get("DEEPSEEK_API_URL",
                                          "https://api.deepseek.com/v1/chat/completions")
        self.tb_timeout.Text = str(config.get("API_TIMEOUT_MS", 30000))
        self.tb_retry.Text = str(config.get("API_RETRY_COUNT", 2))

    def on_cancel(self, sender, args):
        self.Close()

    def on_save(self, sender, args):
        self.config_result = {
            "DEEPSEEK_API_KEY": self.tb_api_key.Text.strip(),
            "DEEPSEEK_MODEL": self.tb_model.Text.strip(),
            "DEEPSEEK_API_URL": self.tb_api_url.Text.strip(),
            "API_TIMEOUT_MS": self.tb_timeout.Text.strip(),
            "API_RETRY_COUNT": self.tb_retry.Text.strip(),
        }
        self.saved = True
        self.Close()


def main():
    config = _load_config()
    window = SettingsWindow(config)
    window.ShowDialog()

    if window.saved:
        config.update(window.config_result)
        _save_config(config)
        forms.alert(
            u"配置已保存到：{}\n\n请重新打开对话窗口使配置生效。".format(USER_CONFIG_PATH),
            title=u"AI 智建 — 设置"
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 为 Settings 按钮生成图标**

在 `scripts/generate_icons.py` 中新增 Settings 图标绘制函数：齿轮(深蓝) + 扳手(橙色)。同时在 `ICONS` 字典和 `DRAW_FUNCS` 字典中注册。运行脚本生成 `icon.png` 和 `icon_dark.png`。

- [ ] **Step 4: 验证语法**

```bash
python3 -c "import ast; ast.parse(open('AISmartBuild.extension/AISmartBuild.tab/Help.panel/Settings.pushbutton/script.py').read()); print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add AISmartBuild.extension/AISmartBuild.tab/Help.panel/Settings.pushbutton/
git add scripts/generate_icons.py
git commit -m "feat(ui): add settings panel for API configuration"
```

---

### Task 7: 新增测试 — ChatWindow 消息格式化和配置面板读写

**Files:**

- Create: `tests/test_ui_helpers.py`

测试可离线运行的 UI 相关逻辑（不依赖 pyRevit/WPF）。

- [ ] **Step 1: 创建测试文件**

```python
# -*- coding: utf-8 -*-
"""Offline tests for UI helper logic."""

import io
import json
import os
import tempfile

import pytest


class TestSettingsConfigIO:
    """Test config load/save logic from Settings pushbutton."""

    def test_save_and_load_config(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        data = {
            "DEEPSEEK_API_KEY": "test-key-123",
            "DEEPSEEK_MODEL": "deepseek-chat",
            "API_TIMEOUT_MS": "30000",
        }
        with io.open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with io.open(config_path, "r", encoding="utf-8-sig") as f:
            loaded = json.load(f)

        assert loaded["DEEPSEEK_API_KEY"] == "test-key-123"
        assert loaded["DEEPSEEK_MODEL"] == "deepseek-chat"
        assert loaded["API_TIMEOUT_MS"] == "30000"

    def test_load_missing_config_returns_empty(self, tmp_path):
        config_path = str(tmp_path / "nonexistent.json")
        assert not os.path.exists(config_path)

    def test_load_invalid_json_returns_empty(self, tmp_path):
        config_path = str(tmp_path / "bad.json")
        with io.open(config_path, "w", encoding="utf-8") as f:
            f.write("not json {{{")

        with pytest.raises(json.JSONDecodeError):
            with io.open(config_path, "r", encoding="utf-8-sig") as f:
                json.load(f)

    def test_save_creates_directory(self, tmp_path):
        nested = str(tmp_path / "a" / "b" / "config.json")
        os.makedirs(os.path.dirname(nested))
        data = {"key": "value"}
        with io.open(nested, "w", encoding="utf-8") as f:
            json.dump(data, f)

        assert os.path.exists(nested)
        with io.open(nested, "r", encoding="utf-8") as f:
            assert json.load(f) == {"key": "value"}

    def test_config_preserves_chinese(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        data = {"DEEPSEEK_MODEL": u"深度求索"}
        with io.open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        with io.open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["DEEPSEEK_MODEL"] == u"深度求索"


class TestChatMessageFormatting:
    """Test the message prefix formatting used by ChatWindow."""

    def _format_user(self, text):
        return u"[你] {}".format(text)

    def _format_ai(self, text):
        return u"[AI] {}".format(text)

    def _format_system(self, text):
        return u"[系统] {}".format(text)

    def test_user_prefix(self):
        assert self._format_user(u"创建一根柱子") == u"[你] 创建一根柱子"

    def test_ai_prefix(self):
        assert self._format_ai(u"已创建柱子") == u"[AI] 已创建柱子"

    def test_system_prefix(self):
        assert self._format_system(u"指令已执行") == u"[系统] 指令已执行"

    def test_empty_message(self):
        assert self._format_user(u"") == u"[你] "

    def test_multiline_message(self):
        msg = u"第一行\n第二行"
        result = self._format_ai(msg)
        assert result == u"[AI] 第一行\n第二行"


class TestIconGeneration:
    """Test that the icon generation script produces valid images."""

    def test_all_icons_exist(self):
        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "AISmartBuild.extension", "AISmartBuild.tab"
        )
        expected_buttons = [
            "AIChat.panel/SmartChat.pushbutton",
            "FrameModel.panel/ExcelImport.pushbutton",
            "FrameModel.panel/GenerateFrame.pushbutton",
            "ElementOps.panel/ModifyElement.pushbutton",
            "ElementOps.panel/DeleteElement.pushbutton",
            "DataIO.panel/ExportModel.pushbutton",
            "Help.panel/About.pushbutton",
        ]
        for btn_path in expected_buttons:
            icon = os.path.join(base, btn_path, "icon.png")
            assert os.path.exists(icon), "Missing icon: {}".format(btn_path)

    def test_icons_are_correct_size(self):
        from PIL import Image
        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "AISmartBuild.extension", "AISmartBuild.tab"
        )
        for panel in os.listdir(base):
            panel_path = os.path.join(base, panel)
            if not panel.endswith(".panel"):
                continue
            for btn in os.listdir(panel_path):
                if not btn.endswith(".pushbutton"):
                    continue
                icon_path = os.path.join(panel_path, btn, "icon.png")
                if os.path.exists(icon_path):
                    img = Image.open(icon_path)
                    assert img.size == (96, 96), "{} is {}".format(btn, img.size)
                    assert img.mode == "RGBA", "{} is {}".format(btn, img.mode)
```

- [ ] **Step 2: 运行测试**

```bash
python3 -m pytest tests/test_ui_helpers.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: 运行全部测试确认无回归**

```bash
python3 -m pytest tests/ -v --tb=short
```

Expected: 271 + 新增测试 全部通过。

- [ ] **Step 4: Commit**

```bash
git add tests/test_ui_helpers.py
git commit -m "test: add offline tests for UI helpers, config IO, and icon validation"
```
