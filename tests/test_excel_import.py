# -*- coding: utf-8 -*-

import pytest

from conftest import load_project_script
from tools.offline_runtime import make_story_levels


excel_import = load_project_script(
    "excel_import_script",
    "AI智建.extension/AI智建.tab/框架建模.panel/Excel导入.pushbutton/script.py",
)


def test_parse_row_for_column_uses_story_base_and_top_levels():
    levels = make_story_levels(3)
    header_map = {
        "type": 0,
        "x": 1,
        "y": 2,
        "floor": 3,
        "section": 4,
    }

    result = excel_import._parse_row(2, ("柱", 0, 6000, 1, "500x500"), header_map, levels)

    assert result["kind"] == "column"
    assert result["base_level"].Name == "±0.000"
    assert result["top_level"].Name == "F1"


def test_parse_row_for_beam_uses_story_framing_level():
    levels = make_story_levels(3)
    header_map = {
        "type": 0,
        "x": 1,
        "y": 2,
        "floor": 3,
        "section": 4,
    }

    result = excel_import._parse_row(3, ("梁", "0,0", "6000,0", 2, "300x600"), header_map, levels)

    assert result["kind"] == "beam"
    assert result["level"].Name == "F2"


def test_parse_row_rejects_out_of_range_floor():
    levels = make_story_levels(2)
    header_map = {
        "type": 0,
        "x": 1,
        "y": 2,
        "floor": 3,
        "section": 4,
    }

    with pytest.raises(ValueError, match="楼层 3 超出当前标高范围"):
        excel_import._parse_row(4, ("梁", "0,0", "6000,0", 3, "300x600"), header_map, levels)
