# -*- coding: utf-8 -*-
"""Tests for the recognition module (schema, coordinator, prompts, recognizer)."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from recognition.schema import validate_step1, validate_step2, validate_step3, validate_full
from recognition.coordinator import (
    grid_ref_to_absolute,
    wall_to_absolute,
    opening_to_absolute,
    convert_all,
)
from recognition.prompts.step1_grids import format_prompt as step1_prompt
from recognition.prompts.step2_walls import format_prompt as step2_prompt
from recognition.prompts.step3_openings import format_prompt as step3_prompt
from recognition.recognizer import PlanRecognizer, RecognitionResult


# ──────────────────────────────────────────────
# Test fixtures
# ──────────────────────────────────────────────

SAMPLE_GRIDS = {
    "x": [
        {"name": "1", "distance": 0},
        {"name": "2", "distance": 1500},
        {"name": "3", "distance": 3600},
        {"name": "4", "distance": 7800},
        {"name": "5", "distance": 11400},
    ],
    "y": [
        {"name": "A", "distance": 0},
        {"name": "B", "distance": 1500},
        {"name": "C", "distance": 6000},
        {"name": "D", "distance": 9300},
        {"name": "E", "distance": 9900},
    ],
}

SAMPLE_STEP1 = {
    "drawing_info": {"title": "一层平面图", "scale": "1:100", "floor": 1},
    "grids": SAMPLE_GRIDS,
    "levels": [
        {"name": "1F", "elevation": 0.0},
        {"name": "2F", "elevation": 3.4},
    ],
}

SAMPLE_WALLS = [
    {
        "id": "W1",
        "start": {"grid_x": "1", "grid_y": "A", "offset_x": 0, "offset_y": 0},
        "end": {"grid_x": "5", "grid_y": "A", "offset_x": 0, "offset_y": 0},
        "thickness": 240,
        "type": "exterior",
    },
    {
        "id": "W2",
        "start": {"grid_x": "1", "grid_y": "A", "offset_x": 0, "offset_y": 0},
        "end": {"grid_x": "1", "grid_y": "E", "offset_x": 0, "offset_y": 0},
        "thickness": 240,
        "type": "exterior",
    },
    {
        "id": "W3",
        "start": {"grid_x": "3", "grid_y": "A", "offset_x": 0, "offset_y": 0},
        "end": {"grid_x": "3", "grid_y": "C", "offset_x": 0, "offset_y": 0},
        "thickness": 240,
        "type": "interior",
    },
]

SAMPLE_STEP2 = {"walls": SAMPLE_WALLS}

SAMPLE_STEP3 = {
    "doors": [
        {
            "code": "M1527",
            "width": 1500,
            "height": 2700,
            "host_wall": "W1",
            "position": {"grid_x": "3", "grid_y": "A", "offset_x": 600, "offset_y": 0},
        }
    ],
    "windows": [
        {
            "code": "C0918",
            "width": 900,
            "height": 1800,
            "sill_height": 900,
            "host_wall": "W2",
            "position": {"grid_x": "1", "grid_y": "D", "offset_x": 0, "offset_y": 0},
        }
    ],
    "rooms": [
        {"name": "客厅", "floor": 1},
        {"name": "车库", "floor": 1},
    ],
}


# ──────────────────────────────────────────────
# Schema validation tests
# ──────────────────────────────────────────────

class TestValidateStep1:
    def test_valid(self):
        assert validate_step1(SAMPLE_STEP1) == []

    def test_missing_grids(self):
        data = {"drawing_info": {"floor": 1}}
        errors = validate_step1(data)
        assert any("grids" in e for e in errors)

    def test_missing_floor(self):
        data = {"drawing_info": {"title": "test"}, "grids": SAMPLE_GRIDS}
        errors = validate_step1(data)
        assert any("floor" in e for e in errors)

    def test_too_few_grid_lines(self):
        data = {
            "drawing_info": {"floor": 1},
            "grids": {
                "x": [{"name": "1", "distance": 0}],
                "y": SAMPLE_GRIDS["y"],
            },
        }
        errors = validate_step1(data)
        assert any("at least 2" in e for e in errors)

    def test_missing_distance(self):
        data = {
            "drawing_info": {"floor": 1},
            "grids": {
                "x": [{"name": "1"}, {"name": "2", "distance": 1500}],
                "y": SAMPLE_GRIDS["y"],
            },
        }
        errors = validate_step1(data)
        assert any("distance" in e for e in errors)


class TestValidateStep2:
    def test_valid(self):
        assert validate_step2(SAMPLE_STEP2) == []

    def test_missing_walls(self):
        errors = validate_step2({})
        assert any("walls" in e for e in errors)

    def test_empty_walls(self):
        errors = validate_step2({"walls": []})
        assert any("empty" in e for e in errors)

    def test_missing_wall_fields(self):
        data = {"walls": [{"thickness": 240, "type": "exterior"}]}
        errors = validate_step2(data)
        assert any("id" in e for e in errors)
        assert any("start" in e for e in errors)

    def test_invalid_wall_type(self):
        wall = dict(SAMPLE_WALLS[0])
        wall["type"] = "unknown"
        errors = validate_step2({"walls": [wall]})
        assert any("type" in e for e in errors)


class TestValidateStep3:
    def test_valid(self):
        assert validate_step3(SAMPLE_STEP3) == []

    def test_missing_doors(self):
        data = {"windows": [], "rooms": []}
        errors = validate_step3(data)
        assert any("doors" in e for e in errors)

    def test_missing_door_code(self):
        data = {
            "doors": [{"width": 900, "height": 2400, "host_wall": "W1"}],
            "windows": [],
            "rooms": [],
        }
        errors = validate_step3(data)
        assert any("code" in e for e in errors)

    def test_missing_room_name(self):
        data = {"doors": [], "windows": [], "rooms": [{"floor": 1}]}
        errors = validate_step3(data)
        assert any("name" in e for e in errors)


class TestValidateFull:
    def test_valid_merged(self):
        merged = {}
        merged.update(SAMPLE_STEP1)
        merged.update(SAMPLE_STEP2)
        merged.update(SAMPLE_STEP3)
        assert validate_full(merged) == []


# ──────────────────────────────────────────────
# Coordinator tests
# ──────────────────────────────────────────────

class TestGridRefToAbsolute:
    def test_origin(self):
        ref = {"grid_x": "1", "grid_y": "A", "offset_x": 0, "offset_y": 0}
        assert grid_ref_to_absolute(SAMPLE_GRIDS, ref) == (0, 0)

    def test_known_grid(self):
        ref = {"grid_x": "3", "grid_y": "C", "offset_x": 0, "offset_y": 0}
        assert grid_ref_to_absolute(SAMPLE_GRIDS, ref) == (3600, 6000)

    def test_with_offset(self):
        ref = {"grid_x": "1", "grid_y": "A", "offset_x": 500, "offset_y": 300}
        assert grid_ref_to_absolute(SAMPLE_GRIDS, ref) == (500, 300)

    def test_last_grid(self):
        ref = {"grid_x": "5", "grid_y": "E", "offset_x": 0, "offset_y": 0}
        assert grid_ref_to_absolute(SAMPLE_GRIDS, ref) == (11400, 9900)

    def test_unknown_grid_raises(self):
        ref = {"grid_x": "99", "grid_y": "A"}
        with pytest.raises(ValueError, match="X"):
            grid_ref_to_absolute(SAMPLE_GRIDS, ref)

    def test_unknown_y_grid_raises(self):
        ref = {"grid_x": "1", "grid_y": "Z"}
        with pytest.raises(ValueError, match="Y"):
            grid_ref_to_absolute(SAMPLE_GRIDS, ref)


class TestWallToAbsolute:
    def test_south_wall(self):
        result = wall_to_absolute(SAMPLE_GRIDS, SAMPLE_WALLS[0])
        assert result["id"] == "W1"
        assert result["start_x"] == 0
        assert result["start_y"] == 0
        assert result["end_x"] == 11400
        assert result["end_y"] == 0
        assert result["thickness"] == 240

    def test_west_wall(self):
        result = wall_to_absolute(SAMPLE_GRIDS, SAMPLE_WALLS[1])
        assert result["start_x"] == 0
        assert result["start_y"] == 0
        assert result["end_x"] == 0
        assert result["end_y"] == 9900

    def test_interior_wall(self):
        result = wall_to_absolute(SAMPLE_GRIDS, SAMPLE_WALLS[2])
        assert result["start_x"] == 3600
        assert result["end_x"] == 3600
        assert result["end_y"] == 6000
        assert result["type"] == "interior"


class TestOpeningToAbsolute:
    def test_door_position(self):
        door = SAMPLE_STEP3["doors"][0]
        result = opening_to_absolute(SAMPLE_GRIDS, door)
        assert result["position_x"] == 3600 + 600  # grid 3 + offset
        assert result["position_y"] == 0
        assert result["code"] == "M1527"

    def test_window_position(self):
        window = SAMPLE_STEP3["windows"][0]
        result = opening_to_absolute(SAMPLE_GRIDS, window)
        assert result["position_x"] == 0
        assert result["position_y"] == 9300  # grid D


class TestConvertAll:
    def test_full_conversion(self):
        merged = {}
        merged.update(SAMPLE_STEP1)
        merged.update(SAMPLE_STEP2)
        merged.update(SAMPLE_STEP3)
        result = convert_all(merged)

        assert result["grids"] == SAMPLE_GRIDS
        assert len(result["walls"]) == 3
        assert result["walls"][0]["start_x"] == 0
        assert result["walls"][0]["end_x"] == 11400
        assert len(result["doors"]) == 1
        assert result["doors"][0]["position_x"] == 4200
        assert len(result["windows"]) == 1
        assert len(result["rooms"]) == 2


# ──────────────────────────────────────────────
# Prompt formatting tests
# ──────────────────────────────────────────────

class TestPromptFormatting:
    def test_step1_prompt(self):
        prompt = step1_prompt()
        assert "轴网" in prompt
        assert "JSON" in prompt
        assert "distance" in prompt

    def test_step2_prompt_includes_grids(self):
        prompt = step2_prompt(SAMPLE_STEP1)
        assert "1500" in prompt
        assert "墙体" in prompt
        assert "grid_x" in prompt

    def test_step3_prompt_includes_walls(self):
        prompt = step3_prompt(SAMPLE_STEP1, SAMPLE_STEP2)
        assert "W1" in prompt
        assert "门" in prompt
        assert "C0918" in prompt or "窗" in prompt


# ──────────────────────────────────────────────
# Recognizer integration tests (with mocked API)
# ──────────────────────────────────────────────

class TestPlanRecognizer:
    @pytest.fixture
    def tmp_image(self, tmp_path):
        """Create a tiny dummy image file for testing."""
        img = tmp_path / "test_plan.png"
        # Minimal 1x1 PNG
        img.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return str(img)

    @patch("recognition.recognizer.call_vision_api")
    def test_step1_only(self, mock_api, tmp_image):
        mock_api.return_value = SAMPLE_STEP1
        rec = PlanRecognizer(api_key="test")
        result = rec.recognize(tmp_image, steps=(1,))
        assert result.ok
        assert result.step1 == SAMPLE_STEP1
        assert result.step2 is None
        assert result.step3 is None
        mock_api.assert_called_once()

    @patch("recognition.recognizer.call_vision_api")
    def test_full_pipeline(self, mock_api, tmp_image):
        mock_api.side_effect = [SAMPLE_STEP1, SAMPLE_STEP2, SAMPLE_STEP3]
        rec = PlanRecognizer(api_key="test")
        result = rec.recognize(tmp_image)
        assert result.ok
        assert mock_api.call_count == 3
        assert result.step1 is not None
        assert result.step2 is not None
        assert result.step3 is not None
        # Check merged result has all keys
        data = result.to_dict()
        assert "grids" in data
        assert "walls" in data
        assert "doors" in data
        assert "windows" in data
        assert "rooms" in data

    @patch("recognition.recognizer.call_vision_api")
    def test_full_pipeline_absolute_coords(self, mock_api, tmp_image):
        mock_api.side_effect = [SAMPLE_STEP1, SAMPLE_STEP2, SAMPLE_STEP3]
        rec = PlanRecognizer(api_key="test")
        result = rec.recognize(tmp_image)
        data = result.to_dict()
        # Walls should have absolute coordinates
        w1 = data["walls"][0]
        assert w1["start_x"] == 0
        assert w1["end_x"] == 11400

    @patch("recognition.recognizer.call_vision_api")
    def test_step1_failure_stops_pipeline(self, mock_api, tmp_image):
        mock_api.side_effect = Exception("API error")
        rec = PlanRecognizer(api_key="test")
        result = rec.recognize(tmp_image)
        assert not result.ok
        assert "Step 1" in result.errors[0]
        assert result.step2 is None
        assert result.step3 is None

    @patch("recognition.recognizer.call_vision_api")
    def test_step2_failure_still_has_step1(self, mock_api, tmp_image):
        mock_api.side_effect = [SAMPLE_STEP1, Exception("wall error")]
        rec = PlanRecognizer(api_key="test")
        result = rec.recognize(tmp_image)
        assert result.step1 is not None
        assert "Step 2" in result.errors[0]

    @patch("recognition.recognizer.call_vision_api")
    def test_json_output(self, mock_api, tmp_image):
        mock_api.side_effect = [SAMPLE_STEP1, SAMPLE_STEP2, SAMPLE_STEP3]
        rec = PlanRecognizer(api_key="test")
        result = rec.recognize(tmp_image)
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["drawing_info"]["title"] == "一层平面图"

    def test_missing_image_raises(self):
        rec = PlanRecognizer(api_key="test")
        with pytest.raises(ValueError, match="不存在"):
            rec.recognize("/nonexistent/path.png")

    @patch("recognition.recognizer.call_vision_api")
    def test_validation_error_in_step1(self, mock_api, tmp_image):
        # Return data missing required fields
        mock_api.return_value = {"drawing_info": {"floor": 1}}
        rec = PlanRecognizer(api_key="test")
        result = rec.recognize(tmp_image, steps=(1,))
        assert not result.ok
        assert "Step 1" in result.errors[0]


# ──────────────────────────────────────────────
# Vision client tests
# ──────────────────────────────────────────────

class TestVisionClient:
    def test_strip_markdown_fence(self):
        from recognition.vision_client import _strip_markdown_fence
        raw = '```json\n{"key": "value"}\n```'
        assert _strip_markdown_fence(raw) == '{"key": "value"}'

    def test_strip_no_fence(self):
        from recognition.vision_client import _strip_markdown_fence
        raw = '{"key": "value"}'
        assert _strip_markdown_fence(raw) == '{"key": "value"}'

    def test_guess_media_type(self):
        from recognition.vision_client import _guess_media_type
        assert _guess_media_type("test.png") == "image/png"
        assert _guess_media_type("test.jpg") == "image/jpeg"
        assert _guess_media_type("test.JPEG") == "image/jpeg"
        assert _guess_media_type("test.bmp") == "image/bmp"
        assert _guess_media_type("test.xyz") == "image/png"  # default

    def test_missing_api_key_raises(self, tmp_path):
        from recognition.vision_client import call_vision_api
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG")
        with pytest.raises(ValueError, match="VISION_API_KEY"):
            call_vision_api(str(img), "test", api_key="")

    def test_missing_file_raises(self):
        from recognition.vision_client import call_vision_api
        with pytest.raises(ValueError, match="不存在"):
            call_vision_api("/no/such/file.png", "test", api_key="key")
