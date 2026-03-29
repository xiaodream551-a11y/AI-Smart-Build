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
    """Save config to file, creating directory if needed."""
    config_dir = os.path.dirname(USER_CONFIG_PATH)
    if config_dir and not os.path.exists(config_dir):
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
        self.config_result = None
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
