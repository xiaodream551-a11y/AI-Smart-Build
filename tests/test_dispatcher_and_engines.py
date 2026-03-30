# -*- coding: utf-8 -*-
"""Tests for recognition/dispatcher and engine/wall, door, window modules."""

import importlib
import json
import types

import pytest

from tools.offline_runtime import (
    FakeDB, FakeXYZ, FakeLevel, FakeElementId, FakeParameter,
    FakeElement, FakeElementType, FakeBuiltInParameter,
)


# ──────────────────────────────────────────────
# Save/restore FakeDB to avoid polluting other test modules
# ──────────────────────────────────────────────

_saved_fakedb_attrs = {}


def _save_fakedb():
    for attr in ("Line", "Wall", "Grid", "FilteredElementCollector"):
        _saved_fakedb_attrs[attr] = getattr(FakeDB, attr, None)


def _restore_fakedb():
    for attr, value in _saved_fakedb_attrs.items():
        if value is not None:
            setattr(FakeDB, attr, value)


_save_fakedb()


@pytest.fixture(autouse=True, scope="module")
def _restore_fakedb_after_module():
    yield
    _restore_fakedb()


# ──────────────────────────────────────────────
# Stubs for wall / door / window engine tests
# ──────────────────────────────────────────────

class _FakeWall(object):
    """Stub wall returned by Wall.Create."""
    _counter = 0

    def __init__(self):
        _FakeWall._counter += 1
        self.Id = FakeElementId(_FakeWall._counter + 1000)
        self._params = {}

    def get_Parameter(self, bid):
        return self._params.get(bid)


class _FakeFamilyInstance(object):
    """Stub family instance returned by NewFamilyInstance."""
    _counter = 0

    def __init__(self):
        _FakeFamilyInstance._counter += 1
        self.Id = FakeElementId(_FakeFamilyInstance._counter + 2000)
        self._params = {}

    def get_Parameter(self, bid):
        return self._params.get(bid)


class _FakeSymbol(object):
    """Stub FamilySymbol for door/window types."""

    def __init__(self, name="Default", element_id=100):
        self.Id = FakeElementId(element_id)
        self.Name = name
        self.IsActive = True
        self._params = {}

    def Activate(self):
        self.IsActive = True

    def get_Parameter(self, bid):
        return self._params.get(bid)

    def LookupParameter(self, name):
        return self._params.get(name)


class _FakeWallType(object):
    """Stub WallType."""

    def __init__(self, name="Generic - 200mm", element_id=200, width_mm=200):
        self.Id = FakeElementId(element_id)
        self.Name = name
        width_ft = width_mm / 304.8
        self._params = {
            FakeBuiltInParameter.WALL_ATTR_WIDTH_PARAM: FakeParameter(width_ft),
        }

    def get_Parameter(self, bid):
        return self._params.get(bid)


def _install_wall_stubs(wall_records=None):
    """Install Line, Wall stubs on FakeDB; return reloaded wall module."""
    if wall_records is None:
        wall_records = []

    def fake_line_create_bound(start, end):
        return (start, end)

    class _WallStub:
        @staticmethod
        def Create(doc, line, wall_type_id, level_id, height, offset, flip, structural):
            wall = _FakeWall()
            wall_records.append({
                "line": line,
                "wall_type_id": wall_type_id,
                "level_id": level_id,
                "height": height,
                "structural": structural,
            })
            return wall

    FakeDB.Line = types.SimpleNamespace(CreateBound=fake_line_create_bound)
    FakeDB.Wall = _WallStub

    if "engine.wall" in importlib.sys.modules:
        del importlib.sys.modules["engine.wall"]
    import engine.wall
    return importlib.reload(engine.wall)


def _install_door_window_stubs():
    """Install NewFamilyInstance stub; return reloaded door and window modules.

    Saves and restores ``FakeDB.FilteredElementCollector`` to avoid
    polluting the global namespace for other test modules.
    """
    placement_records = []

    class _FakeCreator:
        def NewFamilyInstance(self, point, symbol, host, level, structural_type):
            inst = _FakeFamilyInstance()
            # Add sill height param (writable) for window tests
            inst._params[FakeBuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM] = \
                FakeParameter(0.0, read_only=False)
            placement_records.append({
                "point": point,
                "symbol": symbol,
                "host": host,
                "level": level,
            })
            return inst

    class _FakeDoc:
        def __init__(self):
            self.Create = _FakeCreator()
            self.wall_types = [_FakeWallType()]
            self.family_symbols = []
            self.elements = []
            self.levels = []

        def Regenerate(self):
            pass

        def GetElement(self, eid):
            return None

    # Install collector that can find wall types
    _original_collector = FakeDB.FilteredElementCollector

    class _EnhancedCollector:
        def __init__(self, doc):
            self.doc = doc
            self._items = []

        def OfClass(self, cls):
            if cls is FakeDB.WallType:
                self._items = list(getattr(self.doc, "wall_types", []))
            elif cls is FakeDB.FamilySymbol:
                self._items = list(getattr(self.doc, "family_symbols", []))
            return self

        def OfCategory(self, cat):
            self._items = [
                i for i in getattr(self.doc, "elements", [])
                if getattr(i, "category", None) == cat
            ]
            return self

        def __iter__(self):
            return iter(self._items)

    FakeDB.FilteredElementCollector = _EnhancedCollector

    for mod_name in ("engine.door", "engine.window"):
        if mod_name in importlib.sys.modules:
            del importlib.sys.modules[mod_name]
    import engine.door
    import engine.window
    engine.door = importlib.reload(engine.door)
    engine.window = importlib.reload(engine.window)

    # Restore original collector so other tests are not affected
    FakeDB.FilteredElementCollector = _original_collector

    return engine.door, engine.window, _FakeDoc, placement_records


# ──────────────────────────────────────────────
# Dispatcher tests (pure logic, no Revit stubs needed)
# ──────────────────────────────────────────────

from recognition.dispatcher import generate_build_plan, preview_build_plan, plan_to_json

SAMPLE_RECOGNITION = {
    "drawing_info": {"title": "一层平面图", "scale": "1:100", "floor": 1},
    "grids": {
        "x": [
            {"name": "1", "distance": 0},
            {"name": "2", "distance": 1500},
            {"name": "3", "distance": 3600},
            {"name": "4", "distance": 7800},
            {"name": "5", "distance": 11400},
        ],
        "y": [
            {"name": "A", "distance": 0},
            {"name": "B", "distance": 1500},
            {"name": "C", "distance": 6000},
            {"name": "D", "distance": 9300},
            {"name": "E", "distance": 9900},
        ],
    },
    "levels": [
        {"name": "1F", "elevation": 0.0},
        {"name": "2F", "elevation": 3.4},
        {"name": "屋面", "elevation": 6.953},
    ],
    "walls": [
        {"id": "W1", "start_x": 0, "start_y": 0, "end_x": 11400, "end_y": 0,
         "thickness": 240, "type": "exterior"},
        {"id": "W2", "start_x": 0, "start_y": 0, "end_x": 0, "end_y": 9900,
         "thickness": 240, "type": "exterior"},
        {"id": "W3", "start_x": 3600, "start_y": 0, "end_x": 3600, "end_y": 6000,
         "thickness": 240, "type": "interior"},
    ],
    "doors": [
        {"code": "M1527", "width": 1500, "height": 2700,
         "host_wall": "W1", "position_x": 4200, "position_y": 0},
    ],
    "windows": [
        {"code": "C0918", "width": 900, "height": 1800, "sill_height": 900,
         "host_wall": "W2", "position_x": 0, "position_y": 9300},
    ],
    "rooms": [
        {"name": "客厅", "floor": 1},
        {"name": "车库", "floor": 1},
    ],
}


class TestGenerateBuildPlan:
    def test_plan_has_correct_order(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        actions = [cmd["action"] for cmd in plan]
        # Grids first, then levels, then walls, then doors, then windows
        assert actions[0] == "create_grid_system"
        assert actions[1] == "create_levels"
        wall_actions = [a for a in actions if a == "create_wall"]
        assert len(wall_actions) == 3
        assert "place_door" in actions
        assert "place_window" in actions

    def test_plan_step_numbers_sequential(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        for i, cmd in enumerate(plan):
            assert cmd["step"] == i + 1

    def test_grid_params(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        grid_cmd = plan[0]
        assert grid_cmd["action"] == "create_grid_system"
        assert grid_cmd["params"]["x_coords_mm"] == [0, 1500, 3600, 7800, 11400]
        assert grid_cmd["params"]["x_labels"] == ["1", "2", "3", "4", "5"]
        assert grid_cmd["params"]["y_labels"] == ["A", "B", "C", "D", "E"]

    def test_level_params(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        level_cmd = plan[1]
        assert level_cmd["action"] == "create_levels"
        assert len(level_cmd["params"]["levels"]) == 3
        assert level_cmd["params"]["levels"][1]["elevation_m"] == 3.4

    def test_wall_params(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        wall_cmds = [c for c in plan if c["action"] == "create_wall"]
        w1 = wall_cmds[0]
        assert w1["params"]["start_x"] == 0
        assert w1["params"]["end_x"] == 11400
        assert w1["params"]["thickness"] == 240
        assert w1["params"]["wall_type"] == "exterior"

    def test_door_params(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        door_cmd = [c for c in plan if c["action"] == "place_door"][0]
        assert door_cmd["params"]["code"] == "M1527"
        assert door_cmd["params"]["width"] == 1500
        assert door_cmd["params"]["host_wall"] == "W1"

    def test_window_params(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        win_cmd = [c for c in plan if c["action"] == "place_window"][0]
        assert win_cmd["params"]["code"] == "C0918"
        assert win_cmd["params"]["sill_height"] == 900

    def test_total_steps(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        # 1 grid + 1 level + 3 walls + 1 door + 1 window = 7
        assert len(plan) == 7

    def test_empty_input(self):
        plan = generate_build_plan({})
        assert plan == []

    def test_grids_only(self):
        data = {"grids": SAMPLE_RECOGNITION["grids"]}
        plan = generate_build_plan(data)
        assert len(plan) == 1
        assert plan[0]["action"] == "create_grid_system"


class TestPreviewBuildPlan:
    def test_preview_not_empty(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        preview = preview_build_plan(plan)
        assert u"建模计划" in preview
        assert u"7 步" in preview

    def test_preview_has_descriptions(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        preview = preview_build_plan(plan)
        assert u"轴网" in preview
        assert u"标高" in preview
        assert u"外墙" in preview
        assert u"门" in preview
        assert u"窗" in preview

    def test_preview_empty_plan(self):
        preview = preview_build_plan([])
        assert u"空计划" in preview


class TestPlanToJson:
    def test_serializable(self):
        plan = generate_build_plan(SAMPLE_RECOGNITION)
        json_str = plan_to_json(plan)
        parsed = json.loads(json_str)
        assert len(parsed) == 7


# ──────────────────────────────────────────────
# Wall engine tests
# ──────────────────────────────────────────────

class TestCreateWall:
    def test_create_wall_basic(self):
        records = []
        wall_mod = _install_wall_stubs(records)
        level = FakeLevel("1F", 0.0, 1)
        wt = _FakeWallType("240mm", 200, 240)

        wall = wall_mod.create_wall(
            None, 0, 0, 11400, 0, level, height_mm=3000, wall_type=wt,
        )
        assert wall is not None
        assert len(records) == 1
        assert records[0]["height"] == pytest.approx(3000 / 304.8, abs=0.01)

    def test_create_wall_none_level_raises(self):
        wall_mod = _install_wall_stubs()
        with pytest.raises(ValueError, match=u"标高"):
            wall_mod.create_wall(None, 0, 0, 100, 0, level=None)

    def test_create_walls_from_list(self):
        records = []
        wall_mod = _install_wall_stubs(records)
        level = FakeLevel("1F", 0.0, 1)
        wt = _FakeWallType()
        walls_data = [
            {"id": "W1", "start_x": 0, "start_y": 0, "end_x": 11400, "end_y": 0},
            {"id": "W2", "start_x": 0, "start_y": 0, "end_x": 0, "end_y": 9900},
        ]
        results = wall_mod.create_walls_from_list(None, walls_data, level, wall_type=wt)
        assert len(results) == 2
        assert results[0][0] == "W1"
        assert results[1][0] == "W2"


# ──────────────────────────────────────────────
# Door engine tests
# ──────────────────────────────────────────────

class TestPlaceDoor:
    def test_place_door_basic(self):
        door_mod, _, FakeDoc, records = _install_door_window_stubs()
        doc = FakeDoc()
        level = FakeLevel("1F", 0.0, 1)
        host_wall = _FakeWall()
        door_type = _FakeSymbol("SingleDoor")

        door = door_mod.place_door(doc, host_wall, 4200, 0, level, door_type=door_type)
        assert door is not None
        assert len(records) == 1
        assert records[0]["host"] is host_wall

    def test_place_door_none_wall_raises(self):
        door_mod, _, FakeDoc, _ = _install_door_window_stubs()
        doc = FakeDoc()
        level = FakeLevel("1F", 0.0, 1)
        with pytest.raises(ValueError, match=u"墙"):
            door_mod.place_door(doc, None, 0, 0, level)

    def test_place_door_none_level_raises(self):
        door_mod, _, FakeDoc, _ = _install_door_window_stubs()
        doc = FakeDoc()
        host_wall = _FakeWall()
        with pytest.raises(ValueError, match=u"标高"):
            door_mod.place_door(doc, host_wall, 0, 0, None)


# ──────────────────────────────────────────────
# Window engine tests
# ──────────────────────────────────────────────

class TestPlaceWindow:
    def test_place_window_basic(self):
        _, win_mod, FakeDoc, records = _install_door_window_stubs()
        doc = FakeDoc()
        level = FakeLevel("1F", 0.0, 1)
        host_wall = _FakeWall()
        win_type = _FakeSymbol("FixedWindow")

        window = win_mod.place_window(
            doc, host_wall, 0, 9300, level,
            sill_height_mm=900, window_type=win_type,
        )
        assert window is not None
        assert len(records) == 1

    def test_place_window_none_wall_raises(self):
        _, win_mod, FakeDoc, _ = _install_door_window_stubs()
        doc = FakeDoc()
        level = FakeLevel("1F", 0.0, 1)
        with pytest.raises(ValueError, match=u"墙"):
            win_mod.place_window(doc, None, 0, 0, level)

    def test_place_window_sill_height(self):
        _, win_mod, FakeDoc, records = _install_door_window_stubs()
        doc = FakeDoc()
        level = FakeLevel("1F", 0.0, 1)
        host_wall = _FakeWall()
        win_type = _FakeSymbol("Window")

        win_mod.place_window(
            doc, host_wall, 0, 0, level,
            sill_height_mm=1200, window_type=win_type,
        )
        assert len(records) == 1
