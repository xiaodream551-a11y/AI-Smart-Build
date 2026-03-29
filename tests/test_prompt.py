# -*- coding: utf-8 -*-

from ai.prompt import SYSTEM_PROMPT


def test_system_prompt_contains_strict_json_only_constraints():
    assert "你**只能**输出一个合法的 JSON 对象或 JSON 数组" in SYSTEM_PROMPT
    assert "不要输出任何解释、注释、markdown 代码块包裹或其他文字" in SYSTEM_PROMPT
    assert "json.loads() 直接解析" in SYSTEM_PROMPT


def test_system_prompt_contains_default_and_range_rules():
    assert "截面宽度和高度不能超过 2000mm，不能小于 100mm" in SYSTEM_PROMPT
    assert "如果用户只说“加一根柱子”但没给坐标，默认 `x=0, y=0`" in SYSTEM_PROMPT
    assert "如果用户只说“加梁”但没给楼层，默认 `floor=1`" in SYSTEM_PROMPT


def test_system_prompt_contains_boundary_examples():
    assert "用户：加一根柱子" in SYSTEM_PROMPT
    assert "用户：在A1和B1各创建一根柱子" in SYSTEM_PROMPT
    assert "用户：在三层创建一块板" in SYSTEM_PROMPT


def test_system_prompt_contains_query_detail_and_summary_docs():
    assert "- query_detail：查询构件明细" in SYSTEM_PROMPT
    assert "- query_summary：查询模型统计汇总" in SYSTEM_PROMPT
    assert "用户：列出二层所有 500 柱子" in SYSTEM_PROMPT
    assert "用户：查看当前模型统计" in SYSTEM_PROMPT
