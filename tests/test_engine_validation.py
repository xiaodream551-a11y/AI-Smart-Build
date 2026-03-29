# -*- coding: utf-8 -*-

import pytest

from engine import beam, column, floor, frame_generator
from tools.offline_runtime import make_story_levels


def test_create_column_rejects_invalid_section():
    levels = make_story_levels(2)

    with pytest.raises(ValueError, match="截面"):
        column.create_column(None, 0, 0, levels[0], levels[1], "0x0")


def test_create_column_requires_base_level():
    levels = make_story_levels(2)

    with pytest.raises(ValueError, match="柱底标高不能为空"):
        column.create_column(None, 0, 0, None, levels[1], "500x500")


def test_create_column_requires_top_level():
    levels = make_story_levels(2)

    with pytest.raises(ValueError, match="柱顶标高不能为空"):
        column.create_column(None, 0, 0, levels[0], None, "500x500")


def test_create_column_requires_base_lower_than_top():
    levels = make_story_levels(2)

    with pytest.raises(ValueError, match="柱底标高必须低于柱顶标高"):
        column.create_column(None, 0, 0, levels[1], levels[0], "500x500")


def test_create_beam_rejects_zero_length():
    levels = make_story_levels(2)

    with pytest.raises(ValueError, match="零长度梁"):
        beam.create_beam(None, 0, 0, 0, 0, levels[1], "300x600")


def test_create_beam_rejects_invalid_section():
    levels = make_story_levels(2)

    with pytest.raises(ValueError, match="截面"):
        beam.create_beam(None, 0, 0, 6000, 0, levels[1], "abc")


def test_create_beam_requires_level():
    with pytest.raises(ValueError, match="梁所在标高不能为空"):
        beam.create_beam(None, 0, 0, 6000, 0, None, "300x600")


def test_create_floor_requires_at_least_three_points():
    levels = make_story_levels(2)

    with pytest.raises(ValueError, match="至少需要 3 个点"):
        floor.create_floor(None, [(0, 0), (1, 0)], levels[1])


def test_create_floor_rejects_collinear_points():
    levels = make_story_levels(2)

    with pytest.raises(ValueError, match="不能共线"):
        floor.create_floor(None, [(0, 0), (1, 0), (2, 0)], levels[1])


def test_create_floor_requires_level():
    with pytest.raises(ValueError, match="楼板标高不能为空"):
        floor.create_floor(None, [(0, 0), (1, 0), (1, 1)], None)


def test_generate_frame_rejects_invalid_column_section():
    with pytest.raises(ValueError, match="柱截面无效"):
        frame_generator.generate_frame(None, {
            "x_spans": [6000],
            "y_spans": [6000],
            "num_floors": 1,
            "floor_height": 3600,
            "column_section": "bad",
        })


def test_generate_frame_rejects_invalid_beam_section_x():
    with pytest.raises(ValueError, match="X 向梁截面无效"):
        frame_generator.generate_frame(None, {
            "x_spans": [6000],
            "y_spans": [6000],
            "num_floors": 1,
            "floor_height": 3600,
            "beam_section_x": "0x0",
        })


def test_generate_frame_rejects_invalid_beam_section_y():
    with pytest.raises(ValueError, match="Y 向梁截面无效"):
        frame_generator.generate_frame(None, {
            "x_spans": [6000],
            "y_spans": [6000],
            "num_floors": 1,
            "floor_height": 3600,
            "beam_section_y": "abc",
        })
