"""
Text normalization utilities for fund name processing.

This module provides text cleaning and normalization functionality
specifically designed for SEC document text processing.
"""

import re
import unicodedata


class TextNormalizer:
    """
    Normalize text for fund name comparison and processing.

    Handles common SEC document artifacts including:
    - Newlines, tabs, and whitespace
    - Unicode artifacts from PDF extraction
    - Special characters and punctuation
    - Multiple consecutive spaces
    """

    def __init__(self):
        # Translation table for removing trademark and registered symbols
        chars_to_remove = "\u2122\u00ae"  # ™ ®
        self._translation_table = str.maketrans("", "", chars_to_remove)

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

    def is_meaningful_text(self, text: str, min_length: int = 3) -> bool:
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

    def sanitize_document_text(self, text: str) -> str:
        """
        Sanitize document text while preserving document structure.

        Similar to normalize() but preserves line breaks and is more
        suited for document chunking rather than entity comparison.

        Handles:
        - Unicode normalization (NFKC)
        - Unicode dashes and special symbols
        - Control characters
        - Whitespace normalization
        - Dollar sign formatting

        Args:
            text: Raw document text

        Returns:
            Sanitized text with preserved structure
        """
        if not text:
            return ""

        # 1. Normalize unicode (e.g. accented chars, homoglyphs)
        text = unicodedata.normalize("NFKC", text)

        # 2. Replace various Unicode dashes with ASCII hyphen (-)
        text = re.sub(r"[‐‑‒–—−]", "-", text)  # noqa: RUF001

        # 3. Remove trademark and registered symbols
        text = text.translate(self._translation_table)

        # 4. Remove invisible or control characters (except \n or \t)
        text = "".join(
            c for c in text if not unicodedata.category(c).startswith("C") or c in "\n\t"
        )

        # 5. Remove whitespace between dollar sign and number, e.g. "$ 100" → "$100"
        text = re.sub(r"\$\s+(?=\d)", "$", text)

        # 6. Normalize whitespace while preserving line structure
        text = re.sub(r"[ \t]+", " ", text)  # normalize horizontal whitespace
        text = re.sub(r"\s*\n\s*", "\n", text)  # remove spaces around line breaks
        text = re.sub(
            r"\n{3,}", "\n\n", text
        )  # collapse 3+ line breaks to double newlines
        text = text.strip()

        return text
