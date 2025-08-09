"""
Tests for partial matching functionality in the ModelEvaluator.

This module tests the is_partial_match method to ensure it correctly handles
various types of entity matching scenarios.
"""

import pytest

from sec_doc_tool.text_utils import PartialMatcher

# Test data organized by scenario type
# Format: (predicted, expected, expected_match, optional_threshold)

EXACT_MATCH_CASES = [
    ("American Growth Fund", "American Growth Fund", True),
    ("AMERICAN GROWTH FUND", "american growth fund", True),
    ("American Growth Fund", "AMERICAN GROWTH FUND", True),
    (" American Growth Fund ", "American Growth Fund", True),
    ("American  Growth  Fund", "American Growth Fund", True),
]

SUBSTRING_MATCH_CASES = [
    ("Insight Fund", "Morgan Stanley Insight Fund", True),
    ("INSIGHT FUND", "Morgan Stanley Insight Fund", True),
    ("Global Fund", "Leuthold Global Fund", True),
    ("Growth Fund", "American Growth Fund", True),
    ("Leuthold Global Fund", "Global Fund", True),
    ("American Growth Fund", "Growth Fund", True),
    ("American", "American Growth Fund", True),
    ("Fund", "American Growth Fund", True),
    ("Technology Fund", "Healthcare Fund", False),
    ("Bond Fund", "Equity Fund", False),
]

TOKEN_OVERLAP_CASES = [
    # (predicted, expected, expected_match, threshold)
    ("American Growth Fund", "American Growth Mutual Fund", True, 0.6),  # 75% overlap
    ("American Growth", "American International Fund", False, 0.6),  # 50% overlap
    ("Technology Fund", "Healthcare Bond Fund", False, 0.6),  # 20% overlap
    ("American Fund", "International Fund", True, 0.3),  # 33% overlap, low threshold
    ("American Fund", "International Fund", False, 0.8),  # 33% overlap, high threshold
    ("Bond Fund", "Equity Fund", False, 0.6),  # 33% overlap
    ("Bond Fund", "Equity Fund", True, 0.3),  # 33% overlap, low threshold
]

EDGE_CASES = [
    ("", "American Fund", False),
    ("American Fund", "", False),
    ("", "", False),
    ("   ", "American Fund", False),
    ("American Fund", "   ", False),
    ("A", "American Fund", True),  # Substring match
    ("A", "A", True),
]

SPECIAL_CHARACTER_CASES = [
    ("Fund 2030", "Target Date Fund 2030", True),  # Substring
    ("500 Index Fund", "S&P 500 Index Fund", True),  # Substring
    ("S&P Fund", "S&P 500 Index Fund", True, 0.5),  # 50% token overlap
    ("T. Rowe Price", "T. Rowe Price Growth Fund", True),  # Substring
]

REAL_WORLD_ABBREVIATION_CASES = [
    ("Global Fund", "Leuthold Global Fund", True),
    ("Growth Fund", "American Century Growth Fund", True),
    ("Value Fund", "Vanguard Value Fund", True),
    ("International Fund", "Fidelity International Fund", True),
]

REAL_WORLD_TYPE_VARIATION_CASES = [
    ("American Growth Fund", "American Growth Mutual Fund", True),
    ("Bond Index Fund", "Bond Index Mutual Fund", True),
    ("Money Market Fund", "Prime Money Market Fund", True),
]

REAL_WORLD_COMPANY_VARIATION_CASES = [
    # These need lower thresholds due to token overlap ratios
    ("Vanguard 500", "Vanguard S&P 500 Index Fund", True, 0.4),  # 40% overlap
    ("Fidelity Growth", "Fidelity Blue Chip Growth Fund", True, 0.4),  # 40% overlap
]

NON_MATCHING_FUND_CASES = [
    ("Technology Fund", "Healthcare Fund", False),
    ("International Bond", "Domestic Equity", False),
    ("Growth Fund", "Value Fund", False),
    ("Small Cap", "Large Cap", False),
]

THRESHOLD_SENSITIVITY_CASES = [
    # (predicted, expected, thresholds_and_expected_results)
    (
        "American Growth",
        "American International Fund",
        [
            (0.2, True),  # 25% overlap
            (0.25, True),  # 25% overlap
            (0.3, False),  # 25% overlap
        ],
    ),
    (
        "Growth Equity",
        "Growth International Bond",
        [
            (0.2, True),  # 25% overlap
            (0.6, False),  # 25% overlap with default threshold
        ],
    ),
]


@pytest.fixture
def partial_matcher():
    """Create a PartialMatcher instance for testing."""
    return PartialMatcher()


class TestExactMatching:
    """Test cases for exact matching scenarios."""

    def test_exact_matching_cases(self, partial_matcher):
        """Test all exact matching scenarios."""
        for predicted, expected, should_match in EXACT_MATCH_CASES:
            result = partial_matcher.is_match(predicted, expected)
            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )


class TestSubstringMatching:
    """Test cases for substring matching scenarios."""

    def test_substring_matching_cases(self, partial_matcher):
        """Test all substring matching scenarios."""
        for predicted, expected, should_match in SUBSTRING_MATCH_CASES:
            result = partial_matcher.is_match(predicted, expected)
            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )


class TestTokenOverlapMatching:
    """Test cases for token overlap matching scenarios."""

    def test_token_overlap_cases(self, partial_matcher):
        """Test all token overlap scenarios."""
        for case in TOKEN_OVERLAP_CASES:
            predicted, expected, should_match, threshold = case
            result = partial_matcher.is_match(predicted, expected, threshold=threshold)

            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""

    def test_edge_cases(self, partial_matcher):
        """Test all edge cases."""
        for predicted, expected, should_match in EDGE_CASES:
            result = partial_matcher.is_match(predicted, expected)
            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )

    def test_none_values(self, partial_matcher):
        """Test handling of None values."""
        assert not partial_matcher.is_match(None, "American Fund")
        assert not partial_matcher.is_match("American Fund", None)
        assert not partial_matcher.is_match(None, None)

    def test_special_character_cases(self, partial_matcher):
        """Test special character scenarios."""
        for case in SPECIAL_CHARACTER_CASES:
            if len(case) == 4:
                predicted, expected, should_match, threshold = case
                result = partial_matcher.is_match(
                    predicted, expected, threshold=threshold
                )
            else:
                predicted, expected, should_match = case
                result = partial_matcher.is_match(predicted, expected)

            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )


class TestRealWorldScenarios:
    """Test cases based on real-world fund name variations."""

    def test_common_fund_abbreviations(self, partial_matcher):
        """Test common fund name abbreviations."""
        for predicted, expected, should_match in REAL_WORLD_ABBREVIATION_CASES:
            result = partial_matcher.is_match(predicted, expected)
            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )

    def test_fund_type_variations(self, partial_matcher):
        """Test variations in fund type descriptors."""
        for predicted, expected, should_match in REAL_WORLD_TYPE_VARIATION_CASES:
            result = partial_matcher.is_match(predicted, expected)
            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )

    def test_company_name_variations(self, partial_matcher):
        """Test fund names with company name variations."""
        for case in REAL_WORLD_COMPANY_VARIATION_CASES:
            predicted, expected, should_match, threshold = case
            result = partial_matcher.is_match(predicted, expected, threshold=threshold)
            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' with threshold {threshold} "
                f"(expected {should_match}, got {result})"
            )

    def test_non_matching_funds(self, partial_matcher):
        """Test fund names that should not match."""
        for predicted, expected, should_match in NON_MATCHING_FUND_CASES:
            result = partial_matcher.is_match(predicted, expected)
            assert result == should_match, (
                f"Failed for: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )


class TestThresholdSensitivity:
    """Test cases for threshold sensitivity."""

    def test_threshold_sensitivity_cases(self, partial_matcher):
        """Test threshold sensitivity scenarios."""
        for predicted, expected, threshold_tests in THRESHOLD_SENSITIVITY_CASES:
            for threshold, should_match in threshold_tests:
                result = partial_matcher.is_match(
                    predicted, expected, threshold=threshold
                )
                assert result == should_match, (
                    f"Failed: '{predicted}' vs '{expected}' with threshold {threshold} "
                    f"(expected {should_match}, got {result})"
                )
