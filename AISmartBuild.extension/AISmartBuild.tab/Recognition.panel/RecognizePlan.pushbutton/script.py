# -*- coding: utf-8 -*-
"""Drawing recognition — Claude-style UI."""

__doc__ = "上传建筑平面图，AI 自动识别并生成 Revit 模型"
__title__ = "图纸\n识别"
__author__ = "AI智建"

from pyrevit import forms, revit, script, DB

from config import VISION_API_KEY, VISION_API_URL, VISION_MODEL
from ai.chat_common import get_all_levels
from recognition.recognizer import PlanRecognizer
from recognition.dispatcher import generate_build_plan, preview_build_plan
from recognition.executor import execute_build_plan, format_result

try:
    import System
    from System.Windows.Media.Imaging import BitmapImage
    from System import Uri, UriKind
    from System.Windows import Visibility
    from System.Windows.Threading import DispatcherPriority
except Exception:
    pass


class RecognitionWindow(forms.WPFWindow):
    """Drawing recognition window — Claude style."""

    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            Title="AI &#x667a;&#x5efa; &#x2014; &#x56fe;&#x7eb8;&#x8bc6;&#x522b;"
            Width="600" Height="750"
            WindowStartupLocation="CenterScreen"
            MinWidth="480" MinHeight="550"
            Background="#F7F5EE"
            FontFamily="Microsoft YaHei, Segoe UI, sans-serif">

        <Window.Resources>
            <Style x:Key="AccentBtn" TargetType="Button">
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="Button">
                            <Border x:Name="border" Background="#D97757"
                                    CornerRadius="12" Padding="16,7">
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

            <Style x:Key="OutlineBtn" TargetType="Button">
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="Button">
                            <Border x:Name="border" Background="Transparent"
                                    CornerRadius="12" Padding="16,7"
                                    BorderBrush="#E0DCD4" BorderThickness="1.5">
                                <ContentPresenter HorizontalAlignment="Center"
                                                  VerticalAlignment="Center"/>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsMouseOver" Value="True">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#EDE8E0"/>
                                </Trigger>
                                <Trigger Property="IsEnabled" Value="False">
                                    <Setter TargetName="border"
                                            Property="Background" Value="#F0ECE4"/>
                                    <Setter TargetName="border"
                                            Property="BorderBrush" Value="#E8E4DC"/>
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>
        </Window.Resources>

        <DockPanel>
            <!-- &#x2500;&#x2500; Header &#x2500;&#x2500; -->
            <Border DockPanel.Dock="Top" Background="White" Padding="16,12"
                    BorderBrush="#E0DCD4" BorderThickness="0,0,0,1">
                <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
                    <Border Background="#D97757" CornerRadius="8"
                            Width="32" Height="32" Margin="0,0,10,0">
                        <TextBlock Text="&#x2726;" FontSize="16"
                                   Foreground="White"
                                   HorizontalAlignment="Center"
                                   VerticalAlignment="Center"/>
                    </Border>
                    <StackPanel VerticalAlignment="Center">
                        <TextBlock Text="AI &#x667a;&#x5efa;" FontSize="16"
                                   FontWeight="SemiBold" Foreground="#2D2B28"/>
                        <TextBlock Text="&#x56fe;&#x7eb8;&#x8bc6;&#x522b;&#x5efa;&#x6a21;"
                                   FontSize="11" Foreground="#9B9590"
                                   Margin="0,-1,0,0"/>
                    </StackPanel>
                </StackPanel>
            </Border>

            <!-- &#x2500;&#x2500; Bottom toolbar &#x2500;&#x2500; -->
            <Border DockPanel.Dock="Bottom" Background="White" Padding="16,10"
                    BorderBrush="#E0DCD4" BorderThickness="0,1,0,0">
                <StackPanel Orientation="Horizontal"
                            HorizontalAlignment="Center">
                    <Button x:Name="btn_browse"
                            Content="&#x9009;&#x62e9;&#x56fe;&#x7eb8;"
                            FontSize="13" Foreground="#2D2B28"
                            Cursor="Hand" Margin="0,0,10,0"
                            Style="{StaticResource OutlineBtn}"
                            Click="on_browse"/>
                    <Button x:Name="btn_recognize"
                            Content="&#x5f00;&#x59cb;&#x8bc6;&#x56fe;"
                            FontSize="13" Foreground="White"
                            Cursor="Hand" Margin="0,0,10,0"
                            IsEnabled="False"
                            Style="{StaticResource AccentBtn}"
                            Click="on_recognize"/>
                    <Button x:Name="btn_execute"
                            Content="&#x6267;&#x884c;&#x5efa;&#x6a21;"
                            FontSize="13" Foreground="White"
                            Cursor="Hand" IsEnabled="False"
                            Style="{StaticResource AccentBtn}"
                            Click="on_execute"/>
                </StackPanel>
            </Border>

            <!-- &#x2500;&#x2500; Main content &#x2500;&#x2500; -->
            <Grid Margin="16,12,16,12">
                <Grid.RowDefinitions>
                    <RowDefinition Height="200"/>
                    <RowDefinition Height="8"/>
                    <RowDefinition Height="*"/>
                </Grid.RowDefinitions>

                <!-- Image preview -->
                <Border Grid.Row="0" Background="#EDE8E0"
                        CornerRadius="10" ClipToBounds="True">
                    <Grid>
                        <TextBlock x:Name="txt_placeholder"
                                   Text="&#x70b9;&#x51fb;&#x300c;&#x9009;&#x62e9;&#x56fe;&#x7eb8;&#x300d;&#x52a0;&#x8f7d;&#x5efa;&#x7b51;&#x5e73;&#x9762;&#x56fe;"
                                   HorizontalAlignment="Center"
                                   VerticalAlignment="Center"
                                   Foreground="#9B9590" FontSize="14"/>
                        <Image x:Name="img_preview" Stretch="Uniform"
                               Margin="6"/>
                    </Grid>
                </Border>

                <!-- Output log -->
                <Border Grid.Row="2" Background="White"
                        CornerRadius="10" BorderBrush="#E0DCD4"
                        BorderThickness="1" ClipToBounds="True">
                    <TextBox x:Name="tb_output" IsReadOnly="True"
                             TextWrapping="Wrap"
                             VerticalScrollBarVisibility="Auto"
                             BorderThickness="0" Background="Transparent"
                             Foreground="#2D2B28" FontSize="13"
                             FontFamily="Consolas, Microsoft YaHei"
                             Padding="12,10"/>
                </Border>
            </Grid>
        </DockPanel>
    </Window>
    """

    def __init__(self, doc):
        forms.WPFWindow.__init__(self, self.layout, literal_string=True)
        self.doc = doc
        self._image_path = None
        self._plan = None
        self._recognition_data = None
        self._log(u"就绪。请选择一张建筑平面图开始识别。")

    # ── Helpers ───────────────────────────────────

    def _log(self, text):
        if self.tb_output.Text:
            self.tb_output.Text += u"\n"
        self.tb_output.Text += text
        self.tb_output.ScrollToEnd()

    def _force_render(self):
        try:
            self.Dispatcher.Invoke(
                DispatcherPriority.Render,
                System.Action(lambda: None),
            )
        except Exception:
            pass

    def _load_preview(self, path):
        try:
            bmp = BitmapImage()
            bmp.BeginInit()
            bmp.UriSource = Uri(path, UriKind.Absolute)
            bmp.DecodePixelHeight = 400
            bmp.EndInit()
            self.img_preview.Source = bmp
            self.txt_placeholder.Visibility = Visibility.Collapsed
        except Exception:
            self._log(u"[警告] 图片预览加载失败")

    # ── Event handlers ────────────────────────────

    def on_browse(self, sender, args):
        path = forms.pick_file(
            file_ext="png;jpg;jpeg;bmp",
            title=u"选择建筑平面图",
        )
        if not path:
            return
        self._image_path = path
        self._plan = None
        self._recognition_data = None
        self.btn_recognize.IsEnabled = True
        self.btn_execute.IsEnabled = False
        self.tb_output.Text = ""
        self._log(u"已选择: {}".format(path))
        self._load_preview(path)

    def on_recognize(self, sender, args):
        if not self._image_path:
            return

        self.btn_browse.IsEnabled = False
        self.btn_recognize.IsEnabled = False
        self.btn_execute.IsEnabled = False
        self._log(u"\n--- 开始识别 ---")
        self._force_render()

        recognizer = PlanRecognizer()

        try:
            # Step 1
            self._log(u"\n[Step 1/3] 识别轴网和标高...")
            self._force_render()
            step1 = recognizer.recognize_step1(self._image_path)
            grids = step1.get("grids", {})
            x_count = len(grids.get("x", []))
            y_count = len(grids.get("y", []))
            self._log(u"  \u2713 轴网 {}+{} 条，标高 {} 层".format(
                x_count, y_count, len(step1.get("levels", []))))

            # Step 2
            self._log(u"\n[Step 2/3] 识别墙体...")
            self._force_render()
            step2 = recognizer.recognize_step2(self._image_path, step1)
            walls = step2.get("walls", [])
            self._log(u"  \u2713 墙体 {} 道".format(len(walls)))

            # Step 3
            self._log(u"\n[Step 3/3] 识别门窗...")
            self._force_render()
            step3 = recognizer.recognize_step3(self._image_path, step1, step2)
            doors = step3.get("doors", [])
            windows = step3.get("windows", [])
            self._log(u"  \u2713 门 {} 个, 窗 {} 个".format(
                len(doors), len(windows)))

            # Merge and convert
            from recognition.recognizer import RecognitionResult
            result = RecognitionResult(step1, step2, step3)

            if not result.ok:
                self._log(u"\n[警告] 识别结果存在问题:")
                for err in result.errors:
                    self._log(u"  - {}".format(err))

            self._recognition_data = result.to_dict()
            self._plan = generate_build_plan(self._recognition_data)

            self._log(u"\n" + preview_build_plan(self._plan))
            self.btn_execute.IsEnabled = bool(self._plan)

        except Exception as e:
            self._log(u"\n[错误] 识别失败: {}".format(str(e)))

        self.btn_browse.IsEnabled = True
        self.btn_recognize.IsEnabled = True

    def on_execute(self, sender, args):
        if not self._plan:
            return

        self.btn_browse.IsEnabled = False
        self.btn_recognize.IsEnabled = False
        self.btn_execute.IsEnabled = False

        levels = get_all_levels(self.doc)
        base_level = levels[0] if levels else None

        self._log(u"\n--- 开始建模 ({} 步) ---".format(len(self._plan)))
        self._force_render()

        def on_progress(step, total, desc):
            self._log(u"  [{}/{}] {}".format(step, total, desc))
            self._force_render()

        try:
            t = DB.Transaction(self.doc, u"AI 智建 — 图纸识别建模")
            t.Start()
            try:
                result = execute_build_plan(
                    self.doc, self._plan, base_level, on_progress)
                t.Commit()
            except Exception:
                t.RollBack()
                raise

            self._log(u"\n" + format_result(result))
            self._plan = None

        except Exception as e:
            self._log(u"\n[错误] 建模失败: {}".format(str(e)))

        self.btn_browse.IsEnabled = True
        self.btn_recognize.IsEnabled = True


def main():
    doc = revit.doc
    output = script.get_output()

    if not VISION_API_KEY:
        forms.alert(
            u"请先配置 Vision API Key\n\n"
            u"当前模型: {}\n"
            u"API 地址: {}\n\n"
            u"可通过环境变量或 ~/.ai-smart-build/config.json 配置:\n"
            u"  VISION_API_KEY\n"
            u"  VISION_API_URL\n"
            u"  VISION_MODEL".format(VISION_MODEL, VISION_API_URL),
            title=u"AI 智建 — Vision 配置缺失"
        )
        script.exit()

    output.print_md("## AI 智建 — 图纸识别")
    win = RecognitionWindow(doc)
    win.ShowDialog()
    output.print_md("图纸识别结束。")


if __name__ == "__main__":
    main()
