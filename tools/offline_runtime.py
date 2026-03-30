# -*- coding: utf-8 -*-
"""Offline debug helper: import pyRevit-related modules outside the Revit environment."""

import importlib.util
import sys
import types
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LIB_DIR = ROOT_DIR / "AISmartBuild.extension" / "lib"


class FakeElementId(object):
    """Simplified ElementId stub."""

    def __init__(self, value):
        self.IntegerValue = int(value)


class FakeStorageType(object):
    """Simplified StorageType enum stub."""

    ElementId = "ElementId"
    Double = "Double"


class FakeBuiltInCategory(object):
    """Simplified BuiltInCategory enum stub."""

    OST_StructuralColumns = 1
    OST_StructuralFraming = 2
    OST_Floors = 3
    OST_Walls = 4
    OST_Doors = 5
    OST_Windows = 6


class FakeBuiltInParameter(object):
    """Simplified BuiltInParameter enum stub."""

    FAMILY_BASE_LEVEL_PARAM = "FAMILY_BASE_LEVEL_PARAM"
    FAMILY_TOP_LEVEL_PARAM = "FAMILY_TOP_LEVEL_PARAM"
    FAMILY_TOP_LEVEL_OFFSET_PARAM = "FAMILY_TOP_LEVEL_OFFSET_PARAM"
    FAMILY_BASE_LEVEL_OFFSET_PARAM = "FAMILY_BASE_LEVEL_OFFSET_PARAM"
    INSTANCE_REFERENCE_LEVEL_PARAM = "INSTANCE_REFERENCE_LEVEL_PARAM"
    SCHEDULE_LEVEL_PARAM = "SCHEDULE_LEVEL_PARAM"
    LEVEL_PARAM = "LEVEL_PARAM"
    FLOOR_HEIGHTABOVELEVEL_PARAM = "FLOOR_HEIGHTABOVELEVEL_PARAM"
    Z_OFFSET_VALUE = "Z_OFFSET_VALUE"
    HOST_AREA_COMPUTED = "HOST_AREA_COMPUTED"
    WALL_ATTR_WIDTH_PARAM = "WALL_ATTR_WIDTH_PARAM"
    INSTANCE_SILL_HEIGHT_PARAM = "INSTANCE_SILL_HEIGHT_PARAM"


class FakeCategory(object):
    """Simplified Category stub."""

    def __init__(self, builtin, name=None):
        self.Id = FakeElementId(int(builtin))
        self.Name = name or str(builtin)


class FakeLevel(object):
    """Simplified Level stub."""

    _counter = 9000

    def __init__(self, name, elevation, element_id):
        self.Name = name
        self.Elevation = elevation
        self.Id = FakeElementId(element_id)

    @staticmethod
    def Create(doc, elevation_feet):
        FakeLevel._counter += 1
        return FakeLevel("", elevation_feet, FakeLevel._counter)


class FakeParameter(object):
    """Simplified Parameter stub."""

    def __init__(self, value=None, storage_type=None, read_only=False):
        self._value = value
        self.StorageType = storage_type
        self.IsReadOnly = read_only

    def AsElementId(self):
        return self._value

    def AsDouble(self):
        return float(self._value)

    def AsString(self):
        if self._value is None:
            return None
        return "{}".format(self._value)

    def Set(self, value):
        self._value = value


class FakeXYZ(object):
    """Simplified XYZ stub."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.X = float(x)
        self.Y = float(y)
        self.Z = float(z)


class FakeCurve(object):
    """Simplified Curve stub."""

    def __init__(self, start, end):
        self._points = [start, end]

    def GetEndPoint(self, index):
        return self._points[index]


class FakeLine(object):
    """Simplified Line stub with CreateBound factory."""

    def __init__(self, start, end):
        self._start = start
        self._end = end

    def GetEndPoint(self, index):
        return [self._start, self._end][index]

    @staticmethod
    def CreateBound(start, end):
        return FakeLine(start, end)


class FakeGrid(object):
    """Simplified Grid stub."""

    _counter = 8000

    def __init__(self):
        self.Name = None
        FakeGrid._counter += 1
        self.Id = FakeElementId(FakeGrid._counter)

    @staticmethod
    def Create(doc, line):
        return FakeGrid()


class FakeWall(object):
    """Simplified Wall stub."""

    _counter = 7000

    def __init__(self):
        FakeWall._counter += 1
        self.Id = FakeElementId(FakeWall._counter)
        self._params = {}

    def get_Parameter(self, bid):
        return self._params.get(bid)

    @staticmethod
    def Create(doc, line, wall_type_id, level_id, height, offset, flip, structural):
        return FakeWall()


class FakePointLocation(object):
    """Simplified point location stub."""

    def __init__(self, point):
        self.Point = point


class FakeCurveLocation(object):
    """Simplified curve location stub."""

    def __init__(self, curve):
        self.Curve = curve


class FakeElementType(object):
    """Simplified family type stub."""

    def __init__(self, element_id, name="", lookup_params=None):
        self.Id = FakeElementId(element_id)
        self.Name = name
        self._lookup_params = dict(lookup_params or {})
        self.Document = None

    def LookupParameter(self, name):
        return self._lookup_params.get(name)


class FakeElement(object):
    """Simplified model element stub."""

    def __init__(
        self,
        element_id,
        category,
        level_id=None,
        params=None,
        lookup_params=None,
        name=None,
        location=None,
        symbol=None,
        type_id=None,
        area=None,
    ):
        self.Id = FakeElementId(element_id)
        self.category = category
        self.Category = FakeCategory(category, name=name)
        self.LevelId = FakeElementId(level_id) if level_id is not None else None
        self._params = dict(params or {})
        self._lookup_params = dict(lookup_params or {})
        self.Location = location
        self.Symbol = symbol
        self._type_id = FakeElementId(type_id) if type_id is not None else None
        self.Area = area
        self.Document = None

    def get_Parameter(self, builtin):
        return self._params.get(builtin)

    def LookupParameter(self, name):
        return self._lookup_params.get(name)

    def GetTypeId(self):
        return self._type_id


class FakeDocument(object):
    """Simplified Revit Document stub."""

    def __init__(self, levels=None, elements=None, element_types=None):
        self.levels = list(levels or [])
        self.elements = list(elements or [])
        self.element_types = list(element_types or [])
        self._by_id = {}

        for level in self.levels:
            self._by_id[level.Id.IntegerValue] = level
        for element in self.elements:
            self._by_id[element.Id.IntegerValue] = element
            element.Document = self
        for element_type in self.element_types:
            self._by_id[element_type.Id.IntegerValue] = element_type
            element_type.Document = self

    def GetElement(self, element_id):
        value = getattr(element_id, "IntegerValue", element_id)
        return self._by_id.get(value)


class FakeFilteredElementCollector(object):
    """Simplified FilteredElementCollector stub."""

    def __init__(self, doc):
        self.doc = doc
        self._items = list(getattr(doc, "elements", []))

    def OfClass(self, cls):
        if cls is FakeDB.Level:
            self._items = list(getattr(self.doc, "levels", []))
        elif cls is getattr(FakeDB, "FamilySymbol", object):
            self._items = list(getattr(self.doc, "family_symbols", []))
        elif cls is getattr(FakeDB, "FloorType", object):
            self._items = list(getattr(self.doc, "floor_types", []))
        return self

    def OfCategory(self, category):
        self._items = [
            item for item in getattr(self.doc, "elements", [])
            if getattr(item, "category", None) == category
        ]
        return self

    def WhereElementIsNotElementType(self):
        return self

    def __iter__(self):
        return iter(self._items)

    def GetElementCount(self):
        return len(self._items)


class _FakeStructure(object):
    StructuralType = types.SimpleNamespace(
        Column="Column", Beam="Beam", NonStructural="NonStructural",
    )


class _FakeOutput(object):
    def print_md(self, _text):
        return None


class _FakeLogger(object):
    def warning(self, _text):
        return None

    def exception(self, _err):
        return None


class _NullTransaction(object):
    def __init__(self, _name=None):
        self.name = _name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeWPFWindow(object):
    def __init__(self, *_args, **_kwargs):
        return None

    def ShowDialog(self):
        return None

    def Close(self):
        return None


FakeDB = types.SimpleNamespace(
    ElementId=FakeElementId,
    StorageType=FakeStorageType,
    BuiltInCategory=FakeBuiltInCategory,
    BuiltInParameter=FakeBuiltInParameter,
    Level=FakeLevel,
    Line=FakeLine,
    Grid=FakeGrid,
    Wall=FakeWall,
    FilteredElementCollector=FakeFilteredElementCollector,
    FamilySymbol=type("FamilySymbol", (), {}),
    FloorType=type("FloorType", (), {}),
    WallType=type("WallType", (), {}),
    Structure=_FakeStructure(),
    XYZ=FakeXYZ,
)


class _FakeGenericListFactory(object):
    def __getitem__(self, _item):
        class _FakeList(list):
            def Add(self, value):
                self.append(value)

        return _FakeList


def ensure_lib_path():
    """Add the project root and lib directories to sys.path."""
    root = str(ROOT_DIR)
    lib = str(LIB_DIR)

    if root not in sys.path:
        sys.path.insert(0, root)
    if lib not in sys.path:
        sys.path.insert(0, lib)

    return LIB_DIR


def install_clr_stub():
    """Install minimal clr/System stubs."""
    if "clr" not in sys.modules:
        clr_module = types.ModuleType("clr")
        clr_module.AddReference = lambda _name: None
        sys.modules["clr"] = clr_module

    if "System" not in sys.modules:
        system_module = types.ModuleType("System")
        sys.modules["System"] = system_module
    else:
        system_module = sys.modules["System"]

    collections_module = types.ModuleType("System.Collections")
    generic_module = types.ModuleType("System.Collections.Generic")
    generic_module.List = _FakeGenericListFactory()
    collections_module.Generic = generic_module
    system_module.Collections = collections_module

    sys.modules["System.Collections"] = collections_module
    sys.modules["System.Collections.Generic"] = generic_module


def install_pyrevit_stub():
    """Install minimal pyrevit stubs."""
    if "pyrevit" in sys.modules:
        return sys.modules["pyrevit"]
    pyrevit_module = types.ModuleType("pyrevit")
    pyrevit_module.__path__ = []
    pyrevit_module.DB = FakeDB
    pyrevit_module.revit = types.SimpleNamespace(doc=None, Transaction=_NullTransaction)
    pyrevit_module.forms = types.SimpleNamespace(
        WPFWindow=_FakeWPFWindow,
        ask_for_string=lambda *args, **kwargs: None,
        pick_file=lambda *args, **kwargs: None,
        save_file=lambda *args, **kwargs: None,
        alert=lambda *args, **kwargs: None,
        ProgressBar=_NullTransaction,
        SelectFromList=types.SimpleNamespace(show=lambda *args, **kwargs: None),
    )
    pyrevit_module.script = types.SimpleNamespace(
        get_output=lambda: _FakeOutput(),
        get_logger=lambda: _FakeLogger(),
        exit=lambda: None,
    )
    versionmgr_module = types.ModuleType("pyrevit.versionmgr")
    versionmgr_module.get_pyrevit_version = lambda: "unknown"
    pyrevit_module.versionmgr = versionmgr_module

    sys.modules["pyrevit"] = pyrevit_module
    sys.modules["pyrevit.versionmgr"] = versionmgr_module
    return pyrevit_module


def make_story_levels(story_count):
    """Generate a set of story levels following project conventions."""
    levels = [FakeLevel("±0.000", 0.0, 1)]

    for index in range(1, story_count):
        levels.append(FakeLevel("F{}".format(index), float(index), index + 1))

    levels.append(FakeLevel("屋面", float(story_count), story_count + 1))
    return levels


def load_module_from_path(module_name, relative_path):
    """Load a Python file from the project by relative path."""
    file_path = ROOT_DIR / relative_path
    if module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bootstrap():
    """Perform one-time offline import preparation."""
    ensure_lib_path()
    install_clr_stub()
    install_pyrevit_stub()


bootstrap()
