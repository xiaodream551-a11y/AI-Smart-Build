# -*- coding: utf-8 -*-
"""AI chat-based intelligent modeling — Claude-style UI."""

__doc__ = "用中文对话控制 Revit 建模 — 输入指令，AI 自动执行"
__title__ = "智能\n对话"
__author__ = "AI智建"

import datetime

from pyrevit import forms, revit, script

from config import DEEPSEEK_API_KEY, USER_CONFIG_PATH
from ai.chat_common import get_all_levels
from ai.chat_controller import build_chat_state, handle_local_command, run_ai_turn
from ai.client import DeepSeekClient
from engine.logger import (
    ConversationLog, OperationLog,
    export_conversation_log, export_operation_log,
)

try:
    from System.Windows.Input import Key
except Exception:
    Key = None

try:
    import System
    from System.Windows import (
        Thickness, HorizontalAlignment, TextWrapping,
    )
    from System.Windows import CornerRadius as CR
    from System.Windows.Controls import Border as WBorder, TextBlock as WTB
    from System.Windows.Controls import StackPanel as WSP
    from System.Windows.Media import SolidColorBrush, Color
    from System.Windows.Threading import DispatcherPriority
    _HAS_WPF = True
except Exception:
    _HAS_WPF = False


def _brush(r, g, b):
    """Create a SolidColorBrush from RGB values."""
    return SolidColorBrush(Color.FromRgb(r, g, b))


class ChatWindow(forms.WPFWindow):
    """AI chat window — Claude style with chat bubbles."""

    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI &#x667a;&#x5efa; &#x2014; &#x667a;&#x80fd;&#x5bf9;&#x8bdd;"
            Width="520" Height="700"
            WindowStartupLocation="CenterScreen"
            MinWidth="420" MinHeight="500"
            Background="#F7F5EE"
            FontFamily="Microsoft YaHei, Segoe UI, sans-serif">

        <Window.Resources>
            <!-- Input TextBox with rounded border + focus highlight -->
            <Style x:Key="InputBox" TargetType="TextBox">
                <Setter Property="FontSize" Value="14"/>
                <Setter Property="Foreground" Value="#2D2B28"/>
                <Setter Property="CaretBrush" Value="#D97757"/>
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="TextBox">
                            <Border x:Name="border" BorderBrush="#E0DCD4"
                                    BorderThickness="1.5" CornerRadius="14"
                                    Background="#F7F5EE" Padding="12,8">
                                <Grid>
                                    <ScrollViewer x:Name="PART_ContentHost"
                                                  VerticalAlignment="Center"/>
                                    <TextBlock x:Name="hint"
                                               Text="&#x8f93;&#x5165;&#x5efa;&#x6a21;&#x6307;&#x4ee4;..."
                                               Foreground="#9B9590"
                                               VerticalAlignment="Center"
                                               Margin="2,0,0,0"
                                               IsHitTestVisible="False"
                                               Visibility="Collapsed"/>
                                </Grid>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsFocused" Value="True">
                                    <Setter TargetName="border"
                                            Property="BorderBrush" Value="#D97757"/>
                                </Trigger>
                                <MultiTrigger>
                                    <MultiTrigger.Conditions>
                                        <Condition Property="Text" Value=""/>
                                        <Condition Property="IsFocused" Value="False"/>
                                    </MultiTrigger.Conditions>
                                    <Setter TargetName="hint"
                                            Property="Visibility" Value="Visible"/>
                                </MultiTrigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>

            <!-- Send button: Claude terracotta -->
            <Style x:Key="SendButton" TargetType="Button">
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="Button">
                            <Border x:Name="border" Background="#D97757"
                                    CornerRadius="14" Padding="18,8">
                                <ContentPresenter HorizontalAlignment="Center"
                                                  VerticalAlignment="Center"/>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsMouseOver" Value="True">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#C4673E"/>
                                </Trigger>
                                <Trigger Property="IsPressed" Value="True">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#B5582F"/>
                                </Trigger>
                                <Trigger Property="IsEnabled" Value="False">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#C8BEB4"/>
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>

            <!-- Quick command pill button -->
            <Style x:Key="QuickBtn" TargetType="Button">
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="Button">
                            <Border x:Name="border" Background="#1ED97757"
                                    CornerRadius="14" Padding="12,5">
                                <ContentPresenter HorizontalAlignment="Center"
                                                  VerticalAlignment="Center"/>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsMouseOver" Value="True">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#30D97757"/>
                                </Trigger>
                                <Trigger Property="IsPressed" Value="True">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#50D97757"/>
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>

            <!-- Header export button -->
            <Style x:Key="HeaderBtn" TargetType="Button">
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="Button">
                            <Border x:Name="border" Background="Transparent"
                                    CornerRadius="8" Padding="10,5"
                                    BorderBrush="#E0DCD4" BorderThickness="1">
                                <ContentPresenter HorizontalAlignment="Center"
                                                  VerticalAlignment="Center"/>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsMouseOver" Value="True">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#EDE8E0"/>
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>
        </Window.Resources>

        <DockPanel>
            <!-- ── Header ── -->
            <Border DockPanel.Dock="Top" Background="White" Padding="16,12"
                    BorderBrush="#E0DCD4" BorderThickness="0,0,0,1">
                <DockPanel>
                    <Button DockPanel.Dock="Right" Content="&#x5bfc;&#x51fa;"
                            FontSize="12" Foreground="#6B6560" Cursor="Hand"
                            Margin="8,0,0,0"
                            Style="{StaticResource HeaderBtn}"
                            Click="on_export"/>
                    <StackPanel Orientation="Horizontal"
                                VerticalAlignment="Center">
                        <Border Background="#D97757" CornerRadius="8"
                                Width="32" Height="32" Margin="0,0,10,0">
                            <TextBlock Text="&#x2726;" FontSize="16"
                                       Foreground="White"
                                       HorizontalAlignment="Center"
                                       VerticalAlignment="Center"/>
                        </Border>
                        <StackPanel VerticalAlignment="Center">
                            <TextBlock Text="AI &#x667a;&#x5efa;" FontSize="16"
                                       FontWeight="SemiBold"
                                       Foreground="#2D2B28"/>
                            <TextBlock Text="&#x667a;&#x80fd;&#x5bf9;&#x8bdd;&#x5efa;&#x6a21;"
                                       FontSize="11" Foreground="#9B9590"
                                       Margin="0,-1,0,0"/>
                        </StackPanel>
                    </StackPanel>
                </DockPanel>
            </Border>

            <!-- ── Quick commands ── -->
            <Border DockPanel.Dock="Top" Background="White" Padding="12,8"
                    BorderBrush="#E0DCD4" BorderThickness="0,0,0,1">
                <WrapPanel>
                    <Button Content="&#x521b;&#x5efa;&#x67f1;" FontSize="12"
                            Foreground="#D97757" FontWeight="Medium"
                            Margin="0,0,6,4" Cursor="Hand"
                            Style="{StaticResource QuickBtn}"
                            Click="on_quick_column"/>
                    <Button Content="&#x521b;&#x5efa;&#x6881;" FontSize="12"
                            Foreground="#D97757" FontWeight="Medium"
                            Margin="0,0,6,4" Cursor="Hand"
                            Style="{StaticResource QuickBtn}"
                            Click="on_quick_beam"/>
                    <Button Content="&#x751f;&#x6210;&#x6846;&#x67b6;" FontSize="12"
                            Foreground="#D97757" FontWeight="Medium"
                            Margin="0,0,6,4" Cursor="Hand"
                            Style="{StaticResource QuickBtn}"
                            Click="on_quick_frame"/>
                    <Button Content="&#x6a21;&#x578b;&#x6982;&#x51b5;" FontSize="12"
                            Foreground="#D97757" FontWeight="Medium"
                            Margin="0,0,6,4" Cursor="Hand"
                            Style="{StaticResource QuickBtn}"
                            Click="on_quick_summary"/>
                    <Button Content="&#x5e2e;&#x52a9;" FontSize="12"
                            Foreground="#D97757" FontWeight="Medium"
                            Margin="0,0,0,4" Cursor="Hand"
                            Style="{StaticResource QuickBtn}"
                            Click="on_quick_help"/>
                </WrapPanel>
            </Border>

            <!-- ── Input area (bottom) ── -->
            <Border DockPanel.Dock="Bottom" Background="White" Padding="12,10"
                    BorderBrush="#E0DCD4" BorderThickness="0,1,0,0">
                <Grid>
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/>
                        <ColumnDefinition Width="Auto"/>
                    </Grid.ColumnDefinitions>
                    <TextBox x:Name="tb_input" Grid.Column="0"
                             AcceptsReturn="False"
                             KeyDown="on_key_down"
                             Style="{StaticResource InputBox}"/>
                    <Button x:Name="btn_send" Grid.Column="1"
                            Content="&#x53d1;&#x9001;" FontSize="14"
                            Foreground="White"
                            Margin="8,0,0,0" Height="38"
                            Style="{StaticResource SendButton}"
                            Click="on_send"/>
                </Grid>
            </Border>

            <!-- ── Chat area (fills remaining space) ── -->
            <ScrollViewer x:Name="sv_messages"
                          VerticalScrollBarVisibility="Auto"
                          HorizontalScrollBarVisibility="Disabled"
                          Background="#F7F5EE">
                <StackPanel x:Name="sp_messages" Margin="16,16,16,16"/>
            </ScrollViewer>
        </DockPanel>
    </Window>
    """

    def __init__(self, doc, output, client, levels, chat_state,
                 operation_log, conversation_log):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)
        self.doc = doc
        self.output = output
        self.client = client
        self.levels = levels
        self.chat_state = chat_state
        self.operation_log = operation_log
        self.conversation_log = conversation_log
        self._chat_log = []
        self._loading_el = None

        self.append_system(
            u"欢迎使用 AI 智建\n"
            u"输入中文指令即可控制 Revit 建模\n"
            u"例如：在(6000,0)处创建500\u00d7500柱子"
        )

    # ── Bubble rendering ──────────────────────────

    def _make_bubble(self, text, msg_type):
        """Create a styled chat bubble element."""
        wrapper = WSP()
        wrapper.Margin = Thickness(0, 0, 0, 10)

        bubble = WBorder()
        bubble.Padding = Thickness(14, 10, 14, 10)

        tb = WTB()
        tb.Text = text
        tb.TextWrapping = TextWrapping.Wrap
        tb.FontSize = 13.5

        if msg_type == "user":
            bubble.Background = _brush(0xD9, 0x77, 0x57)
            bubble.CornerRadius = CR(14, 14, 4, 14)
            tb.Foreground = _brush(0xFF, 0xFF, 0xFF)
            wrapper.HorizontalAlignment = HorizontalAlignment.Right
            bubble.MaxWidth = 380
        elif msg_type == "ai":
            bubble.Background = _brush(0xFF, 0xFF, 0xFF)
            bubble.CornerRadius = CR(14, 14, 14, 4)
            bubble.BorderBrush = _brush(0xE0, 0xDC, 0xD4)
            bubble.BorderThickness = Thickness(1)
            tb.Foreground = _brush(0x2D, 0x2B, 0x28)
            wrapper.HorizontalAlignment = HorizontalAlignment.Left
            bubble.MaxWidth = 420
        else:
            bubble.Background = _brush(0xED, 0xE8, 0xE0)
            bubble.CornerRadius = CR(10, 10, 10, 10)
            tb.Foreground = _brush(0x6B, 0x65, 0x60)
            tb.FontSize = 12
            wrapper.HorizontalAlignment = HorizontalAlignment.Center
            bubble.MaxWidth = 380

        bubble.Child = tb
        wrapper.Children.Add(bubble)

        time_tb = WTB()
        time_tb.Text = datetime.datetime.now().strftime("%H:%M")
        time_tb.FontSize = 10
        time_tb.Foreground = _brush(0x9B, 0x95, 0x90)
        time_tb.Margin = Thickness(4, 2, 4, 0)
        if msg_type == "user":
            time_tb.HorizontalAlignment = HorizontalAlignment.Right
        elif msg_type == "ai":
            time_tb.HorizontalAlignment = HorizontalAlignment.Left
        else:
            time_tb.HorizontalAlignment = HorizontalAlignment.Center
        wrapper.Children.Add(time_tb)

        return wrapper

    def _add_bubble(self, text, msg_type):
        """Add a chat bubble and scroll to bottom."""
        if not _HAS_WPF:
            return None
        el = self._make_bubble(text, msg_type)
        self.sp_messages.Children.Add(el)
        self.sv_messages.UpdateLayout()
        self.sv_messages.ScrollToEnd()
        return el

    def _force_render(self):
        """Force WPF to process pending render operations."""
        try:
            self.Dispatcher.Invoke(
                DispatcherPriority.Render,
                System.Action(lambda: None),
            )
        except Exception:
            pass

    def _show_loading(self):
        """Show a 'thinking' bubble and force-render it."""
        self._loading_el = self._add_bubble(u"AI \u6b63\u5728\u601d\u8003...", "system")
        self._force_render()

    def _hide_loading(self):
        """Remove the 'thinking' bubble."""
        if self._loading_el is not None:
            try:
                self.sp_messages.Children.Remove(self._loading_el)
            except Exception:
                pass
            self._loading_el = None

    # ── Public message API ────────────────────────

    def append_user(self, text):
        self._chat_log.append(("user", text))
        self._add_bubble(text, "user")

    def append_ai(self, text):
        self._chat_log.append(("ai", text))
        self._add_bubble(text, "ai")

    def append_system(self, text):
        self._chat_log.append(("system", text))
        self._add_bubble(text, "system")

    # ── Actions ───────────────────────────────────

    def _do_send(self):
        """Process the current input."""
        text = self.tb_input.Text.strip()
        if not text:
            return

        self.tb_input.Text = ""

        if text.lower() == "q":
            self.Close()
            return

        self.append_user(text)

        # Handle local commands (/help, /reset, /retry, etc.)
        handled, self.levels = handle_local_command(
            text,
            self.output,
            self.client,
            doc=self.doc,
            levels=self.levels,
            operation_log=self.operation_log,
            conversation_log=self.conversation_log,
            chat_state=self.chat_state,
        )
        if handled:
            self.append_system(u"指令已执行，详情请查看输出面板。")
            return

        # Show loading, call AI, hide loading
        self.btn_send.IsEnabled = False
        self._show_loading()
        try:
            self.levels = run_ai_turn(
                self.doc,
                self.output,
                self.client,
                self.levels,
                text,
                self.operation_log,
                self.conversation_log,
                self.chat_state,
            )
        finally:
            self._hide_loading()
            self.btn_send.IsEnabled = True
            self.tb_input.Focus()

        # Show result in chat window
        result = self.chat_state.get("last_result")
        if result:
            self.append_ai(result)
        else:
            reply = self.chat_state.get("last_reply")
            if reply:
                self.append_ai(reply)
            else:
                self.append_system(u"执行完成。")

    def on_send(self, sender, args):
        self._do_send()

    def on_key_down(self, sender, args):
        if Key and args.Key == Key.Return:
            self._do_send()
            args.Handled = True

    def on_export(self, sender, args):
        """Export chat content to a text file."""
        if not self._chat_log:
            return
        prefixes = {"user": u"[你]", "ai": u"[AI]", "system": u"[系统]"}
        lines = [u"{} {}".format(prefixes.get(t, ""), m)
                 for t, m in self._chat_log]
        content = u"\n".join(lines)
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

    # ── Quick commands ────────────────────────────

    def on_quick_column(self, sender, args):
        self.tb_input.Text = u"在1-A位置创建一根柱子"
        self._do_send()

    def on_quick_beam(self, sender, args):
        self.tb_input.Text = u"在1楼A-B轴之间创建一根梁"
        self._do_send()

    def on_quick_frame(self, sender, args):
        self.tb_input.Text = u"生成3x2跨5层框架"
        self._do_send()

    def on_quick_summary(self, sender, args):
        self.tb_input.Text = u"查询模型概况"
        self._do_send()

    def on_quick_help(self, sender, args):
        self.tb_input.Text = u"/help"
        self._do_send()


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

    output.print_md("## AI 智建 — 智能对话建模")

    client = DeepSeekClient()
    levels = get_all_levels(doc)
    chat_state = build_chat_state()

    chat = ChatWindow(
        doc, output, client, levels, chat_state,
        operation_log, conversation_log
    )
    chat.ShowDialog()

    output.print_md("对话结束。")
    conversation_path = export_conversation_log(conversation_log, u"AI对话会话")
    if operation_log.logs:
        log_path = export_operation_log(operation_log, u"AI对话")
        output.print_md("### " + operation_log.get_summary())
        if log_path:
            output.print_md("- 日志已导出：`{}`".format(log_path))
    if conversation_path:
        output.print_md("- 会话记录已导出：`{}`".format(conversation_path))


if __name__ == "__main__":
    main()
