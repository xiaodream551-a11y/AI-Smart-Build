# -*- coding: utf-8 -*-
"""AI chat-based intelligent modeling."""

__doc__ = "用中文对话控制 Revit 建模 — 输入指令，AI 自动执行"
__title__ = "智能\n对话"
__author__ = "AI智建"

from pyrevit import forms, revit, script

from config import DEEPSEEK_API_KEY, USER_CONFIG_PATH
from ai.chat_common import get_all_levels
from ai.chat_controller import build_chat_state, handle_local_command, run_ai_turn
from ai.client import DeepSeekClient
from engine.logger import ConversationLog, OperationLog, export_conversation_log, export_operation_log

try:
    from System.Windows.Input import Key
except Exception:
    Key = None


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

            <!-- Hint bar -->
            <Border DockPanel.Dock="Top" Background="#E8EDF2" Padding="16,6">
                <TextBlock FontSize="11" Foreground="#666666" TextWrapping="Wrap">
                    <Run Text="输入中文指令，如 &quot;在(6000,0)处创建500x500柱子&quot;"/>
                    <Run Text=" | /help 查看帮助 | /reset 重置 | q 退出"/>
                </TextBlock>
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

    def _append(self, text):
        """Append text to output area and scroll to end."""
        self.tb_output.Text += text + u"\n"
        self.tb_output.ScrollToEnd()

    def append_user(self, text):
        self._append(u"[你] {}".format(text))

    def append_ai(self, text):
        self._append(u"[AI] {}".format(text))

    def append_system(self, text):
        self._append(u"[系统] {}".format(text))

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

        # Run AI turn
        self.append_system(u"AI 正在思考...")
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
