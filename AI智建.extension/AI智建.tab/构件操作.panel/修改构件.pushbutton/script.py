# -*- coding: utf-8 -*-
"""修改选中构件的截面、标高等属性"""

__doc__ = "选中构件后修改截面尺寸、标高等属性，支持批量修改"
__title__ = "修改\n构件"
__author__ = "AI智建"

from pyrevit import revit, DB, forms, script

from engine.modify import modify_element, batch_modify_by_filter

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


MODE_SINGLE = u"单个修改"
MODE_BATCH = u"批量修改"


def _get_levels(doc):
    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level))
    levels.sort(key=lambda level: level.Elevation)
    return levels


def _ask_section(prompt, default=None):
    value = forms.ask_for_string(
        prompt=prompt,
        default=default or ""
    )
    if value is None:
        return None

    if isinstance(value, string_types):
        value = value.strip()
    else:
        value = "{}".format(value).strip()

    return value or None


def _pick_mode():
    return forms.SelectFromList.show(
        [MODE_SINGLE, MODE_BATCH],
        title=u"选择修改模式",
        button_name=u"确定"
    )


def _run_single_modify(doc):
    try:
        element = revit.pick_element("选择要修改的构件")
    except Exception:
        return u"未选择构件"

    if not element:
        return u"未选择构件"

    new_section = _ask_section(u"输入新的截面尺寸，如 600x600")
    if not new_section:
        return u"未输入新的截面尺寸"

    with revit.Transaction(u"AI智建：修改构件"):
        return modify_element(doc, element.Id, new_section=new_section)


def _run_batch_modify(doc):
    category_text = forms.SelectFromList.show(
        [u"柱", u"梁"],
        title=u"选择批量修改的构件类型",
        button_name=u"确定"
    )
    if not category_text:
        return u"未选择构件类型"

    levels = _get_levels(doc)
    if not levels:
        return u"当前模型中没有可用标高"

    selected_level = forms.SelectFromList.show(
        levels,
        name_attr="Name",
        title=u"选择批量修改的楼层",
        button_name=u"确定"
    )
    if not selected_level:
        return u"未选择楼层"

    old_section = _ask_section(u"输入旧截面尺寸，如 500x500")
    if not old_section:
        return u"未输入旧截面尺寸"

    new_section = _ask_section(u"输入新截面尺寸，如 600x600")
    if not new_section:
        return u"未输入新截面尺寸"

    category_map = {
        u"柱": "column",
        u"梁": "beam",
    }

    with revit.Transaction(u"AI智建：修改构件"):
        return batch_modify_by_filter(
            doc,
            category_map[category_text],
            selected_level,
            old_section,
            new_section
        )


def main():
    doc = revit.doc
    logger = script.get_logger()

    try:
        mode = _pick_mode()
        if not mode:
            script.exit()

        if mode == MODE_SINGLE:
            result = _run_single_modify(doc)
        else:
            result = _run_batch_modify(doc)

        forms.alert(result, title=u"AI 智建")
    except Exception as err:
        logger.exception(err)
        forms.alert(
            u"修改构件时发生错误：{}".format(err),
            title=u"AI 智建"
        )


if __name__ == "__main__":
    main()
