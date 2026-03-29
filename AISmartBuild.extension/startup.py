# -*- coding: utf-8 -*-
"""pyRevit extension startup script."""

import os
import sys

from pyrevit import script


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(CURRENT_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from config import VERSION  # noqa: E402


def _write_output(message):
    try:
        output = script.get_output()
        output.print_md(message)
        return
    except Exception:
        pass
    print(message)


def _detect_runtime():
    implementation = ""
    try:
        implementation = sys.implementation.name
    except Exception:
        implementation = ""

    normalized = "{} {}".format(
        implementation,
        sys.version
    ).lower()
    if "ironpython" in normalized:
        return "IronPython"
    return "CPython"


def main():
    _write_output(u"AI 智建 v{} 已加载".format(VERSION))
    _write_output(u"运行环境: {}".format(_detect_runtime()))


main()
