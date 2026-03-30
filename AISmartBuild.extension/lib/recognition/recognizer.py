# -*- coding: utf-8 -*-
"""PlanRecognizer -- 3-step architectural drawing recognition pipeline."""

import json
import os

from recognition.vision_client import call_vision_api
from recognition.prompts.step1_grids import format_prompt as step1_prompt
from recognition.prompts.step2_walls import format_prompt as step2_prompt
from recognition.prompts.step3_openings import format_prompt as step3_prompt
from recognition import schema
from recognition.coordinator import convert_all


class RecognitionResult(object):
    """Container for recognition pipeline output."""

    def __init__(self):
        self.step1 = None   # grids + levels
        self.step2 = None   # walls
        self.step3 = None   # doors + windows + rooms
        self.merged = None   # combined result
        self.absolute = None  # with absolute coordinates
        self.errors = []     # validation errors

    @property
    def ok(self):
        return len(self.errors) == 0

    def to_dict(self):
        return self.absolute or self.merged or {}

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class PlanRecognizer(object):
    """3-step pipeline: grids -> walls -> openings.

    Each step calls the vision API with the drawing image and a
    step-specific prompt. Results from earlier steps are fed as
    context to later steps.

    Usage::

        recognizer = PlanRecognizer()
        result = recognizer.recognize("floor_plan.png")
        if result.ok:
            print(result.to_json())
    """

    def __init__(self, api_key=None, api_url=None, model=None, timeout_ms=None):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout_ms = timeout_ms

    def _call_api(self, image_path, prompt):
        """Call vision API with common config."""
        return call_vision_api(
            image_path, prompt,
            api_key=self.api_key,
            api_url=self.api_url,
            model=self.model,
            timeout_ms=self.timeout_ms,
        )

    def recognize_step1(self, image_path):
        """Step 1: Recognize grids, levels, and drawing info.

        Returns:
            dict: Step 1 result (grids + levels + drawing_info).
        """
        prompt = step1_prompt()
        result = self._call_api(image_path, prompt)
        errors = schema.validate_step1(result)
        if errors:
            raise ValueError(u"Step 1 校验失败: {}".format("; ".join(errors)))
        return result

    def recognize_step2(self, image_path, step1_data):
        """Step 2: Recognize walls using grid context.

        Args:
            image_path: Path to the drawing image.
            step1_data: Dict from step 1 (must contain "grids").

        Returns:
            dict: Step 2 result (walls list).
        """
        prompt = step2_prompt(step1_data)
        result = self._call_api(image_path, prompt)
        errors = schema.validate_step2(result)
        if errors:
            raise ValueError(u"Step 2 校验失败: {}".format("; ".join(errors)))
        return result

    def recognize_step3(self, image_path, step1_data, step2_data):
        """Step 3: Recognize doors, windows, and rooms.

        Args:
            image_path: Path to the drawing image.
            step1_data: Dict from step 1 (must contain "grids").
            step2_data: Dict from step 2 (must contain "walls").

        Returns:
            dict: Step 3 result (doors + windows + rooms).
        """
        prompt = step3_prompt(step1_data, step2_data)
        result = self._call_api(image_path, prompt)
        errors = schema.validate_step3(result)
        if errors:
            raise ValueError(u"Step 3 校验失败: {}".format("; ".join(errors)))
        return result

    def recognize(self, image_path, steps=(1, 2, 3)):
        """Run the full recognition pipeline.

        Args:
            image_path: Path to the architectural drawing image.
            steps: Tuple of step numbers to run (default all 3).

        Returns:
            RecognitionResult with merged data and validation status.
        """
        if not os.path.isfile(image_path):
            raise ValueError(u"图片文件不存在: {}".format(image_path))

        result = RecognitionResult()

        # Step 1: grids + levels
        if 1 in steps:
            try:
                result.step1 = self.recognize_step1(image_path)
            except (ValueError, Exception) as err:
                result.errors.append(u"Step 1 失败: {}".format(str(err)))
                return result

        # Step 2: walls (needs step 1)
        if 2 in steps and result.step1:
            try:
                result.step2 = self.recognize_step2(image_path, result.step1)
            except (ValueError, Exception) as err:
                result.errors.append(u"Step 2 失败: {}".format(str(err)))

        # Step 3: openings (needs step 1 + 2)
        if 3 in steps and result.step1 and result.step2:
            try:
                result.step3 = self.recognize_step3(
                    image_path, result.step1, result.step2
                )
            except (ValueError, Exception) as err:
                result.errors.append(u"Step 3 失败: {}".format(str(err)))

        # Merge all results
        merged = {}
        if result.step1:
            merged.update(result.step1)
        if result.step2:
            merged["walls"] = result.step2.get("walls", [])
        if result.step3:
            merged["doors"] = result.step3.get("doors", [])
            merged["windows"] = result.step3.get("windows", [])
            merged["rooms"] = result.step3.get("rooms", [])

        result.merged = merged

        # Convert to absolute coordinates
        try:
            result.absolute = convert_all(merged)
        except Exception as err:
            result.errors.append(u"坐标转换失败: {}".format(str(err)))

        return result
