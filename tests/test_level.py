# -*- coding: utf-8 -*-
"""Tests for engine.level -- offline validation and parameter checks."""

import types
import sys

import pytest

from tools.offline_runtime import (
    FakeDB,
    FakeLevel,
    FakeFilteredElementCollector,
    FakeDocument,
    bootstrap,
)


def _mm_to_feet(value_mm):
    return float(value_mm) / 304.8


def _make_fake_level_module(monkeypatch, doc):
    """Reload engine.level with a fresh DB.Level.Create stub that records calls."""
    records = {"created": []}

    class StubLevel(object):
        def __init__(self, name, elevation, element_id):
            self.Name = name
            self.Elevation = elevation
            self.Id = FakeDB.ElementId(element_id)

        @staticmethod
        def Create(doc, elevation_feet):
            level = StubLevel("", elevation_feet, 9000 + len(records["created"]))
            records["created"].append(level)
            return level

    monkeypatch.setattr(FakeDB, "Level", StubLevel)

    import importlib
    from engine import level as level_module
    importlib.reload(level_module)

    return level_module, records


def test_create_level_converts_mm_to_feet(monkeypatch):
    """create_level should convert the elevation from mm to feet."""
    doc = FakeDocument(levels=[], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    result = level_module.create_level(doc, "F1", 3600)

    assert len(records["created"]) == 1
    assert result.Name == "F1"
    expected_feet = _mm_to_feet(3600)
    assert abs(result.Elevation - expected_feet) < 1e-6


def test_create_level_returns_existing_by_name(monkeypatch):
    """If a level with the same name already exists, return it without creating a new one."""
    existing_level = FakeLevel("F1", _mm_to_feet(3600), 100)
    doc = FakeDocument(levels=[existing_level], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    result = level_module.create_level(doc, "F1", 3600)

    assert result is existing_level
    assert len(records["created"]) == 0


def test_create_level_returns_existing_by_elevation(monkeypatch):
    """If a level at the same elevation already exists, return it."""
    elevation_mm = 7200
    existing_level = FakeLevel("SomeLevel", _mm_to_feet(elevation_mm), 200)
    doc = FakeDocument(levels=[existing_level], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    result = level_module.create_level(doc, "F2", elevation_mm)

    assert result is existing_level
    assert len(records["created"]) == 0


def test_create_level_creates_new_when_no_match(monkeypatch):
    """When neither name nor elevation matches, a new level should be created."""
    existing_level = FakeLevel("F1", _mm_to_feet(3600), 100)
    doc = FakeDocument(levels=[existing_level], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    result = level_module.create_level(doc, "F2", 7200)

    assert len(records["created"]) == 1
    assert result.Name == "F2"


def test_create_level_system_produces_correct_count(monkeypatch):
    """create_level_system should produce num_floors + 1 levels (base + stories + roof)."""
    doc = FakeDocument(levels=[], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    levels = level_module.create_level_system(doc, num_floors=3, floor_height_mm=3600)

    # Base + F1 + F2 + F3 (roof) = 4 levels
    assert len(levels) == 4


def test_create_level_system_uses_first_floor_height(monkeypatch):
    """When first_floor_height_mm is provided, the first floor should use it."""
    doc = FakeDocument(levels=[], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    levels = level_module.create_level_system(
        doc, num_floors=3, floor_height_mm=3600, first_floor_height_mm=4200
    )

    # Check elevations: base=0, F1=4200, F2=4200+3600=7800, roof=7800+3600=11400
    elevations_mm = [0, 4200, 7800, 11400]
    for i, expected_mm in enumerate(elevations_mm):
        expected_feet = _mm_to_feet(expected_mm)
        assert abs(levels[i].Elevation - expected_feet) < 1e-6


def test_create_level_system_defaults_first_floor_to_standard(monkeypatch):
    """When first_floor_height_mm is None, all floors use the standard height."""
    doc = FakeDocument(levels=[], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    levels = level_module.create_level_system(
        doc, num_floors=2, floor_height_mm=3600
    )

    # Base=0, F1=3600, roof=7200
    elevations_mm = [0, 3600, 7200]
    for i, expected_mm in enumerate(elevations_mm):
        expected_feet = _mm_to_feet(expected_mm)
        assert abs(levels[i].Elevation - expected_feet) < 1e-6


def test_create_level_system_naming_convention(monkeypatch):
    """Level names should follow project convention: base, F1..FN-1, roof."""
    doc = FakeDocument(levels=[], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    levels = level_module.create_level_system(
        doc, num_floors=3, floor_height_mm=3000
    )

    names = [lvl.Name for lvl in levels]
    assert names[0] == u"\u00b10.000"  # +-0.000
    assert names[1] == "F1"
    assert names[2] == "F2"
    assert names[-1] == u"屋面"        # Roof


def test_create_level_system_with_base_elevation(monkeypatch):
    """A non-zero base_elevation_mm should shift all levels up."""
    doc = FakeDocument(levels=[], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    levels = level_module.create_level_system(
        doc, num_floors=2, floor_height_mm=3600, base_elevation_mm=1000
    )

    # Base=1000, F1=4600, roof=8200
    elevations_mm = [1000, 4600, 8200]
    for i, expected_mm in enumerate(elevations_mm):
        expected_feet = _mm_to_feet(expected_mm)
        assert abs(levels[i].Elevation - expected_feet) < 1e-6


def test_create_level_system_single_floor(monkeypatch):
    """A single-floor system should produce base + roof = 2 levels."""
    doc = FakeDocument(levels=[], elements=[])
    level_module, records = _make_fake_level_module(monkeypatch, doc)

    levels = level_module.create_level_system(
        doc, num_floors=1, floor_height_mm=3600
    )

    assert len(levels) == 2
    assert levels[0].Name == u"\u00b10.000"
    assert levels[-1].Name == u"屋面"
