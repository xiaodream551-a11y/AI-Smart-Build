# -*- coding: utf-8 -*-
"""修改选中构件的截面、标高等属性"""

__doc__ = "选中构件后修改截面尺寸、标高等属性，支持批量修改"
__title__ = "修改\n构件"
__author__ = "AI智建"

from pyrevit import revit, forms, script

from engine.logger import OperationLog, export_operation_log
from engine.modify import modify_element, batch_modify_by_filter
from utils import get_sorted_levels, list_story_floor_choices

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


MODE_SINGLE = u"单个修改"
MODE_BATCH = u"批量修改"


class StoryFloorOption(object):
    """批量操作的故事层选项。"""

    def __init__(self, floor_number, level):
        self.floor_number = floor_number
        self.level = level
        self.Name = u"第 {} 层（{}）".format(floor_number, level.Name)


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
    category_map = {
        u"柱": "column",
        u"梁": "beam",
    }

    category_text = forms.SelectFromList.show(
        [u"柱", u"梁"],
        title=u"选择批量修改的构件类型",
        button_name=u"确定"
    )
    if not category_text:
        return u"未选择构件类型"

    levels = get_sorted_levels(doc)
    floor_options = _build_floor_options(levels, category_map[category_text])
    if not floor_options:
        return u"当前模型中没有可用楼层"

    selected_level = forms.SelectFromList.show(
        floor_options,
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

    with revit.Transaction(u"AI智建：修改构件"):
        return batch_modify_by_filter(
            doc,
            category_map[category_text],
            selected_level.floor_number,
            old_section,
            new_section
        )


def _build_floor_options(levels, category):
    return [
        StoryFloorOption(floor_number, level)
        for floor_number, level in list_story_floor_choices(levels, category)
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
            result = _run_single_modify(doc)
            operation_log.log("modify_element", result)
        else:
            result = _run_batch_modify(doc)
            operation_log.log("batch_modify_by_filter", result)

        log_path = export_operation_log(operation_log, u"修改构件")
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
            u"修改构件时发生错误：{}".format(err),
            title=u"AI 智建"
        )


if __name__ == "__main__":
    main()
