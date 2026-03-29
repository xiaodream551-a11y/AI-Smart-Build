# -*- coding: utf-8 -*-

from tools.offline_runtime import FakeBuiltInCategory, make_story_levels

from utils import (
    get_story_count,
    list_story_floor_choices,
    normalize_floor_number,
    resolve_floor_boundary_level,
    resolve_story_base_level,
    resolve_story_framing_level,
    resolve_story_level_by_category,
)


def test_normalize_floor_number():
    assert normalize_floor_number("2") == 2
    assert normalize_floor_number(3) == 3
    assert normalize_floor_number(" 4 ") == 4
    assert normalize_floor_number("0") is None
    assert normalize_floor_number("-1") is None
    assert normalize_floor_number("abc") is None


def test_story_level_resolution():
    levels = make_story_levels(3)

    assert get_story_count(levels) == 3
    assert [level.Name for level in levels] == ["±0.000", "F1", "F2", "屋面"]

    assert resolve_floor_boundary_level(levels, 1).Name == "±0.000"
    assert resolve_floor_boundary_level(levels, 2).Name == "F1"
    assert resolve_floor_boundary_level(levels, 4).Name == "屋面"
    assert resolve_floor_boundary_level(levels, 5) is None

    assert resolve_story_base_level(levels, 1).Name == "±0.000"
    assert resolve_story_base_level(levels, 2).Name == "F1"
    assert resolve_story_base_level(levels, 4) is None

    assert resolve_story_framing_level(levels, 1).Name == "F1"
    assert resolve_story_framing_level(levels, 2).Name == "F2"
    assert resolve_story_framing_level(levels, 3).Name == "屋面"
    assert resolve_story_framing_level(levels, 4) is None


def test_story_level_resolution_by_category():
    levels = make_story_levels(3)

    assert resolve_story_level_by_category(levels, "column", 1).Name == "±0.000"
    assert resolve_story_level_by_category(levels, "beam", 2).Name == "F2"
    assert resolve_story_level_by_category(
        levels,
        FakeBuiltInCategory.OST_StructuralColumns,
        2
    ).Name == "F1"
    assert resolve_story_level_by_category(
        levels,
        FakeBuiltInCategory.OST_Floors,
        3
    ).Name == "屋面"


def test_story_floor_choices_follow_category_semantics():
    levels = make_story_levels(3)

    column_choices = list_story_floor_choices(levels, "column")
    beam_choices = list_story_floor_choices(levels, "beam")

    assert [(floor, level.Name) for floor, level in column_choices] == [
        (1, "±0.000"),
        (2, "F1"),
        (3, "F2"),
    ]
    assert [(floor, level.Name) for floor, level in beam_choices] == [
        (1, "F1"),
        (2, "F2"),
        (3, "屋面"),
    ]
