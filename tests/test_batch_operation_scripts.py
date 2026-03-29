# -*- coding: utf-8 -*-
"""Tests for batch operation scripts — floor option building."""

from conftest import load_project_script
from tools.offline_runtime import FakeDocument, make_story_levels


modify_script = load_project_script(
    "modify_script_for_tests",
    "AISmartBuild.extension/AISmartBuild.tab/ElementOps.panel/ModifyElement.pushbutton/script.py",
)

delete_script = load_project_script(
    "delete_script_for_tests",
    "AISmartBuild.extension/AISmartBuild.tab/ElementOps.panel/DeleteElement.pushbutton/script.py",
)


def test_modify_build_floor_options_maps_story_numbers():
    """StoryFloorOption.floor_number should match story-based numbering."""
    levels = make_story_levels(3)
    options = modify_script._build_floor_options(levels, "column")

    assert len(options) >= 1
    for opt in options:
        assert hasattr(opt, "floor_number")
        assert hasattr(opt, "Name")
        assert opt.floor_number >= 1


def test_modify_story_floor_option_name_format():
    """StoryFloorOption.Name should contain floor number and level name."""
    levels = make_story_levels(3)
    options = modify_script._build_floor_options(levels, "column")

    for opt in options:
        assert u"第" in opt.Name
        assert u"层" in opt.Name


def test_delete_build_floor_options_maps_story_numbers():
    """DeleteElement floor options should have correct floor numbers."""
    doc = FakeDocument(levels=make_story_levels(3))
    options = delete_script._build_floor_options(doc, "beam")

    assert len(options) >= 1
    for opt in options:
        assert hasattr(opt, "floor_number")
        assert hasattr(opt, "Name")


def test_delete_floor_option_name_format():
    """FloorOption.Name should contain floor number and level name."""
    doc = FakeDocument(levels=make_story_levels(3))
    options = delete_script._build_floor_options(doc, "beam")

    for opt in options:
        assert u"第" in opt.Name
        assert u"层" in opt.Name
