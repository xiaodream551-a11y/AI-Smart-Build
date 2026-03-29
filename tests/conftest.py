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
    """在测试中重载模块，确保读取最新环境变量与文件状态。"""
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def load_project_script(module_name, relative_path):
    """按相对路径加载按钮脚本。"""
    return load_module_from_path(module_name, relative_path)
