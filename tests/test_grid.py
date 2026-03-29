# -*- coding: utf-8 -*-
"""Tests for engine.grid -- offline validation and parameter checks."""

import importlib
import types

import pytest

from tools.offline_runtime import FakeDB, FakeXYZ, bootstrap


def _mm_to_feet(value_mm):
    return float(value_mm) / 304.8


class _FakeGridObject(object):
    """Stub grid returned by FakeDB.Grid.Create."""

    def __init__(self):
        self.Name = None


def _install_grid_stubs(records=None, created_grids=None):
    """Add Line and Grid stubs to FakeDB; return the reloaded grid module."""
    if records is None:
        records = {}
    if created_grids is None:
        created_grids = []

    def fake_line_create_bound(start, end):
        records.setdefault("starts", []).append(start)
        records.setdefault("ends", []).append(end)
        return (start, end)

    class _GridStub(object):
        def __init__(self):
            self.Name = None

        @staticmethod
        def Create(doc, line):
            grid = _GridStub()
            grid._line = line
            records["doc"] = doc
            created_grids.append(grid)
            return grid

    FakeDB.Line = types.SimpleNamespace(CreateBound=fake_line_create_bound)
    FakeDB.Grid = _GridStub

    from engine import grid as grid_module
    importlib.reload(grid_module)
    return grid_module


def test_create_grid_converts_mm_to_feet_and_sets_name():
    """create_grid should convert mm coordinates to feet and assign the grid name."""
    records = {}
    created = []
    grid_module = _install_grid_stubs(records, created)

    result = grid_module.create_grid("mock-doc", "A", 0, 0, 6000, 0)

    assert records["doc"] == "mock-doc"
    assert result.Name == "A"
    assert abs(records["starts"][0].X - _mm_to_feet(0)) < 1e-6
    assert abs(records["ends"][0].X - _mm_to_feet(6000)) < 1e-6


def test_create_grid_system_generates_correct_number_of_grids():
    """create_grid_system should create one grid per X coord and one per Y coord."""
    created = []
    grid_module = _install_grid_stubs(created_grids=created)

    x_coords = [0, 6000, 12000]
    y_coords = [0, 8000]

    x_grids, y_grids = grid_module.create_grid_system(
        "mock-doc", x_coords, y_coords
    )

    assert len(x_grids) == 3
    assert len(y_grids) == 2
    assert len(created) == 5


def test_create_grid_system_uses_default_labels():
    """create_grid_system should auto-label X grids as 1,2,3 and Y grids as A,B."""
    grid_module = _install_grid_stubs()

    x_grids, y_grids = grid_module.create_grid_system(
        "mock-doc", [0, 6000, 12000], [0, 8000]
    )

    assert [g.Name for g in x_grids] == ["1", "2", "3"]
    assert [g.Name for g in y_grids] == ["A", "B"]


def test_create_grid_system_uses_custom_labels():
    """create_grid_system should use caller-provided labels when supplied."""
    grid_module = _install_grid_stubs()

    x_grids, y_grids = grid_module.create_grid_system(
        "mock-doc",
        [0, 6000],
        [0, 8000, 16000],
        x_labels=["X1", "X2"],
        y_labels=["YA", "YB", "YC"],
    )

    assert [g.Name for g in x_grids] == ["X1", "X2"]
    assert [g.Name for g in y_grids] == ["YA", "YB", "YC"]


def test_create_grid_system_extension_mm_extends_grid_lines():
    """Grid lines should extend beyond the outermost coordinates by extension_mm."""
    records = {}
    grid_module = _install_grid_stubs(records)

    x_coords = [0, 6000]
    y_coords = [0, 8000]
    extension = 2000

    grid_module.create_grid_system(
        "mock-doc", x_coords, y_coords, extension_mm=extension
    )

    starts = records["starts"]
    ends = records["ends"]

    # The first X-direction grid (vertical line at x=0) should span from
    # y_min - extension to y_max + extension
    expected_y_min = _mm_to_feet(0 - extension)
    expected_y_max = _mm_to_feet(8000 + extension)
    assert abs(starts[0].Y - expected_y_min) < 1e-6
    assert abs(ends[0].Y - expected_y_max) < 1e-6

    # The first Y-direction grid (horizontal line at y=0) should span from
    # x_min - extension to x_max + extension
    first_y_start = starts[2]  # After 2 X grids
    first_y_end = ends[2]
    expected_x_min = _mm_to_feet(0 - extension)
    expected_x_max = _mm_to_feet(6000 + extension)
    assert abs(first_y_start.X - expected_x_min) < 1e-6
    assert abs(first_y_end.X - expected_x_max) < 1e-6


def test_create_grid_system_falls_back_to_numeric_label_when_labels_short():
    """When x_labels is shorter than x_coords, the remainder should get auto-numbered labels."""
    grid_module = _install_grid_stubs()

    x_grids, y_grids = grid_module.create_grid_system(
        "mock-doc",
        [0, 6000, 12000],
        [0],
        x_labels=["X"],  # Only 1 label for 3 coords
        y_labels=[],       # Empty labels for 1 coord
    )

    assert x_grids[0].Name == "X"
    assert x_grids[1].Name == "2"  # Falls back to str(i+1)
    assert x_grids[2].Name == "3"
    assert y_grids[0].Name == "A"  # Falls back to chr(65+i)
