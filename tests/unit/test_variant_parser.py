# tests/unit/test_variant_parser.py

import pytest
from app.variant_parser import normalize_variant_for_vep

# `pytest.mark.parametrize` is a pytest feature that allows you to run the same
# test function with multiple different inputs and expected outputs. It's an
# efficient way to test many cases without writing repetitive code.
# The first argument is a string of comma-separated parameter names ("input_str,expected_output").
# The second argument is a list of tuples, where each tuple corresponds to one test case.
@pytest.mark.parametrize("input_str, expected_output", [
    # Test case 1: Valid rsID
    ("rs113488022", "rs113488022"),
    # Test case 2: Valid rsID with different casing
    ("RS123", "RS123"),
    # Test case 3: Valid chr:pos:ref:alt format
    ("7:140753336:A:T", "7:g.140753336A>T"),
    # Test case 4: Coordinate format with "chr" prefix
    ("chr17:7675088:C:T", "17:g.7675088C>T"),
    # Test case 5: Valid chr:posREF>ALT format
    ("12:25245350C>T", "12:g.25245350C>T"),
    # Test case 6: Valid full HGVS g. notation (should pass through)
    ("7:g.140753336A>T", "7:g.140753336A>T"),
    # Test case 7: Valid full HGVS c. notation (should pass through)
    ("NM_004333.6:c.1799T>A", "NM_004333.6:c.1799T>A"),
    # Test case 8: Invalid string
    ("abcde", None),
    # Test case 9: Incomplete coordinate format
    ("7:140753336", None),
    # Test case 10: Coordinate format with non-numeric position
    ("7:not_a_number:A:T", None),
    # Test case 11: Empty string input
    ("", None),
])
def test_normalize_variant_for_vep(input_str, expected_output):
    """
    Tests the normalize_variant_for_vep function with various inputs.
    `pytest` will run this function once for each tuple in the parametrize list,
    passing the values as `input_str` and `expected_output`.
    """
    # The `assert` statement is the core of a pytest test.
    # It checks if a condition is true. If it's false, the test fails.
    assert normalize_variant_for_vep(input_str) == expected_output

