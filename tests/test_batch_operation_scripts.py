# -*- coding: utf-8 -*-

from conftest import load_project_script
from tools.offline_runtime import FakeDocument, make_story_levels


modify_script = load_project_script(
    "modify_script_for_tests",
    "AI智建.extension/AI智建.tab/构件操作.panel/修改构件.pushbutton/script.py",
)

delete_script = load_project_script(
    "delete_script_for_tests",
    "AI智建.extension/AI智建.tab/构件操作.panel/删除构件.pushbutton/script.py",
)


def test_batch_modify_uses_story_floor_number(monkeypatch):
    doc = FakeDocument(levels=make_story_levels(3))
    records = {}
    sections = iter([u"500x500", u"600x600"])
    call_count = {"value": 0}

    def fake_show(options, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            assert options == [u"柱", u"梁"]
            return u"柱"

        assert options[0].Name == u"第 1 层（±0.000）"
        return options[1]

    monkeypatch.setattr(
        modify_script.forms.SelectFromList,
        "show",
        fake_show
    )
    monkeypatch.setattr(
        modify_script,
        "_ask_section",
        lambda *args, **kwargs: next(sections)
    )
    monkeypatch.setattr(
        modify_script,
        "batch_modify_by_filter",
        lambda doc_arg, category, floor_level, old_section, new_section: (
            records.update({
                "doc": doc_arg,
                "category": category,
                "floor_level": floor_level,
                "old_section": old_section,
                "new_section": new_section,
            }) or u"ok"
        )
    )

    result = modify_script._run_batch_modify(doc)

    assert result == u"ok"
    assert records["doc"] is doc
    assert records["category"] == "column"
    assert records["floor_level"] == 2
    assert records["old_section"] == u"500x500"
    assert records["new_section"] == u"600x600"


def test_batch_delete_uses_story_floor_number(monkeypatch):
    doc = FakeDocument(levels=make_story_levels(3))
    records = {}
    call_count = {"value": 0}

    def fake_show(options, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            assert options == [u"柱", u"梁", u"板"]
            return u"梁"

        assert options[1].Name == u"第 1 层（F1）"
        assert options[2].Name == u"第 2 层（F2）"
        return options[2]

    monkeypatch.setattr(
        delete_script.forms.SelectFromList,
        "show",
        fake_show
    )
    monkeypatch.setattr(delete_script, "_confirm", lambda _message: True)
    monkeypatch.setattr(
        delete_script,
        "batch_delete_by_filter",
        lambda doc_arg, category, floor_level: (
            records.update({
                "doc": doc_arg,
                "category": category,
                "floor_level": floor_level,
            }) or u"ok"
        )
    )

    result = delete_script._run_batch_delete(doc)

    assert result == u"ok"
    assert records["doc"] is doc
    assert records["category"] == "beam"
    assert records["floor_level"] == 2
