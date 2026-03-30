# -*- coding: utf-8 -*-
"""Regression tests for recognition accuracy against ground truth data.

Validates that:
1. Ground truth data passes schema validation
2. Ground truth converts to valid absolute coordinates
3. Ground truth generates a correct build plan
4. Scoring functions correctly compare API results vs ground truth
"""

import json
import os
from pathlib import Path

import pytest

from recognition.schema import validate_step1, validate_step2, validate_step3, validate_full
from recognition.coordinator import convert_all, grid_ref_to_absolute
from recognition.dispatcher import generate_build_plan, preview_build_plan


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
EXPECTED_PATH = EXAMPLES_DIR / "villa_recognition_expected.json"


@pytest.fixture
def ground_truth():
    """Load the villa ground truth data."""
    with open(str(EXPECTED_PATH), "r", encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# Scoring utilities
# ──────────────────────────────────────────────

def score_grids(actual, expected):
    """Score grid recognition accuracy.

    Returns:
        dict: {matched, total, accuracy, details}
    """
    details = []
    total = 0
    matched = 0

    for axis in ("x", "y"):
        expected_grids = {str(g["name"]): g["distance"] for g in expected.get(axis, [])}
        actual_grids = {str(g["name"]): g["distance"] for g in actual.get(axis, [])}
        total += len(expected_grids)

        for name, exp_dist in expected_grids.items():
            if name in actual_grids:
                act_dist = actual_grids[name]
                if abs(act_dist - exp_dist) <= 100:  # 100mm tolerance
                    matched += 1
                    details.append({"axis": axis, "name": name, "status": "ok"})
                else:
                    details.append({
                        "axis": axis, "name": name, "status": "wrong_distance",
                        "expected": exp_dist, "actual": act_dist,
                    })
            else:
                details.append({"axis": axis, "name": name, "status": "missing"})

    accuracy = matched / total if total > 0 else 0
    return {"matched": matched, "total": total, "accuracy": accuracy, "details": details}


def score_walls(actual_walls, expected_walls, grids):
    """Score wall recognition accuracy.

    Compares by checking if endpoints are close (within 500mm).
    """
    matched = 0
    total = len(expected_walls)

    for ew in expected_walls:
        e_start = grid_ref_to_absolute(grids, ew["start"])
        e_end = grid_ref_to_absolute(grids, ew["end"])

        for aw in actual_walls:
            a_start = grid_ref_to_absolute(grids, aw["start"])
            a_end = grid_ref_to_absolute(grids, aw["end"])

            if (_points_close(e_start, a_start, 500) and _points_close(e_end, a_end, 500)) or \
               (_points_close(e_start, a_end, 500) and _points_close(e_end, a_start, 500)):
                matched += 1
                break

    accuracy = matched / total if total > 0 else 0
    return {"matched": matched, "total": total, "accuracy": accuracy}


def score_openings(actual, expected):
    """Score door/window recognition by matching codes."""
    expected_codes = sorted([item["code"] for item in expected])
    actual_codes = sorted([item["code"] for item in actual])

    matched = 0
    remaining = list(actual_codes)
    for code in expected_codes:
        if code in remaining:
            matched += 1
            remaining.remove(code)

    total = len(expected_codes)
    extra = len(remaining)
    accuracy = matched / total if total > 0 else 0
    return {"matched": matched, "total": total, "extra": extra, "accuracy": accuracy}


def score_rooms(actual, expected):
    """Score room name recognition."""
    expected_names = {r["name"] for r in expected}
    actual_names = {r["name"] for r in actual}
    matched = len(expected_names & actual_names)
    total = len(expected_names)
    accuracy = matched / total if total > 0 else 0
    return {"matched": matched, "total": total, "accuracy": accuracy}


def score_full(actual, expected):
    """Full recognition scoring report.

    Args:
        actual: Recognition result from API.
        expected: Ground truth data.
    Returns:
        dict with per-category scores and overall accuracy.
    """
    grids = expected.get("grids", {})

    grid_score = score_grids(
        actual.get("grids", {}), expected.get("grids", {}),
    )
    wall_score = score_walls(
        actual.get("walls", []), expected.get("walls", []), grids,
    )
    door_score = score_openings(
        actual.get("doors", []), expected.get("doors", []),
    )
    window_score = score_openings(
        actual.get("windows", []), expected.get("windows", []),
    )
    room_score = score_rooms(
        actual.get("rooms", []), expected.get("rooms", []),
    )

    total_items = (
        grid_score["total"] + wall_score["total"] +
        door_score["total"] + window_score["total"] + room_score["total"]
    )
    total_matched = (
        grid_score["matched"] + wall_score["matched"] +
        door_score["matched"] + window_score["matched"] + room_score["matched"]
    )
    overall = total_matched / total_items if total_items > 0 else 0

    return {
        "grids": grid_score,
        "walls": wall_score,
        "doors": door_score,
        "windows": window_score,
        "rooms": room_score,
        "overall": {"matched": total_matched, "total": total_items, "accuracy": overall},
    }


def format_score_report(scores):
    """Format scores into a readable report."""
    lines = [u"=== 识别准确率报告 ===", ""]
    for category in ("grids", "walls", "doors", "windows", "rooms"):
        s = scores[category]
        pct = s["accuracy"] * 100
        lines.append(u"  {:<8s}: {}/{} ({:.0f}%)".format(
            category, s["matched"], s["total"], pct,
        ))
    o = scores["overall"]
    lines.append("")
    lines.append(u"  OVERALL : {}/{} ({:.0f}%)".format(
        o["matched"], o["total"], o["accuracy"] * 100,
    ))
    return "\n".join(lines)


def _points_close(p1, p2, tolerance):
    """Check if two (x, y) points are within tolerance."""
    return abs(p1[0] - p2[0]) <= tolerance and abs(p1[1] - p2[1]) <= tolerance


# ──────────────────────────────────────────────
# Tests: Ground truth validation
# ──────────────────────────────────────────────

class TestGroundTruthValidity:
    def test_file_exists(self):
        assert EXPECTED_PATH.exists()

    def test_schema_step1_valid(self, ground_truth):
        errors = validate_step1(ground_truth)
        assert errors == [], "Step1 errors: {}".format(errors)

    def test_schema_step2_valid(self, ground_truth):
        errors = validate_step2(ground_truth)
        assert errors == [], "Step2 errors: {}".format(errors)

    def test_schema_step3_valid(self, ground_truth):
        errors = validate_step3(ground_truth)
        assert errors == [], "Step3 errors: {}".format(errors)

    def test_full_schema_valid(self, ground_truth):
        errors = validate_full(ground_truth)
        assert errors == [], "Full errors: {}".format(errors)


class TestGroundTruthContent:
    def test_has_5_x_grids(self, ground_truth):
        assert len(ground_truth["grids"]["x"]) == 5

    def test_has_5_y_grids(self, ground_truth):
        assert len(ground_truth["grids"]["y"]) == 5

    def test_grid_total_x_span(self, ground_truth):
        x_grids = ground_truth["grids"]["x"]
        assert x_grids[-1]["distance"] == 11400

    def test_grid_total_y_span(self, ground_truth):
        y_grids = ground_truth["grids"]["y"]
        assert y_grids[-1]["distance"] == 9900

    def test_has_8_walls(self, ground_truth):
        assert len(ground_truth["walls"]) == 8

    def test_has_4_exterior_walls(self, ground_truth):
        ext = [w for w in ground_truth["walls"] if w["type"] == "exterior"]
        assert len(ext) == 4

    def test_has_5_doors(self, ground_truth):
        assert len(ground_truth["doors"]) == 5

    def test_has_7_windows(self, ground_truth):
        assert len(ground_truth["windows"]) == 7

    def test_has_4_rooms(self, ground_truth):
        assert len(ground_truth["rooms"]) == 4
        names = {r["name"] for r in ground_truth["rooms"]}
        assert names == {"车库", "客厅", "厨房", "卫生间"}


class TestGroundTruthCoordinates:
    def test_convert_all_succeeds(self, ground_truth):
        result = convert_all(ground_truth)
        assert "walls" in result
        assert len(result["walls"]) == 8

    def test_south_wall_absolute(self, ground_truth):
        result = convert_all(ground_truth)
        w1 = result["walls"][0]
        assert w1["start_x"] == 0
        assert w1["start_y"] == 0
        assert w1["end_x"] == 11400
        assert w1["end_y"] == 0

    def test_east_wall_absolute(self, ground_truth):
        result = convert_all(ground_truth)
        w2 = result["walls"][1]
        assert w2["start_x"] == 11400
        assert w2["end_y"] == 9900


class TestGroundTruthBuildPlan:
    def test_generates_valid_plan(self, ground_truth):
        absolute = convert_all(ground_truth)
        plan = generate_build_plan(absolute)
        assert len(plan) > 0

    def test_plan_step_count(self, ground_truth):
        absolute = convert_all(ground_truth)
        plan = generate_build_plan(absolute)
        # 1 grid + 1 level + 8 walls + 5 doors + 7 windows = 22
        assert len(plan) == 22

    def test_plan_preview(self, ground_truth):
        absolute = convert_all(ground_truth)
        plan = generate_build_plan(absolute)
        preview = preview_build_plan(plan)
        assert u"22 步" in preview


# ──────────────────────────────────────────────
# Tests: Scoring functions
# ──────────────────────────────────────────────

class TestScoringFunctions:
    def test_perfect_score_against_self(self, ground_truth):
        scores = score_full(ground_truth, ground_truth)
        assert scores["overall"]["accuracy"] == 1.0

    def test_grid_score_perfect(self, ground_truth):
        s = score_grids(ground_truth["grids"], ground_truth["grids"])
        assert s["accuracy"] == 1.0
        assert s["matched"] == 10  # 5 x + 5 y

    def test_grid_score_with_missing(self, ground_truth):
        partial = {"x": ground_truth["grids"]["x"][:3], "y": ground_truth["grids"]["y"]}
        s = score_grids(partial, ground_truth["grids"])
        assert s["matched"] == 8  # 3 x + 5 y
        assert s["total"] == 10

    def test_grid_score_with_wrong_distance(self, ground_truth):
        wrong = {"x": [{"name": "1", "distance": 999}], "y": []}
        s = score_grids(wrong, ground_truth["grids"])
        assert s["matched"] == 0  # 999 vs 0, diff > 100mm

    def test_wall_score_perfect(self, ground_truth):
        grids = ground_truth["grids"]
        s = score_walls(ground_truth["walls"], ground_truth["walls"], grids)
        assert s["accuracy"] == 1.0

    def test_opening_score_perfect(self, ground_truth):
        s = score_openings(ground_truth["doors"], ground_truth["doors"])
        assert s["accuracy"] == 1.0
        assert s["extra"] == 0

    def test_opening_score_partial(self):
        expected = [{"code": "M0924"}, {"code": "M1527"}, {"code": "C0918"}]
        actual = [{"code": "M0924"}, {"code": "C0918"}]
        s = score_openings(actual, expected)
        assert s["matched"] == 2
        assert s["total"] == 3

    def test_room_score(self, ground_truth):
        s = score_rooms(ground_truth["rooms"], ground_truth["rooms"])
        assert s["accuracy"] == 1.0

    def test_format_report(self, ground_truth):
        scores = score_full(ground_truth, ground_truth)
        report = format_score_report(scores)
        assert "100%" in report
        assert "OVERALL" in report
