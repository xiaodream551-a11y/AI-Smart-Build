# -*- coding: utf-8 -*-
"""Tests for recognition.executor — build-plan execution."""

from unittest import mock

import pytest

from recognition.executor import execute_build_plan, format_result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class FakeLevel:
    def __init__(self, name="F1"):
        self.Name = name


class FakeWall:
    def __init__(self, wall_id="W1"):
        self._id = wall_id


class FakeDoor:
    pass


class FakeWindow:
    pass


@pytest.fixture
def base_level():
    return FakeLevel("base")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _grid_cmd(x_coords, y_coords, x_labels=None, y_labels=None):
    params = {"x_coords_mm": x_coords, "y_coords_mm": y_coords}
    if x_labels:
        params["x_labels"] = x_labels
    if y_labels:
        params["y_labels"] = y_labels
    return {"step": 1, "action": "create_grid_system", "params": params,
            "description": "grids"}


def _levels_cmd(levels):
    return {"step": 2, "action": "create_levels",
            "params": {"levels": levels}, "description": "levels"}


def _wall_cmd(wall_id, sx, sy, ex, ey):
    return {"step": 3, "action": "create_wall",
            "params": {"id": wall_id, "start_x": sx, "start_y": sy,
                       "end_x": ex, "end_y": ey},
            "description": "wall " + wall_id}


def _door_cmd(code, host_wall, px, py):
    return {"step": 4, "action": "place_door",
            "params": {"code": code, "host_wall": host_wall,
                       "position_x": px, "position_y": py},
            "description": "door " + code}


def _window_cmd(code, host_wall, px, py, sill=900):
    return {"step": 5, "action": "place_window",
            "params": {"code": code, "host_wall": host_wall,
                       "position_x": px, "position_y": py,
                       "sill_height": sill},
            "description": "window " + code}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExecuteEmptyPlan:
    def test_empty_plan_returns_zeros(self, base_level):
        result = execute_build_plan(None, [], base_level)
        assert result["grids"] == 0
        assert result["walls"] == 0
        assert result["errors"] == []


class TestGridCreation:
    @mock.patch("engine.grid.create_grid_system")
    def test_creates_grids(self, mock_cgs, base_level):
        mock_cgs.return_value = (["g1", "g2"], ["gA"])
        plan = [_grid_cmd([0, 6000], [0], x_labels=["1", "2"], y_labels=["A"])]

        result = execute_build_plan(None, plan, base_level)

        mock_cgs.assert_called_once()
        assert result["grids"] == 3


class TestLevelCreation:
    @mock.patch("engine.level.create_level")
    def test_creates_levels(self, mock_cl, base_level):
        mock_cl.return_value = FakeLevel("F1")
        plan = [_levels_cmd([
            {"name": "F1", "elevation_m": 0},
            {"name": "F2", "elevation_m": 3.3},
        ])]

        result = execute_build_plan(None, plan, base_level)

        assert mock_cl.call_count == 2
        # elevation_m * 1000 = mm
        _, call2 = mock_cl.call_args_list
        assert call2[0][2] == 3300.0  # 3.3 * 1000
        assert result["levels"] == 2


class TestWallCreation:
    @mock.patch("engine.wall.create_wall")
    def test_creates_wall_and_tracks_id(self, mock_cw, base_level):
        fake_wall = FakeWall("W1")
        mock_cw.return_value = fake_wall
        plan = [_wall_cmd("W1", 0, 0, 6000, 0)]

        result = execute_build_plan(None, plan, base_level)

        mock_cw.assert_called_once()
        assert result["walls"] == 1

    @mock.patch("engine.wall.create_wall")
    def test_skips_wall_without_level(self, mock_cw):
        plan = [_wall_cmd("W1", 0, 0, 6000, 0)]

        result = execute_build_plan(None, plan, base_level=None)

        mock_cw.assert_not_called()
        assert result["walls"] == 0
        assert len(result["errors"]) == 1
        assert u"无可用标高" in result["errors"][0]

    @mock.patch("engine.level.create_level")
    @mock.patch("engine.wall.create_wall")
    def test_uses_created_level_for_walls(self, mock_cw, mock_cl):
        created_lv = FakeLevel("F1")
        mock_cl.return_value = created_lv
        mock_cw.return_value = FakeWall()

        plan = [
            _levels_cmd([{"name": "F1", "elevation_m": 0}]),
            _wall_cmd("W1", 0, 0, 6000, 0),
        ]
        result = execute_build_plan(None, plan, base_level=None)

        # Wall should use created level, not base_level (which is None)
        assert mock_cw.call_args[1]["level"] is created_lv
        assert result["walls"] == 1
        assert result["errors"] == []


class TestDoorPlacement:
    @mock.patch("engine.door.place_door")
    @mock.patch("engine.wall.create_wall")
    def test_places_door_on_host_wall(self, mock_cw, mock_pd, base_level):
        fake_wall = FakeWall("W1")
        mock_cw.return_value = fake_wall
        plan = [
            _wall_cmd("W1", 0, 0, 6000, 0),
            _door_cmd("D1", "W1", 3000, 0),
        ]

        result = execute_build_plan(None, plan, base_level)

        mock_pd.assert_called_once()
        assert mock_pd.call_args[0][1] is fake_wall  # host_wall arg
        assert result["doors"] == 1

    @mock.patch("engine.wall.create_wall")
    def test_error_when_host_wall_missing(self, mock_cw, base_level):
        mock_cw.return_value = FakeWall("W1")
        plan = [
            _wall_cmd("W1", 0, 0, 6000, 0),
            _door_cmd("D1", "W99", 3000, 0),  # W99 doesn't exist
        ]

        result = execute_build_plan(None, plan, base_level)

        assert result["doors"] == 0
        assert len(result["errors"]) == 1
        assert "W99" in result["errors"][0]


class TestWindowPlacement:
    @mock.patch("engine.window.place_window")
    @mock.patch("engine.wall.create_wall")
    def test_places_window_with_sill_height(self, mock_cw, mock_pw, base_level):
        fake_wall = FakeWall("W2")
        mock_cw.return_value = fake_wall
        plan = [
            _wall_cmd("W2", 0, 0, 0, 6000),
            _window_cmd("C1", "W2", 0, 3000, sill=1200),
        ]

        result = execute_build_plan(None, plan, base_level)

        mock_pw.assert_called_once()
        assert mock_pw.call_args[1]["sill_height_mm"] == 1200
        assert result["windows"] == 1


class TestUnknownAction:
    def test_unknown_action_logs_error(self, base_level):
        plan = [{"step": 1, "action": "fly_to_moon", "params": {},
                 "description": "nope"}]

        result = execute_build_plan(None, plan, base_level)
        assert len(result["errors"]) == 1
        assert "fly_to_moon" in result["errors"][0]


class TestExceptionHandling:
    @mock.patch("engine.grid.create_grid_system", side_effect=RuntimeError("boom"))
    def test_exception_captured_as_error(self, mock_cgs, base_level):
        plan = [_grid_cmd([0], [0])]

        result = execute_build_plan(None, plan, base_level)

        assert result["grids"] == 0
        assert len(result["errors"]) == 1
        assert "boom" in result["errors"][0]


class TestProgressCallback:
    @mock.patch("engine.grid.create_grid_system", return_value=([], []))
    def test_callback_called_for_each_step(self, mock_cgs, base_level):
        calls = []
        plan = [_grid_cmd([0], [0])]

        execute_build_plan(None, plan, base_level,
                           progress_callback=lambda s, t, d: calls.append((s, t, d)))

        assert calls == [(1, 1, "grids")]


class TestFormatResult:
    def test_format_success(self):
        result = {"grids": 5, "levels": 2, "walls": 8, "doors": 3,
                  "windows": 4, "errors": []}
        text = format_result(result)
        assert u"22" in text  # total = 5+2+8+3+4
        assert u"轴网" in text
        assert u"警告" not in text

    def test_format_with_errors(self):
        result = {"grids": 0, "levels": 0, "walls": 0, "doors": 0,
                  "windows": 0, "errors": [u"测试错误"]}
        text = format_result(result)
        assert u"警告" in text
        assert u"测试错误" in text


class TestFullPipeline:
    """End-to-end test with all action types."""

    @mock.patch("engine.window.place_window", return_value=FakeWindow())
    @mock.patch("engine.door.place_door", return_value=FakeDoor())
    @mock.patch("engine.wall.create_wall")
    @mock.patch("engine.level.create_level")
    @mock.patch("engine.grid.create_grid_system")
    def test_full_plan_execution(self, mock_cgs, mock_cl, mock_cw,
                                  mock_pd, mock_pw, base_level):
        mock_cgs.return_value = (["g1", "g2"], ["gA", "gB"])
        mock_cl.return_value = FakeLevel("F1")
        wall1 = FakeWall("W1")
        wall2 = FakeWall("W2")
        mock_cw.side_effect = [wall1, wall2]

        plan = [
            _grid_cmd([0, 6000], [0, 6000]),
            _levels_cmd([{"name": "F1", "elevation_m": 0}]),
            _wall_cmd("W1", 0, 0, 6000, 0),
            _wall_cmd("W2", 0, 0, 0, 6000),
            _door_cmd("D1", "W1", 3000, 0),
            _window_cmd("C1", "W2", 0, 3000),
        ]

        result = execute_build_plan(None, plan, base_level)

        assert result == {
            "grids": 4, "levels": 1, "walls": 2,
            "doors": 1, "windows": 1, "errors": [],
        }
