# -*- coding: utf-8 -*-
"""删除指定构件或按条件批量删除"""

__doc__ = "删除选中构件，或按楼层/类型批量删除"
__title__ = "删除\n构件"
__author__ = "AI智建"

from pyrevit import revit, DB, forms, script

from engine.modify import delete_element, batch_delete_by_filter


MODE_SINGLE = u"单个删除"
MODE_BATCH = u"批量删除"


class LevelOption(object):
    """楼层选择项"""

    def __init__(self, name, level=None):
        self.Name = name
        self.level = level


def _get_levels(doc):
    levels = list(DB.FilteredElementCollector(doc).OfClass(DB.Level))
    levels.sort(key=lambda level: level.Elevation)
    return levels


def _pick_mode():
    return forms.SelectFromList.show(
        [MODE_SINGLE, MODE_BATCH],
        title=u"选择删除模式",
        button_name=u"确定"
    )


def _confirm(message):
    return forms.alert(
        message,
        title=u"AI 智建",
        yes=True,
        no=True
    )


def _get_element_label(element):
    if element and element.Category:
        return element.Category.Name
    return u"构件"


def _run_single_delete(doc):
    try:
        element = revit.pick_element("选择要删除的构件")
    except Exception:
        return u"未选择构件"

    if not element:
        return u"未选择构件"

    confirm_text = u"确定要删除{}(ID: {})吗？".format(
        _get_element_label(element),
        element.Id.IntegerValue
    )
    if not _confirm(confirm_text):
        return u"已取消删除"

    with revit.Transaction(u"AI智建：删除构件"):
        return delete_element(doc, element.Id)


def _run_batch_delete(doc):
    category_text = forms.SelectFromList.show(
        [u"柱", u"梁", u"板"],
        title=u"选择批量删除的构件类别",
        button_name=u"确定"
    )
    if not category_text:
        return u"未选择构件类别"

    level_options = [LevelOption(u"全部楼层")]
    for level in _get_levels(doc):
        level_options.append(LevelOption(level.Name, level))

    selected_option = forms.SelectFromList.show(
        level_options,
        name_attr="Name",
        title=u"选择楼层条件（可选）",
        button_name=u"确定"
    )
    if not selected_option:
        return u"未选择楼层条件"

    category_map = {
        u"柱": "column",
        u"梁": "beam",
        u"板": "slab",
    }

    if selected_option.level:
        confirm_text = u"确定要删除标高“{}”上的所有{}吗？".format(
            selected_option.level.Name,
            category_text
        )
    else:
        confirm_text = u"确定要删除所有{}吗？".format(category_text)

    if not _confirm(confirm_text):
        return u"已取消删除"

    with revit.Transaction(u"AI智建：删除构件"):
        return batch_delete_by_filter(
            doc,
            category_map[category_text],
            selected_option.level
        )


def main():
    doc = revit.doc
    logger = script.get_logger()

    try:
        mode = _pick_mode()
        if not mode:
            script.exit()

        if mode == MODE_SINGLE:
            result = _run_single_delete(doc)
        else:
            result = _run_batch_delete(doc)

        forms.alert(result, title=u"AI 智建")
    except Exception as err:
        logger.exception(err)
        forms.alert(
            u"删除构件时发生错误：{}".format(err),
            title=u"AI 智建"
        )


if __name__ == "__main__":
    main()
