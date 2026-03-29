#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨平台环境检查脚本。"""

import importlib
import json
import os
import platform
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
EXTENSION_DIR = ROOT_DIR / "AISmartBuild.extension"
CONFIG_PATH = Path.home() / ".ai-smart-build" / "config.json"

REQUIRED_EXTENSION_FILES = [
    "extension.json",
    "startup.py",
    "templates/构件导入模板.xlsx",
    "AISmartBuild.tab/bundle.yaml",
    "AISmartBuild.tab/FrameModel.panel/bundle.yaml",
    "AISmartBuild.tab/FrameModel.panel/GenerateFrame.pushbutton/bundle.yaml",
    "AISmartBuild.tab/FrameModel.panel/GenerateFrame.pushbutton/script.py",
    "AISmartBuild.tab/FrameModel.panel/ExcelImport.pushbutton/bundle.yaml",
    "AISmartBuild.tab/FrameModel.panel/ExcelImport.pushbutton/script.py",
    "AISmartBuild.tab/AIChat.panel/bundle.yaml",
    "AISmartBuild.tab/AIChat.panel/SmartChat.pushbutton/bundle.yaml",
    "AISmartBuild.tab/AIChat.panel/SmartChat.pushbutton/script.py",
    "AISmartBuild.tab/ElementOps.panel/bundle.yaml",
    "AISmartBuild.tab/ElementOps.panel/ModifyElement.pushbutton/bundle.yaml",
    "AISmartBuild.tab/ElementOps.panel/ModifyElement.pushbutton/script.py",
    "AISmartBuild.tab/ElementOps.panel/DeleteElement.pushbutton/bundle.yaml",
    "AISmartBuild.tab/ElementOps.panel/DeleteElement.pushbutton/script.py",
    "AISmartBuild.tab/Help.panel/bundle.yaml",
    "AISmartBuild.tab/Help.panel/About.pushbutton/bundle.yaml",
    "AISmartBuild.tab/Help.panel/About.pushbutton/script.py",
    "AISmartBuild.tab/DataIO.panel/bundle.yaml",
    "AISmartBuild.tab/DataIO.panel/ExportModel.pushbutton/bundle.yaml",
    "AISmartBuild.tab/DataIO.panel/ExportModel.pushbutton/script.py",
]


def check_python_version():
    current_version = "{}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    is_ok = sys.version_info >= (3, 10)
    return {
        "name": "Python 版本",
        "ok": is_ok,
        "detail": "当前版本 {}".format(current_version),
    }


def check_openpyxl():
    try:
        module = importlib.import_module("openpyxl")
    except Exception as err:
        return {
            "name": "openpyxl 依赖",
            "ok": False,
            "detail": "未安装或导入失败：{}".format(err),
        }

    return {
        "name": "openpyxl 依赖",
        "ok": True,
        "detail": "已安装，版本 {}".format(getattr(module, "__version__", "unknown")),
    }


def check_config_file():
    if not CONFIG_PATH.exists():
        return {
            "name": "DeepSeek 配置",
            "ok": False,
            "detail": "未找到配置文件：{}".format(CONFIG_PATH),
        }

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as input_file:
            data = json.load(input_file)
    except Exception as err:
        return {
            "name": "DeepSeek 配置",
            "ok": False,
            "detail": "配置文件读取失败：{}".format(err),
        }

    api_key = ""
    if isinstance(data, dict):
        api_key = "{}".format(data.get("DEEPSEEK_API_KEY", "")).strip()

    if not api_key:
        return {
            "name": "DeepSeek 配置",
            "ok": False,
            "detail": "配置文件存在，但 `DEEPSEEK_API_KEY` 为空：{}".format(CONFIG_PATH),
        }

    return {
        "name": "DeepSeek 配置",
        "ok": True,
        "detail": "配置文件存在，API Key 已填写：{}".format(CONFIG_PATH),
    }


def check_extension_structure():
    issues = []

    if not EXTENSION_DIR.exists():
        return {
            "name": "扩展目录结构",
            "ok": False,
            "detail": "未找到扩展目录：{}".format(EXTENSION_DIR),
        }

    for relative_path in REQUIRED_EXTENSION_FILES:
        full_path = EXTENSION_DIR / relative_path
        if not full_path.exists():
            issues.append("缺少文件：{}".format(full_path.relative_to(ROOT_DIR)))

    for directory in EXTENSION_DIR.rglob("*"):
        if not directory.is_dir():
            continue

        if directory.name.endswith(".pushbutton"):
            for filename in ("bundle.yaml", "script.py"):
                target = directory / filename
                if not target.exists():
                    issues.append("缺少文件：{}".format(target.relative_to(ROOT_DIR)))

        if directory.name.endswith(".panel") or directory.name.endswith(".tab"):
            target = directory / "bundle.yaml"
            if not target.exists():
                issues.append("缺少文件：{}".format(target.relative_to(ROOT_DIR)))

    if issues:
        return {
            "name": "扩展目录结构",
            "ok": False,
            "detail": "发现 {} 个问题：{}".format(len(issues), "；".join(issues)),
        }

    return {
        "name": "扩展目录结构",
        "ok": True,
        "detail": "AISmartBuild.extension 目录结构完整",
    }


def main():
    checks = [
        check_python_version(),
        check_openpyxl(),
        check_config_file(),
        check_extension_structure(),
    ]

    print("=== AI 智建 — 环境检查报告 ===")
    print("项目目录：{}".format(ROOT_DIR))
    print("运行平台：{} {}".format(platform.system(), platform.release()))
    print()

    failed_count = 0
    for item in checks:
        prefix = "通过" if item["ok"] else "失败"
        if not item["ok"]:
            failed_count += 1
        print("[{}] {}：{}".format(prefix, item["name"], item["detail"]))

    print()
    if failed_count == 0:
        print("总体结论：环境检查通过，可以继续安装或联调。")
    else:
        print("总体结论：发现 {} 项待处理问题，请按上面的提示修正。".format(failed_count))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
