#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-platform environment check script."""

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
        "name": "Python version",
        "ok": is_ok,
        "detail": "Current version {}".format(current_version),
    }


def check_openpyxl():
    try:
        module = importlib.import_module("openpyxl")
    except Exception as err:
        return {
            "name": "openpyxl dependency",
            "ok": False,
            "detail": "Not installed or import failed: {}".format(err),
        }

    return {
        "name": "openpyxl dependency",
        "ok": True,
        "detail": "Installed, version {}".format(getattr(module, "__version__", "unknown")),
    }


def check_config_file():
    if not CONFIG_PATH.exists():
        return {
            "name": "DeepSeek config",
            "ok": False,
            "detail": "Config file not found: {}".format(CONFIG_PATH),
        }

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as input_file:
            data = json.load(input_file)
    except Exception as err:
        return {
            "name": "DeepSeek config",
            "ok": False,
            "detail": "Failed to read config file: {}".format(err),
        }

    api_key = ""
    if isinstance(data, dict):
        api_key = "{}".format(data.get("DEEPSEEK_API_KEY", "")).strip()

    if not api_key:
        return {
            "name": "DeepSeek config",
            "ok": False,
            "detail": "Config file exists but `DEEPSEEK_API_KEY` is empty: {}".format(CONFIG_PATH),
        }

    return {
        "name": "DeepSeek config",
        "ok": True,
        "detail": "Config file exists, API Key is set: {}".format(CONFIG_PATH),
    }


def check_extension_structure():
    issues = []

    if not EXTENSION_DIR.exists():
        return {
            "name": "Extension directory structure",
            "ok": False,
            "detail": "Extension directory not found: {}".format(EXTENSION_DIR),
        }

    for relative_path in REQUIRED_EXTENSION_FILES:
        full_path = EXTENSION_DIR / relative_path
        if not full_path.exists():
            issues.append("Missing file: {}".format(full_path.relative_to(ROOT_DIR)))

    for directory in EXTENSION_DIR.rglob("*"):
        if not directory.is_dir():
            continue

        if directory.name.endswith(".pushbutton"):
            for filename in ("bundle.yaml", "script.py"):
                target = directory / filename
                if not target.exists():
                    issues.append("Missing file: {}".format(target.relative_to(ROOT_DIR)))

        if directory.name.endswith(".panel") or directory.name.endswith(".tab"):
            target = directory / "bundle.yaml"
            if not target.exists():
                issues.append("Missing file: {}".format(target.relative_to(ROOT_DIR)))

    if issues:
        return {
            "name": "Extension directory structure",
            "ok": False,
            "detail": "Found {} issue(s): {}".format(len(issues), "; ".join(issues)),
        }

    return {
        "name": "Extension directory structure",
        "ok": True,
        "detail": "AISmartBuild.extension directory structure is complete",
    }


def main():
    checks = [
        check_python_version(),
        check_openpyxl(),
        check_config_file(),
        check_extension_structure(),
    ]

    print("=== AI SmartBuild — Environment Check Report ===")
    print("Project directory: {}".format(ROOT_DIR))
    print("Platform: {} {}".format(platform.system(), platform.release()))
    print()

    failed_count = 0
    for item in checks:
        prefix = "PASS" if item["ok"] else "FAIL"
        if not item["ok"]:
            failed_count += 1
        print("[{}] {}: {}".format(prefix, item["name"], item["detail"]))

    print()
    if failed_count == 0:
        print("Overall: Environment check passed, ready to proceed with installation or integration.")
    else:
        print("Overall: Found {} issue(s) to resolve, please fix according to the hints above.".format(failed_count))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
