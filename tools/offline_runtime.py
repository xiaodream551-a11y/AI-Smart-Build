# -*- coding: utf-8 -*-
"""离线调试辅助：在非 Revit 环境下导入 pyRevit 相关模块。"""

import importlib.util
import sys
import types
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LIB_DIR = ROOT_DIR / "AISmartBuild.extension" / "lib"


class FakeElementId(object):
    """简化版 ElementId。"""

    def __init__(self, value):
        self.IntegerValue = int(value)


class FakeStorageType(object):
    """简化版 StorageType 枚举。"""

    ElementId = "ElementId"
    Double = "Double"


class FakeBuiltInCategory(object):
    """简化版 BuiltInCategory 枚举。"""

    OST_StructuralColumns = 1
    OST_StructuralFraming = 2
    OST_Floors = 3


class FakeBuiltInParameter(object):
    """简化版 BuiltInParameter 枚举。"""

    FAMILY_BASE_LEVEL_PARAM = "FAMILY_BASE_LEVEL_PARAM"
    FAMILY_TOP_LEVEL_PARAM = "FAMILY_TOP_LEVEL_PARAM"
    FAMILY_TOP_LEVEL_OFFSET_PARAM = "FAMILY_TOP_LEVEL_OFFSET_PARAM"
    FAMILY_BASE_LEVEL_OFFSET_PARAM = "FAMILY_BASE_LEVEL_OFFSET_PARAM"
    INSTANCE_REFERENCE_LEVEL_PARAM = "INSTANCE_REFERENCE_LEVEL_PARAM"
    SCHEDULE_LEVEL_PARAM = "SCHEDULE_LEVEL_PARAM"
    LEVEL_PARAM = "LEVEL_PARAM"
    FLOOR_HEIGHTABOVELEVEL_PARAM = "FLOOR_HEIGHTABOVELEVEL_PARAM"
    Z_OFFSET_VALUE = "Z_OFFSET_VALUE"


class FakeCategory(object):
    """简化版 Category。"""

    def __init__(self, builtin, name=None):
        self.Id = FakeElementId(int(builtin))
        self.Name = name or str(builtin)


class FakeLevel(object):
    """简化版 Level。"""

    def __init__(self, name, elevation, element_id):
        self.Name = name
        self.Elevation = elevation
        self.Id = FakeElementId(element_id)


class FakeParameter(object):
    """简化版 Parameter。"""

    def __init__(self, value=None, storage_type=None, read_only=False):
        self._value = value
        self.StorageType = storage_type
        self.IsReadOnly = read_only

    def AsElementId(self):
        return self._value

    def AsDouble(self):
        return float(self._value)

    def Set(self, value):
        self._value = value


class FakeElement(object):
    """简化版模型元素。"""

    def __init__(self, element_id, category, level_id=None, params=None, name=None):
        self.Id = FakeElementId(element_id)
        self.category = category
        self.Category = FakeCategory(category, name=name)
        self.LevelId = FakeElementId(level_id) if level_id is not None else None
        self._params = dict(params or {})

    def get_Parameter(self, builtin):
        return self._params.get(builtin)


class FakeDocument(object):
    """简化版 Revit Document。"""

    def __init__(self, levels=None, elements=None):
        self.levels = list(levels or [])
        self.elements = list(elements or [])
        self._by_id = {}

        for level in self.levels:
            self._by_id[level.Id.IntegerValue] = level
        for element in self.elements:
            self._by_id[element.Id.IntegerValue] = element

    def GetElement(self, element_id):
        value = getattr(element_id, "IntegerValue", element_id)
        return self._by_id.get(value)


class FakeFilteredElementCollector(object):
    """简化版 FilteredElementCollector。"""

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
    StructuralType = types.SimpleNamespace(Column="Column", Beam="Beam")


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
    FilteredElementCollector=FakeFilteredElementCollector,
    FamilySymbol=type("FamilySymbol", (), {}),
    FloorType=type("FloorType", (), {}),
    Structure=_FakeStructure(),
)


class _FakeGenericListFactory(object):
    def __getitem__(self, _item):
        class _FakeList(list):
            def Add(self, value):
                self.append(value)

        return _FakeList


def ensure_lib_path():
    """把项目根目录和 lib 目录加入 sys.path。"""
    root = str(ROOT_DIR)
    lib = str(LIB_DIR)

    if root not in sys.path:
        sys.path.insert(0, root)
    if lib not in sys.path:
        sys.path.insert(0, lib)

    return LIB_DIR


def install_clr_stub():
    """安装最小可用的 clr/System stub。"""
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
    """安装最小可用的 pyrevit stub。"""
    pyrevit_module = types.ModuleType("pyrevit")
    pyrevit_module.__path__ = []
    pyrevit_module.DB = FakeDB
    pyrevit_module.revit = types.SimpleNamespace(doc=None, Transaction=_NullTransaction)
    pyrevit_module.forms = types.SimpleNamespace(
        WPFWindow=_FakeWPFWindow,
        ask_for_string=lambda *args, **kwargs: None,
        pick_file=lambda *args, **kwargs: None,
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
    """按项目约定生成一组故事层标高。"""
    levels = [FakeLevel("±0.000", 0.0, 1)]

    for index in range(1, story_count):
        levels.append(FakeLevel("F{}".format(index), float(index), index + 1))

    levels.append(FakeLevel("屋面", float(story_count), story_count + 1))
    return levels


def load_module_from_path(module_name, relative_path):
    """按相对路径加载项目中的 Python 文件。"""
    file_path = ROOT_DIR / relative_path
    if module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bootstrap():
    """一次性完成离线导入准备。"""
    ensure_lib_path()
    install_clr_stub()
    install_pyrevit_stub()


bootstrap()
