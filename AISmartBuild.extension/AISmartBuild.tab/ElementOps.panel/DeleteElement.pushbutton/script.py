#! python3
# -*- coding: utf-8 -*-
"""Delete specified elements or batch-delete by filter criteria."""

__doc__ = "删除选中构件，或按楼层/类型批量删除"
__title__ = "删除\n构件"
__author__ = "AI智建"

from pyrevit import revit, forms, script

from engine.logger import OperationLog, export_operation_log
from engine.modify import delete_element, batch_delete_by_filter
from utils import get_sorted_levels, list_story_floor_choices


MODE_SINGLE = u"单个删除"
MODE_BATCH = u"批量删除"


class FloorOption(object):
    """Floor selection option."""

    def __init__(self, name, floor_number=None):
        self.Name = name
        self.floor_number = floor_number


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
    category_map = {
        u"柱": "column",
        u"梁": "beam",
        u"板": "slab",
    }

    category_text = forms.SelectFromList.show(
        [u"柱", u"梁", u"板"],
        title=u"选择批量删除的构件类别",
        button_name=u"确定"
    )
    if not category_text:
        return u"未选择构件类别"

    level_options = [FloorOption(u"全部楼层")]
    level_options.extend(_build_floor_options(doc, category_map[category_text]))

    selected_option = forms.SelectFromList.show(
        level_options,
        name_attr="Name",
        title=u"选择楼层条件（可选）",
        button_name=u"确定"
    )
    if not selected_option:
        return u"未选择楼层条件"

    if selected_option.floor_number:
        confirm_text = u"确定要删除第 {} 层的所有{}吗？".format(
            selected_option.floor_number,
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
            selected_option.floor_number
        )


def _build_floor_options(doc, category):
    return [
        FloorOption(
            u"第 {} 层（{}）".format(floor_number, level.Name),
            floor_number=floor_number
        )
        for floor_number, level in list_story_floor_choices(
            get_sorted_levels(doc), category
        )
    ]


def main():
    doc = revit.doc
    logger = script.get_logger()
    operation_log = OperationLog()

    try:
        mode = _pick_mode()
        if not mode:
            script.exit()

        if mode == MODE_SINGLE:
            result = _run_single_delete(doc)
            operation_log.log("delete_element", result)
        else:
            result = _run_batch_delete(doc)
            operation_log.log("batch_delete_by_filter", result)

        log_path = export_operation_log(operation_log, u"删除构件")
        message = result
        if log_path:
            message += u"\n\n{}\n日志：{}".format(
                operation_log.get_summary(),
                log_path
            )
        forms.alert(message, title=u"AI 智建")
    except Exception as err:
        logger.exception(err)
        forms.alert(
            u"删除构件时发生错误：{}".format(err),
            title=u"AI 智建"
        )


if __name__ == "__main__":
    main()
