"""
Test for text normalization functionality.

Tests the _normalize_entity_text method to ensure it properly cleans
formatting artifacts commonly found in SEC document text.
"""

import pytest

from sec_doc_tool.text_utils import PartialMatcher, TextNormalizer


@pytest.fixture
def text_normalizer():
    """Create a TextNormalizer instance for testing."""
    return TextNormalizer()


@pytest.fixture
def partial_matcher():
    """Create a PartialMatcher instance for testing."""
    return PartialMatcher()


class TestTextNormalization:
    """Test cases for text normalization functionality."""

    def test_basic_normalization(self, text_normalizer):
        """Test basic case conversion and whitespace handling."""
        test_cases = [
            ("American Growth Fund", "american growth fund"),
            ("AMERICAN GROWTH FUND", "american growth fund"),
            ("  American Growth Fund  ", "american growth fund"),
            ("American  Growth  Fund", "american growth fund"),
        ]

        for input_text, expected in test_cases:
            result = text_normalizer.normalize(input_text)
            assert result == expected, (
                f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
            )

    def test_newline_and_tab_handling(self, text_normalizer):
        """Test removal of newlines and tabs."""
        test_cases = [
            ("American\nGrowth Fund", "american growth fund"),
            ("American\r\nGrowth Fund", "american growth fund"),
            ("American\tGrowth\tFund", "american growth fund"),
            ("American\n\r\tGrowth Fund", "american growth fund"),
            ("American\n\nGrowth\n\nFund", "american growth fund"),
        ]

        for input_text, expected in test_cases:
            result = text_normalizer.normalize(input_text)
            assert result == expected, (
                f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
            )

    def test_punctuation_and_special_characters(self, text_normalizer):
        """Test handling of punctuation and special characters."""
        test_cases = [
            # Keep important characters
            ("S&P 500 Fund", "s&p 500 fund"),
            ("T. Rowe Price", "t. rowe price"),
            ("American Growth Fund-A", "american growth fund-a"),
            ("Investor's Fund", "investor's fund"),
            # Remove unwanted punctuation
            ("American Growth Fund!", "american growth fund"),
            ("American, Growth Fund", "american growth fund"),
            ("American (Growth) Fund", "american growth fund"),
            ("American [Growth] Fund", "american growth fund"),
            ("American {Growth} Fund", "american growth fund"),
            ("American Growth Fund?", "american growth fund"),
            ("American Growth Fund;", "american growth fund"),
            ("American Growth Fund:", "american growth fund"),
            ('American"Growth"Fund', "american growth fund"),
        ]

        for input_text, expected in test_cases:
            result = text_normalizer.normalize(input_text)
            assert result == expected, (
                f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
            )

    def test_unicode_artifacts(self, text_normalizer):
        """Test handling of Unicode artifacts from PDF extraction."""
        test_cases = [
            # Non-breaking spaces and other Unicode whitespace
            ("American\u00a0Growth Fund", "american growth fund"),
            ("American\u2003Growth Fund", "american growth fund"),  # Em space
            ("American\u2009Growth Fund", "american growth fund"),  # Thin space
            # Common Unicode punctuation (converted to regular equivalents)
            ("American\u2013Growth Fund", "american-growth fund"),  # En dash -> hyphen
            ("American\u2014Growth Fund", "american-growth fund"),  # Em dash -> hyphen
            ("American\u201cGrowth\u201d Fund", "american growth fund"),  # Curly quotes
            (
                "American\u2018Growth\u2019 Fund",
                "american growth fund",
            ),  # Single curly quotes
            # Bullet points and list markers
            ("• American Growth Fund", "american growth fund"),
            ("▪ American Growth Fund", "american growth fund"),
            ("○ American Growth Fund", "american growth fund"),
        ]

        for input_text, expected in test_cases:
            result = text_normalizer.normalize(input_text)
            assert result == expected, (
                f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
            )

    def test_multiple_consecutive_spaces(self, text_normalizer):
        """Test normalization of multiple consecutive spaces."""
        test_cases = [
            ("American     Growth     Fund", "american growth fund"),
            ("American\t\t\tGrowth Fund", "american growth fund"),
            ("American \n \r \t Growth Fund", "american growth fund"),
            ("  American   Growth   Fund  ", "american growth fund"),
        ]

        for input_text, expected in test_cases:
            result = text_normalizer.normalize(input_text)
            assert result == expected, (
                f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
            )

    def test_edge_cases(self, text_normalizer):
        """Test edge cases and error conditions."""
        test_cases = [
            ("", ""),
            (None, ""),
            ("   ", ""),
            ("\n\r\t", ""),
            ("!@#$%^&*()", "&"),  # & is preserved per regex
            ("123", "123"),
            ("Fund 2030", "fund 2030"),
            ("A", "a"),
        ]

        for input_text, expected in test_cases:
            result = text_normalizer.normalize(input_text)
            assert result == expected, (
                f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
            )

    def test_real_world_sec_artifacts(self, text_normalizer):
        """
        Test with realistic SEC document text artifacts using the
        clean_sec_artifacts method.
        """
        test_cases = [
            # Common SEC filing artifacts
            ("American\nGrowth\nFund\n", "american growth fund"),
            ("American Growth Fund™", "american growth fund"),
            ("American Growth Fund®", "american growth fund"),
            ("American Growth Fund©", "american growth fund"),
            ("American Growth Fund\x00", "american growth fund"),  # Null byte
            (
                "American Growth Fund\ufffd",
                "american growth fund",
            ),  # Replacement character
            # Table artifacts
            ("American|Growth|Fund", "american growth fund"),
            ("American\tGrowth\tFund\t$1,000", "american growth fund 1 000"),
            # Mixed artifacts
            ("  American\n\r\tGrowth   Fund™®©  \n", "american growth fund"),
            ("【American】Growth〖Fund〗", "american growth fund"),
        ]

        for input_text, expected in test_cases:
            result = text_normalizer.clean_sec_artifacts(input_text)
            assert result == expected, (
                f"Input: '{input_text}', Expected: '{expected}', Got: '{result}'"
            )

    def test_partial_matching_with_normalization(self, partial_matcher):
        """Test that partial matching works correctly with normalized text."""
        # Test cases where normalization enables proper matching
        test_cases = [
            # Newlines and formatting should not prevent matches
            ("American\nGrowth Fund", "American Growth Fund", True),
            ("American Growth Fund!", "American Growth Fund", True),
            ("American  Growth  Fund", "American Growth Fund", True),
            # Unicode artifacts should not prevent matches
            (
                "American\u2013Growth Fund",
                "American-Growth Fund",
                True,
            ),  # En dash vs hyphen
            (
                "American\u201cGrowth\u201d Fund",
                "American Growth Fund",
                True,
            ),  # Quotes removed
            # Should still work for partial matches
            (
                "Growth Fund",
                "American\nGrowth\nFund",
                True,
            ),  # Substring after normalization
        ]

        for predicted, expected, should_match in test_cases:
            result = partial_matcher.is_match(predicted, expected)
            assert result == should_match, (
                f"Partial match failed: '{predicted}' vs '{expected}' "
                f"(expected {should_match}, got {result})"
            )
