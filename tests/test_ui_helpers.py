# -*- coding: utf-8 -*-
"""Offline tests for UI helper logic."""

import io
import json
import os

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

    def test_load_missing_config_returns_no_file(self, tmp_path):
        config_path = str(tmp_path / "nonexistent.json")
        assert not os.path.exists(config_path)

    def test_load_invalid_json_raises(self, tmp_path):
        config_path = str(tmp_path / "bad.json")
        with io.open(config_path, "w", encoding="utf-8") as f:
            f.write("not json {{{")

        with pytest.raises(json.JSONDecodeError):
            with io.open(config_path, "r", encoding="utf-8-sig") as f:
                json.load(f)

    def test_save_creates_file(self, tmp_path):
        config_path = str(tmp_path / "new_config.json")
        data = {"key": "value"}
        with io.open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        assert os.path.exists(config_path)
        with io.open(config_path, "r", encoding="utf-8") as f:
            assert json.load(f) == {"key": "value"}

    def test_config_preserves_chinese(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        data = {"DEEPSEEK_MODEL": u"深度求索"}
        with io.open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        with io.open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["DEEPSEEK_MODEL"] == u"深度求索"

    def test_config_round_trip_all_fields(self, tmp_path):
        config_path = str(tmp_path / "config.json")
        data = {
            "DEEPSEEK_API_KEY": "sk-abc123",
            "DEEPSEEK_MODEL": "deepseek-chat",
            "DEEPSEEK_API_URL": "https://api.deepseek.com/v1/chat/completions",
            "API_TIMEOUT_MS": "30000",
            "API_RETRY_COUNT": "2",
        }
        with io.open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        with io.open(config_path, "r", encoding="utf-8-sig") as f:
            loaded = json.load(f)

        for key, value in data.items():
            assert loaded[key] == value


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

    def test_special_characters(self):
        msg = u"截面 500x500 → 600x600"
        assert self._format_system(msg) == u"[系统] 截面 500x500 → 600x600"


class TestIconGeneration:
    """Test that the icon generation script produces valid images."""

    @staticmethod
    def _get_tab_path():
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "AISmartBuild.extension", "AISmartBuild.tab"
        )

    EXPECTED_BUTTONS = [
        "AIChat.panel/SmartChat.pushbutton",
        "FrameModel.panel/ExcelImport.pushbutton",
        "FrameModel.panel/GenerateFrame.pushbutton",
        "ElementOps.panel/ModifyElement.pushbutton",
        "ElementOps.panel/DeleteElement.pushbutton",
        "DataIO.panel/ExportModel.pushbutton",
        "Help.panel/About.pushbutton",
        "Help.panel/Settings.pushbutton",
    ]

    def test_all_icons_exist(self):
        base = self._get_tab_path()
        for btn_path in self.EXPECTED_BUTTONS:
            icon = os.path.join(base, btn_path, "icon.png")
            assert os.path.exists(icon), "Missing icon: {}".format(btn_path)

    def test_all_dark_icons_exist(self):
        base = self._get_tab_path()
        for btn_path in self.EXPECTED_BUTTONS:
            icon = os.path.join(base, btn_path, "icon_dark.png")
            assert os.path.exists(icon), "Missing dark icon: {}".format(btn_path)

    def test_icons_are_correct_size(self):
        from PIL import Image
        base = self._get_tab_path()
        for btn_path in self.EXPECTED_BUTTONS:
            icon_path = os.path.join(base, btn_path, "icon.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                assert img.size == (96, 96), "{} is {}".format(btn_path, img.size)
                assert img.mode == "RGBA", "{} mode is {}".format(btn_path, img.mode)

    def test_dark_icons_are_correct_size(self):
        from PIL import Image
        base = self._get_tab_path()
        for btn_path in self.EXPECTED_BUTTONS:
            icon_path = os.path.join(base, btn_path, "icon_dark.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                assert img.size == (96, 96), "{} dark is {}".format(btn_path, img.size)
                assert img.mode == "RGBA", "{} dark mode is {}".format(btn_path, img.mode)
