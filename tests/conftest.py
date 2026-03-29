# -*- coding: utf-8 -*-

import importlib
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
root_text = str(ROOT_DIR)
if root_text not in sys.path:
    sys.path.insert(0, root_text)

from tools.offline_runtime import bootstrap, load_module_from_path


bootstrap()


def reload_module(module_name):
    """Reload a module during tests to pick up the latest env vars and file state."""
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def load_project_script(module_name, relative_path):
    """Load a button script by relative path."""
    return load_module_from_path(module_name, relative_path)
