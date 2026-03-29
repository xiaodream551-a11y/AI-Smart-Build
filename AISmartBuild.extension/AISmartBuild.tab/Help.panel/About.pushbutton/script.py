# -*- coding: utf-8 -*-
"""查看插件版本与环境信息。"""

__doc__ = "查看插件版本与环境信息"
__title__ = "关于"
__author__ = "AI智建"

import sys

from pyrevit import forms, revit

from config import DEEPSEEK_API_KEY, USER_CONFIG_PATH, VERSION

try:
    from pyrevit.versionmgr import get_pyrevit_version
except Exception:
    get_pyrevit_version = None


def _get_pyrevit_version_text():
    if get_pyrevit_version is None:
        return u"未知"

    try:
        version = get_pyrevit_version()
    except Exception:
        return u"未知"

    if version is None:
        return u"未知"

    formatter = getattr(version, "get_formatted", None)
    if callable(formatter):
        try:
            return formatter()
        except Exception:
            pass

    formatted = getattr(version, "formatted", None)
    if formatted:
        return u"{}".format(formatted)
    return u"{}".format(version)


def _get_revit_version_text():
    try:
        app = revit.doc.Application
        return u"{}".format(getattr(app, "VersionNumber", u"未知"))
    except Exception:
        return u"未知"


def main():
    message = (
        u"插件版本：v{version}\n"
        u"Python 版本：{python_version}\n"
        u"pyRevit 版本：{pyrevit_version}\n"
        u"Revit 版本：{revit_version}\n"
        u"DeepSeek API Key：{api_key_status}\n"
        u"用户配置文件路径：{config_path}"
    ).format(
        version=VERSION,
        python_version=sys.version,
        pyrevit_version=_get_pyrevit_version_text(),
        revit_version=_get_revit_version_text(),
        api_key_status=u"已配置" if DEEPSEEK_API_KEY else u"未配置",
        config_path=USER_CONFIG_PATH,
    )
    forms.alert(message, title=u"AI 智建 — 关于")


if __name__ == "__main__":
    main()
