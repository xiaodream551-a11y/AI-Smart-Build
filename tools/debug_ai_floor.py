# -*- coding: utf-8 -*-
"""本地 AI / 楼层解析调试脚本。"""

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.offline_runtime import FakeLevel, bootstrap, make_story_levels


bootstrap()

from ai.parser import parse_command  # noqa: E402
from utils import (  # noqa: E402
    get_story_count,
    resolve_floor_boundary_level,
    resolve_story_base_level,
    resolve_story_framing_level,
)


DEFAULT_REPLY = """```json
{"action":"create_beam","params":{"start_x":0,"start_y":0,"end_x":6000,"end_y":0,"floor":2,"section":"300x600"}}
```"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="离线调试 AI JSON 解析和楼层映射"
    )
    parser.add_argument(
        "--reply",
        help="模型原始回复文本，支持直接 JSON 或 markdown 代码块",
    )
    parser.add_argument(
        "--reply-file",
        help="从文件读取模型原始回复文本",
    )
    parser.add_argument(
        "--stories",
        type=int,
        default=5,
        help="按项目约定自动生成故事层数量，默认 5",
    )
    parser.add_argument(
        "--levels",
        help="自定义标高名称，逗号分隔，例如 '±0.000,F1,F2,屋面'",
    )
    return parser.parse_args()


def build_levels(args):
    if args.levels:
        names = [name.strip() for name in args.levels.split(",") if name.strip()]
        return [
            FakeLevel(name, float(index), index + 1)
            for index, name in enumerate(names)
        ]

    return make_story_levels(args.stories)


def read_reply(args):
    if args.reply:
        return args.reply
    if args.reply_file:
        with open(args.reply_file, "r", encoding="utf-8") as input_file:
            return input_file.read()
    return DEFAULT_REPLY


def describe_resolution(command, levels):
    action = command.get("action")
    params = command.get("params", {})

    result = {
        "action": action,
        "story_count": get_story_count(levels),
        "levels": [level.Name for level in levels],
    }

    if action == "create_column":
        base_level = resolve_floor_boundary_level(levels, params.get("base_floor"))
        top_level = resolve_floor_boundary_level(levels, params.get("top_floor"))
        result["resolved"] = {
            "base_floor": params.get("base_floor"),
            "base_level": getattr(base_level, "Name", None),
            "top_floor": params.get("top_floor"),
            "top_level": getattr(top_level, "Name", None),
        }
        return result

    if action in ("create_beam", "create_slab"):
        level = resolve_story_framing_level(levels, params.get("floor"))
        result["resolved"] = {
            "floor": params.get("floor"),
            "level": getattr(level, "Name", None),
        }
        return result

    if action in ("modify_section", "delete_element", "query_count"):
        category = params.get("element_type")
        floor = params.get("floor")
        if category in ("column", "columns", "柱"):
            level = resolve_story_base_level(levels, floor)
            level_kind = "story_base_level"
        else:
            level = resolve_story_framing_level(levels, floor)
            level_kind = "story_framing_level"

        result["resolved"] = {
            "element_type": category,
            "floor": floor,
            "level_kind": level_kind,
            "level": getattr(level, "Name", None),
        }
        return result

    if action == "generate_frame":
        result["resolved"] = {
            "x_span_count": len(params.get("x_spans", [])),
            "y_span_count": len(params.get("y_spans", [])),
            "num_floors": params.get("num_floors"),
            "expected_level_count": (
                int(params.get("num_floors", 0)) + 1
                if params.get("num_floors") is not None else None
            ),
        }
        return result

    result["resolved"] = {"message": params.get("message")}
    return result


def main():
    args = parse_args()
    levels = build_levels(args)
    reply_text = read_reply(args)

    try:
        command = parse_command(reply_text)
    except Exception as err:
        print("解析失败：{}".format(err), file=sys.stderr)
        return 1

    output = {
        "reply": reply_text,
        "command": command,
        "inspection": describe_resolution(command, levels),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
