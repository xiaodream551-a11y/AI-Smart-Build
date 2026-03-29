# -*- coding: utf-8 -*-
"""View plugin version and environment information."""

__doc__ = "查看插件版本与环境信息"
__title__ = "关于"
__author__ = "AI智建"

import sys

from pyrevit import forms, revit

from config import DEEPSEEK_API_KEY, USER_CONFIG_PATH, VERSION

try:
    from pyrevit.versionmgr import get_pyrevit_version
except Exception:
    get_pyrevit_version = None


def _get_pyrevit_version_text():
    if get_pyrevit_version is None:
        return u"未知"

    try:
        version = get_pyrevit_version()
    except Exception:
        return u"未知"

    if version is None:
        return u"未知"

    formatter = getattr(version, "get_formatted", None)
    if callable(formatter):
        try:
            return formatter()
        except Exception:
            pass

    formatted = getattr(version, "formatted", None)
    if formatted:
        return u"{}".format(formatted)
    return u"{}".format(version)


def _get_revit_version_text():
    try:
        app = revit.doc.Application
        return u"{}".format(getattr(app, "VersionNumber", u"未知"))
    except Exception:
        return u"未知"


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


if __name__ == "__main__":
    main()
