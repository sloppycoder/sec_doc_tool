"""
Text normalization utilities for fund name processing.

This module provides text cleaning and normalization functionality
specifically designed for SEC document text processing.
"""

import re


class TextNormalizer:
    """
    Normalize text for fund name comparison and processing.

    Handles common SEC document artifacts including:
    - Newlines, tabs, and whitespace
    - Unicode artifacts from PDF extraction
    - Special characters and punctuation
    - Multiple consecutive spaces
    """

    def normalize(self, text: str) -> str:
        """
        Normalize entity text by cleaning formatting artifacts and
        non-alphanumeric characters.

        Common issues in SEC document text:
        - Newlines and whitespace artifacts
        - Punctuation and special characters
        - Unicode artifacts from PDF extraction
        - Multiple consecutive spaces

        Args:
            text: Raw entity text

        Returns:
            Normalized text suitable for comparison
        """
        if not text:
            return ""

        # Convert to lowercase
        normalized = text.lower()

        # Replace newlines and tabs with spaces
        normalized = re.sub(r"[\n\r\t]+", " ", normalized)

        # Convert common Unicode dashes to regular hyphens
        normalized = re.sub(r"[\u2013\u2014]", "-", normalized)  # En dash, Em dash

        # Remove common Unicode artifacts and special characters
        # Keep alphanumeric, spaces, periods, ampersands, hyphens, apostrophes
        normalized = re.sub(r"[^\w\s.&\-\']+", " ", normalized)

        # Normalize multiple spaces to single space
        normalized = re.sub(r"\s+", " ", normalized)

        # Strip leading/trailing whitespace
        normalized = normalized.strip()

        return normalized

    def clean_sec_artifacts(self, text: str) -> str:
        """
        Remove common SEC document artifacts from text.

        More aggressive cleaning for SEC-specific formatting issues.

        Args:
            text: Raw text with potential SEC artifacts

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        cleaned = text

        # Remove null bytes and replacement characters
        cleaned = cleaned.replace("\x00", "")  # Remove null bytes
        cleaned = cleaned.replace("\ufffd", "")  # Remove replacement characters

        # Remove trademark and copyright symbols
        cleaned = re.sub(r"[™®©]", "", cleaned)

        # Remove table separators
        cleaned = cleaned.replace("|", " ")

        # Remove bullet points and list markers
        cleaned = re.sub(r"[•▪○]", "", cleaned)

        # Remove Unicode brackets (replace with spaces)
        cleaned = re.sub(r"[【】〖〗]", " ", cleaned)

        return self.normalize(cleaned)

    def is_meaningful_text(self, text: str, min_length: int = 2) -> bool:
        """
        Check if normalized text is meaningful (not empty/whitespace after normalization).

        Args:
            text: Text to check
            min_length: Minimum length for meaningful text

        Returns:
            True if text is meaningful, False otherwise
        """
        normalized = self.normalize(text)
        return len(normalized) >= min_length
