# -*- coding: utf-8 -*-
"""Delete specified elements or batch-delete by filter criteria."""

__doc__ = "删除选中构件，或按楼层/类型批量删除"
__title__ = "删除\n构件"
__author__ = "AI智建"

from pyrevit import revit, forms, script

from engine.logger import OperationLog, export_operation_log
from engine.modify import delete_element, batch_delete_by_filter
from utils import get_sorted_levels, list_story_floor_choices


MODE_SINGLE = u"单个删除"
MODE_BATCH = u"批量删除"


class FloorOption(object):
    """Floor selection option."""

    def __init__(self, name, floor_number=None):
        self.Name = name
        self.floor_number = floor_number


def _confirm(message):
    return forms.alert(
        message,
        title=u"AI 智建",
        yes=True,
        no=True
    )


def _get_element_label(element):
    if element and element.Category:
        return element.Category.Name
    return u"构件"


def _build_floor_options(doc, category):
    return [
        FloorOption(
            u"第 {} 层（{}）".format(floor_number, level.Name),
            floor_number=floor_number
        )
        for floor_number, level in list_story_floor_choices(
            get_sorted_levels(doc), category
        )
    ]


class DeleteForm(forms.WPFWindow):
    """Delete element form — single window replaces multi-step dialogs."""

    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI 智建 — 删除构件" Width="420" Height="380"
            WindowStartupLocation="CenterScreen"
            ResizeMode="NoResize" Background="#F0F0F0">

        <Window.Resources>
            <Style x:Key="FieldLabel" TargetType="TextBlock">
                <Setter Property="VerticalAlignment" Value="Center"/>
                <Setter Property="Foreground" Value="#333333"/>
                <Setter Property="FontSize" Value="13"/>
            </Style>
        </Window.Resources>

        <DockPanel>
            <Border DockPanel.Dock="Top" Background="#1E3A5F" Padding="20,12">
                <TextBlock Text="删除构件" FontSize="18" FontWeight="Bold" Foreground="White"/>
            </Border>

            <Border DockPanel.Dock="Bottom" Padding="20,10">
                <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">
                    <Button Content="取消" Width="80" Height="36" Margin="0,0,10,0"
                            Click="on_cancel"/>
                    <Button Content="确定删除" Height="36" Foreground="White" Click="on_confirm">
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
                        <TextBlock Text="删除模式" Style="{StaticResource FieldLabel}"/>
                        <ComboBox x:Name="cb_mode" Grid.Column="1" Height="30"
                                  FontSize="13" SelectedIndex="0"
                                  SelectionChanged="on_mode_changed">
                            <ComboBoxItem Content="单个删除"/>
                            <ComboBoxItem Content="批量删除"/>
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
                                <ComboBoxItem Content="板"/>
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
                    </StackPanel>
                </StackPanel>
            </Border>
        </DockPanel>
    </Window>
    """

    def __init__(self, floor_options):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)
        self.result = None
        self._floor_options = floor_options
        self.cb_floor.Items.Add(u"全部楼层")
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
        if self.cb_mode.SelectedIndex == 0:
            self.result = {"mode": "single"}
        else:
            cat_index = self.cb_category.SelectedIndex
            category_map = {0: "column", 1: "beam", 2: "slab"}
            category = category_map[cat_index]

            floor_idx = self.cb_floor.SelectedIndex
            if floor_idx <= 0:
                floor_number = None
            else:
                opt_idx = floor_idx - 1
                floor_number = self._floor_options[opt_idx].floor_number if opt_idx < len(self._floor_options) else None

            category_labels = {0: u"柱", 1: u"梁", 2: u"板"}
            self.result = {
                "mode": "batch",
                "category": category,
                "floor_number": floor_number,
                "category_label": category_labels[cat_index],
            }
        self.Close()


def main():
    doc = revit.doc
    logger = script.get_logger()
    operation_log = OperationLog()

    try:
        floor_options = _build_floor_options(doc, "column")

        form = DeleteForm(floor_options)
        form.ShowDialog()

        if not form.result:
            script.exit()

        result = form.result

        if result["mode"] == "single":
            try:
                element = revit.pick_element("选择要删除的构件")
            except Exception:
                script.exit()
            if not element:
                script.exit()

            confirm_text = u"确定要删除{}(ID: {})吗？".format(
                _get_element_label(element),
                element.Id.IntegerValue
            )
            if not _confirm(confirm_text):
                script.exit()

            with revit.Transaction(u"AI智建：删除构件"):
                msg = delete_element(doc, element.Id)
            operation_log.log("delete_element", msg)
        else:
            if result["floor_number"]:
                confirm_text = u"确定要删除第 {} 层的所有{}吗？".format(
                    result["floor_number"],
                    result["category_label"]
                )
            else:
                confirm_text = u"确定要删除所有{}吗？".format(result["category_label"])

            if not _confirm(confirm_text):
                script.exit()

            with revit.Transaction(u"AI智建：删除构件"):
                msg = batch_delete_by_filter(
                    doc,
                    result["category"],
                    result["floor_number"]
                )
            operation_log.log("batch_delete_by_filter", msg)

        log_path = export_operation_log(operation_log, u"删除构件")
        message = msg
        if log_path:
            message += u"\n\n{}\n日志：{}".format(operation_log.get_summary(), log_path)
        forms.alert(message, title=u"AI 智建")
    except Exception as err:
        logger.exception(err)
        forms.alert(u"删除构件时发生错误：{}".format(err), title=u"AI 智建")


if __name__ == "__main__":
    main()
