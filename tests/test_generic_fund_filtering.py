"""
Test for generic fund filtering functionality.

Tests the _is_generic_fund_name method to ensure it correctly identifies
generic fund names that should be filtered from evaluation.
"""

import pytest

from sec_doc_tool.text_utils import GenericFundFilter, TextNormalizer


@pytest.fixture
def generic_filter():
    """Create a GenericFundFilter instance for testing."""
    return GenericFundFilter()


@pytest.fixture
def text_normalizer():
    """Create a TextNormalizer instance for testing."""
    return TextNormalizer()


class TestGenericFundDetection:
    """Test cases for generic fund name detection."""

    def test_basic_generic_patterns(self, generic_filter):
        """Test detection of basic generic fund patterns."""
        generic_names = [
            "money market fund",
            "bond fund",
            "equity fund",
            "stock fund",
            "mutual fund",
            "index fund",
            "growth fund",
            "value fund",
            "income fund",
            "dividend fund",
            "balanced fund",
        ]

        for name in generic_names:
            assert generic_filter.is_generic(name), f"Should be generic: '{name}'"
            # Test plural forms
            plural = name.replace(" fund", " funds")
            assert generic_filter.is_generic(plural), f"Should be generic: '{plural}'"

    def test_geographic_generic_patterns(self, generic_filter):
        """Test detection of geographic generic patterns."""
        generic_names = [
            "international fund",
            "global fund",
            "domestic fund",
            "foreign fund",
            "emerging market fund",
        ]

        for name in generic_names:
            assert generic_filter.is_generic(name), f"Should be generic: '{name}'"

    def test_size_based_generic_patterns(self, generic_filter):
        """Test detection of size-based generic patterns."""
        generic_names = [
            "large cap fund",
            "mid cap fund",
            "small cap fund",
        ]

        for name in generic_names:
            assert generic_filter.is_generic(name), f"Should be generic: '{name}'"

    def test_sector_generic_patterns(self, generic_filter):
        """Test detection of sector-based generic patterns."""
        generic_names = [
            "sector fund",
            "industry fund",
            "technology fund",
            "healthcare fund",
            "financial fund",
            "energy fund",
        ]

        for name in generic_names:
            assert generic_filter.is_generic(name), f"Should be generic: '{name}'"

    def test_very_short_generic_terms(self, generic_filter):
        """Test detection of very short or minimal terms."""
        generic_names = [
            "fund",
            "funds",
            "the fund",
            "investment fund",
            "target date fund",
            "retirement fund",
        ]

        for name in generic_names:
            assert generic_filter.is_generic(name), f"Should be generic: '{name}'"

    def test_specific_fund_names(self, generic_filter):
        """Test that specific fund names are NOT marked as generic."""
        specific_names = [
            "American Growth Fund",
            "Vanguard S&P 500 Index Fund",
            "Fidelity Blue Chip Growth Fund",
            "T. Rowe Price Growth Stock Fund",
            "Morgan Stanley Insight Fund",
            "Leuthold Global Fund",
            "American Century Growth Fund",
            "BlackRock Technology Fund",  # Has specific company name
            "JPMorgan Bond Fund",  # Has specific company name
            "Goldman Sachs Equity Fund",  # Has specific company name
        ]

        for name in specific_names:
            assert not generic_filter.is_generic(name), f"Should be specific: '{name}'"

    def test_case_insensitive_detection(self, generic_filter):
        """Test that detection works regardless of case."""
        test_cases = [
            "MONEY MARKET FUND",
            "Money Market Fund",
            "money market fund",
            "MoNeY mArKeT fUnD",
        ]

        for name in test_cases:
            assert generic_filter.is_generic(name), (
                f"Should be generic regardless of case: '{name}'"
            )

    def test_empty_and_edge_cases(self, generic_filter):
        """Test edge cases and empty inputs."""
        edge_cases = [
            "",
            None,
            "   ",
            "a",  # Too short
            "the",  # Too short + generic
        ]

        for case in edge_cases:
            assert generic_filter.is_generic(case), f"Should be generic: '{case}'"


class TestEvaluationWithFiltering:
    """Test the full evaluation process with generic fund filtering."""

    def test_evaluation_with_filtering_enabled(self, generic_filter, text_normalizer):
        """Test that generic funds are filtered during evaluation."""
        # Mock predicted entities including generic ones
        predicted_entity_texts = [
            "American Growth Fund",
            "money market fund",
            "bond fund",
            "Vanguard S&P 500",
        ]
        expected_entity_texts = [
            "American Growth Fund",
            "Vanguard S&P 500",
        ]

        # Simulate the filtering logic
        predicted_unique_raw = set()
        expected_unique = set()

        for entry in predicted_entity_texts:
            predicted_unique_raw.add(text_normalizer.normalize(entry))

        for entry in expected_entity_texts:
            expected_unique.add(text_normalizer.normalize(entry))

        # Apply filtering using the generic filter
        predicted_unique = generic_filter.filter_unique_predictions(predicted_unique_raw)

        # Verify filtering results
        assert len(predicted_unique_raw) == 4, (
            f"Expected 4 raw predictions, got {len(predicted_unique_raw)}"
        )
        assert len(predicted_unique) == 2, (
            f"Expected 2 filtered predictions, got {len(predicted_unique)}"
        )
        assert "money market fund" not in predicted_unique, (
            "Generic fund should be filtered"
        )
        assert "bond fund" not in predicted_unique, "Generic fund should be filtered"
        assert "american growth fund" in predicted_unique, "Specific fund should remain"
        assert "vanguard s&p 500" in predicted_unique, "Specific fund should remain"
