# -*- coding: utf-8 -*-
"""One-click frame structure model generation."""

__doc__ = "输入结构参数，自动生成完整的多层框架结构（轴网+标高+柱+梁+板）"
__title__ = "一键\n生成"
__author__ = "AI智建"

from pyrevit import revit, DB, forms, script

from engine.frame_generator import generate_frame, format_stats
from engine.logger import OperationLog, export_operation_log

# ============================================================
# Parameter input form
# ============================================================

class FrameParamsForm(forms.WPFWindow):
    """Frame structure parameter input panel."""

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

            <!-- Bottom button -->
            <Border DockPanel.Dock="Bottom" Padding="20,12" Background="#F0F0F0">
                <Button Content="生 成 框 架" FontSize="15" FontWeight="Bold"
                        Height="42" Foreground="White"
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

            <!-- Main content -->
            <ScrollViewer VerticalScrollBarVisibility="Auto" Padding="20,16,20,0">
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
        </DockPanel>
    </Window>
    """

    def __init__(self):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)

    def _parse_spans(self, text):
        """Parse span input '6000, 6000, 6000' -> [6000.0, 6000.0, 6000.0]."""
        parts = text.replace("\uff0c", ",").split(",")  # Support Chinese comma
        return [float(p.strip()) for p in parts if p.strip()]

    def on_generate(self, sender, args):
        """Handle generate button click."""
        try:
            params = {
                "x_spans": self._parse_spans(self.tb_x_spans.Text),
                "y_spans": self._parse_spans(self.tb_y_spans.Text),
                "num_floors": int(self.tb_floors.Text),
                "floor_height": float(self.tb_floor_height.Text),
                "column_section": self.tb_col_section.Text.strip(),
                "beam_section_x": self.tb_beam_x.Text.strip(),
                "beam_section_y": self.tb_beam_y.Text.strip(),
            }

            first = self.tb_first_height.Text.strip()
            if first:
                params["first_floor_height"] = float(first)

            self.result = params
            self.Close()

        except Exception as e:
            forms.alert("参数输入有误：{}".format(str(e)), title="输入错误")


# ============================================================
# Main logic
# ============================================================

def main():
    doc = revit.doc
    output = script.get_output()
    operation_log = OperationLog()

    # Show parameter panel
    form = FrameParamsForm()
    form.ShowDialog()

    if not hasattr(form, "result"):
        script.exit()  # User cancelled

    params = form.result

    output.print_md("## AI 智建 — 框架结构生成")
    output.print_md("参数：{x} 跨 x {y} 跨，{n} 层".format(
        x=len(params["x_spans"]),
        y=len(params["y_spans"]),
        n=params["num_floors"],
    ))

    total_steps = 1 + 1 + params["num_floors"] * 3 + 1
    current_step = [0]

    try:
        with forms.ProgressBar(title="AI 智建 — 生成中...", cancellable=True) as pb:
            pb.update_progress(0, total_steps)

            def on_progress(msg):
                if pb.cancelled:
                    raise Exception("用户取消")

                current_step[0] += 1
                pb.title = msg
                pb.update_progress(current_step[0], total_steps)
                output.print_md("- " + msg)

                if pb.cancelled:
                    raise Exception("用户取消")

            # Execute modeling within a transaction
            with revit.Transaction("AI智建：一键生成框架"):
                stats = generate_frame(
                    doc, params,
                    progress_callback=on_progress
                )
    except Exception as err:
        if str(err) == "用户取消":
            forms.alert("用户取消", title="AI 智建")
            return
        raise

    # Output statistics
    operation_log.log("create_grid", "一键生成创建轴网", count=stats["grids"])
    operation_log.log("create_level", "一键生成创建标高", count=stats["levels"])
    operation_log.log("create_column", "一键生成创建结构柱", count=stats["columns"])
    operation_log.log("create_beam", "一键生成创建结构梁", count=stats["beams"])
    operation_log.log("create_floor", "一键生成创建楼板", count=stats["floors"])
    log_path = export_operation_log(operation_log, u"一键生成")

    output.print_md("---")
    output.print_md("### " + format_stats(stats).replace("\n", "\n- "))
    output.print_md("### " + operation_log.get_summary())
    if log_path:
        output.print_md("- 日志已导出：`{}`".format(log_path))

    message = format_stats(stats)
    if log_path:
        message += "\n\n日志：{}".format(log_path)
    forms.alert(message, title="AI 智建 — 生成完成")


# Entry point
if __name__ == "__main__":
    main()
