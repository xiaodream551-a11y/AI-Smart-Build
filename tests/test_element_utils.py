# -*- coding: utf-8 -*-

import pytest

from engine.element_utils import (
    format_number,
    is_valid_element_id,
    looks_like_plain_numeric_text,
    normalize_numeric_text,
    to_text,
    try_parse_section_name,
)


# ============================================================
# to_text
# ============================================================

class TestToText:
    def test_none_returns_empty_string(self):
        assert to_text(None) == ""

    def test_string_value_returned_stripped(self):
        assert to_text("  hello  ") == "hello"

    def test_integer_converted_to_string(self):
        assert to_text(42) == "42"

    def test_float_converted_to_string(self):
        assert to_text(3.14) == "3.14"

    def test_empty_string_returns_empty(self):
        assert to_text("") == ""

    def test_whitespace_only_returns_empty(self):
        assert to_text("   ") == ""


# ============================================================
# looks_like_plain_numeric_text
# ============================================================

class TestLooksLikePlainNumericText:
    def test_integer_string(self):
        assert looks_like_plain_numeric_text("500") is True

    def test_decimal_string(self):
        assert looks_like_plain_numeric_text("3.14") is True

    def test_non_numeric_string(self):
        assert looks_like_plain_numeric_text("abc") is False

    def test_mixed_string(self):
        assert looks_like_plain_numeric_text("500x500") is False

    def test_empty_string(self):
        assert looks_like_plain_numeric_text("") is False

    def test_none_value(self):
        assert looks_like_plain_numeric_text(None) is False

    def test_integer_value(self):
        assert looks_like_plain_numeric_text(500) is True

    def test_negative_not_matched(self):
        assert looks_like_plain_numeric_text("-5") is False

    def test_trailing_dot_not_matched(self):
        assert looks_like_plain_numeric_text("5.") is False


# ============================================================
# normalize_numeric_text
# ============================================================

class TestNormalizeNumericText:
    def test_integer_string_stays_integer(self):
        assert normalize_numeric_text("500") == "500"

    def test_float_with_zero_decimal_becomes_integer(self):
        assert normalize_numeric_text("500.0") == "500"

    def test_float_with_nonzero_decimal_kept(self):
        assert normalize_numeric_text("3.14") == "3.14"

    def test_integer_input(self):
        assert normalize_numeric_text(42) == "42"

    def test_float_input_whole_number(self):
        assert normalize_numeric_text(300.0) == "300"


# ============================================================
# format_number
# ============================================================

class TestFormatNumber:
    def test_whole_number_returns_int_string(self):
        assert format_number(500.0) == "500"

    def test_near_whole_number_rounds_to_int(self):
        assert format_number(499.9999) == "500"

    def test_decimal_value_preserved(self):
        assert format_number(3.14) == "3.14"

    def test_trailing_zeros_stripped(self):
        assert format_number(2.100) == "2.1"

    def test_integer_input(self):
        assert format_number(300) == "300"

    def test_zero(self):
        assert format_number(0) == "0"

    def test_string_numeric_input(self):
        assert format_number("6000") == "6000"

    def test_small_fraction(self):
        result = format_number(0.001)
        assert result == "0.001"


# ============================================================
# is_valid_element_id
# ============================================================

class _FakeId:
    def __init__(self, value):
        self.IntegerValue = value


class TestIsValidElementId:
    def test_none_is_invalid(self):
        assert is_valid_element_id(None) is False

    def test_positive_id_is_valid(self):
        assert is_valid_element_id(_FakeId(1)) is True

    def test_zero_id_is_invalid(self):
        assert is_valid_element_id(_FakeId(0)) is False

    def test_negative_id_is_invalid(self):
        assert is_valid_element_id(_FakeId(-1)) is False

    def test_object_without_integer_value_is_invalid(self):
        assert is_valid_element_id(object()) is False

    def test_large_positive_id_is_valid(self):
        assert is_valid_element_id(_FakeId(999999)) is True


# ============================================================
# try_parse_section_name
# ============================================================

class TestTryParseSectionName:
    def test_standard_section(self):
        assert try_parse_section_name("500x500") == "500x500"

    def test_uppercase_x_separator(self):
        assert try_parse_section_name("300X600") == "300x600"

    def test_unicode_multiplication_sign(self):
        assert try_parse_section_name("300\u00d7600") == "300x600"

    def test_with_mm_suffix(self):
        assert try_parse_section_name("500x500mm") == "500x500"

    def test_with_MM_suffix(self):
        assert try_parse_section_name("300X600MM") == "300x600"

    def test_with_spaces(self):
        assert try_parse_section_name(" 500 x 500 ") == "500x500"

    def test_decimal_values(self):
        assert try_parse_section_name("300.5x600.0") == "300.5x600"

    def test_empty_string_returns_empty(self):
        assert try_parse_section_name("") == ""

    def test_none_returns_empty(self):
        assert try_parse_section_name(None) == ""

    def test_non_numeric_parts_returns_empty(self):
        assert try_parse_section_name("abcxdef") == ""

    def test_single_number_no_separator_returns_empty(self):
        assert try_parse_section_name("500") == ""

    def test_name_without_separator_returns_empty(self):
        assert try_parse_section_name("SomeTypeName") == ""
