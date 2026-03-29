# -*- coding: utf-8 -*-
"""Modify cross-section, level, and other properties of selected elements."""

__doc__ = "选中构件后修改截面尺寸、标高等属性，支持批量修改"
__title__ = "修改\n构件"
__author__ = "AI智建"

from pyrevit import revit, forms, script

from engine.logger import OperationLog, export_operation_log
from engine.modify import modify_element, batch_modify_by_filter
from utils import get_sorted_levels, list_story_floor_choices

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


MODE_SINGLE = u"单个修改"
MODE_BATCH = u"批量修改"


class StoryFloorOption(object):
    """Story floor option for batch operations."""

    def __init__(self, floor_number, level):
        self.floor_number = floor_number
        self.level = level
        self.Name = u"第 {} 层（{}）".format(floor_number, level.Name)


def _build_floor_options(levels, category):
    return [
        StoryFloorOption(floor_number, level)
        for floor_number, level in list_story_floor_choices(levels, category)
    ]


class ModifyForm(forms.WPFWindow):
    """Modify element form — single window replaces multi-step dialogs."""

    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI 智建 — 修改构件" Width="420" Height="420"
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

    def __init__(self, floor_options):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)
        self.result = None
        self._floor_options = floor_options
        for opt in floor_options:
            self.cb_floor.Items.Add(opt.Name)
        if self.cb_floor.Items.Count > 0:
            self.cb_floor.SelectedIndex = 0

    def on_mode_changed(self, sender, args):
        from System.Windows import Visibility
        if self.cb_mode.SelectedIndex == 1:
            self.panel_batch.Visibility = Visibility.Visible
        else:
            self.panel_batch.Visibility = Visibility.Collapsed

    def on_cancel(self, sender, args):
        self.Close()

    def on_confirm(self, sender, args):
        new_section = self.tb_new_section.Text.strip()
        if not new_section:
            return
        if self.cb_mode.SelectedIndex == 0:
            self.result = {"mode": "single", "new_section": new_section}
        else:
            floor_idx = self.cb_floor.SelectedIndex
            floor_number = self._floor_options[floor_idx].floor_number if floor_idx >= 0 and floor_idx < len(self._floor_options) else None
            cat_index = self.cb_category.SelectedIndex
            old_section = self.tb_old_section.Text.strip()
            if not old_section:
                return
            self.result = {
                "mode": "batch",
                "category": "column" if cat_index == 0 else "beam",
                "floor_number": floor_number,
                "old_section": old_section,
                "new_section": new_section,
            }
        self.Close()


def main():
    doc = revit.doc
    logger = script.get_logger()
    operation_log = OperationLog()

    try:
        levels = get_sorted_levels(doc)
        floor_options = _build_floor_options(levels, "column")

        form = ModifyForm(floor_options)
        form.ShowDialog()

        if not form.result:
            script.exit()

        result = form.result

        if result["mode"] == "single":
            try:
                element = revit.pick_element("选择要修改的构件")
            except Exception:
                script.exit()
            if not element:
                script.exit()
            with revit.Transaction(u"AI智建：修改构件"):
                msg = modify_element(doc, element.Id, new_section=result["new_section"])
            operation_log.log("modify_element", msg)
        else:
            with revit.Transaction(u"AI智建：修改构件"):
                msg = batch_modify_by_filter(
                    doc,
                    result["category"],
                    result["floor_number"],
                    result["old_section"],
                    result["new_section"]
                )
            operation_log.log("batch_modify_by_filter", msg)

        log_path = export_operation_log(operation_log, u"修改构件")
        message = msg
        if log_path:
            message += u"\n\n{}\n日志：{}".format(operation_log.get_summary(), log_path)
        forms.alert(message, title=u"AI 智建")
    except Exception as err:
        logger.exception(err)
        forms.alert(u"修改构件时发生错误：{}".format(err), title=u"AI 智建")


if __name__ == "__main__":
    main()
