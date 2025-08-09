"""
Partial matching utilities for fund name comparison.

This module provides fuzzy matching functionality for comparing fund names
with support for substring matching and token overlap analysis.
"""

from typing import Optional

from .text_normalizer import TextNormalizer


class PartialMatcher:
    """
    Partial matching utility for comparing fund names.

    Supports multiple matching strategies:
    - Exact matching (normalized)
    - Substring matching (one contains the other)
    - Token overlap matching (Jaccard similarity)
    """

    def __init__(
        self, threshold: float = 0.6, text_normalizer: Optional[TextNormalizer] = None
    ):
        """
        Initialize the partial matcher.

        Args:
            threshold: Minimum token overlap ratio for match (0.0 to 1.0)
            text_normalizer: TextNormalizer instance (creates new one if not provided)
        """
        self.threshold = threshold
        self.text_normalizer = text_normalizer or TextNormalizer()

    def is_match(
        self, predicted: str, expected: str, threshold: Optional[float] = None
    ) -> bool:
        """
        Check if a predicted entity partially matches an expected entity.

        Uses both substring matching and token overlap to determine if entities match.

        Args:
            predicted: Predicted entity text
            expected: Expected entity text
            threshold: Override default threshold for this comparison

        Returns:
            True if entities are considered a match, False otherwise
        """
        if not predicted or not expected:
            return False

        # Use provided threshold or instance default
        match_threshold = threshold if threshold is not None else self.threshold

        # Normalize both texts for comparison
        predicted_normalized = self.text_normalizer.normalize(predicted)
        expected_normalized = self.text_normalizer.normalize(expected)

        # Check if strings are empty after normalization
        if not predicted_normalized or not expected_normalized:
            return False

        # Exact match
        if predicted_normalized == expected_normalized:
            return True

        # Substring check - if one is contained in the other
        if (
            predicted_normalized in expected_normalized
            or expected_normalized in predicted_normalized
        ):
            return True

        # Token overlap check
        pred_tokens = set(predicted_normalized.split())
        exp_tokens = set(expected_normalized.split())

        # Avoid division by zero
        if not pred_tokens or not exp_tokens:
            return False

        # Calculate Jaccard similarity (intersection over union)
        overlap_ratio = len(pred_tokens & exp_tokens) / len(pred_tokens | exp_tokens)
        return overlap_ratio >= match_threshold

    def get_match_score(self, predicted: str, expected: str) -> float:
        """
        Get the match score between two entity texts.

        Returns a score from 0.0 (no match) to 1.0 (perfect match).

        Args:
            predicted: Predicted entity text
            expected: Expected entity text

        Returns:
            Match score between 0.0 and 1.0
        """
        if not predicted or not expected:
            return 0.0

        # Normalize both texts for comparison
        predicted_normalized = self.text_normalizer.normalize(predicted)
        expected_normalized = self.text_normalizer.normalize(expected)

        # Check if strings are empty after normalization
        if not predicted_normalized or not expected_normalized:
            return 0.0

        # Exact match
        if predicted_normalized == expected_normalized:
            return 1.0

        # Substring match gets high score
        if (
            predicted_normalized in expected_normalized
            or expected_normalized in predicted_normalized
        ):
            # Score based on length ratio (longer substring = higher score)
            min_len = min(len(predicted_normalized), len(expected_normalized))
            max_len = max(len(predicted_normalized), len(expected_normalized))
            return 0.8 + 0.2 * (min_len / max_len)  # 0.8-1.0 range

        # Token overlap score
        pred_tokens = set(predicted_normalized.split())
        exp_tokens = set(expected_normalized.split())

        if not pred_tokens or not exp_tokens:
            return 0.0

        # Jaccard similarity
        jaccard_score = len(pred_tokens & exp_tokens) / len(pred_tokens | exp_tokens)
        return jaccard_score

    def get_match_type(self, predicted: str, expected: str) -> str:
        """
        Get the type of match between two entity texts.

        Args:
            predicted: Predicted entity text
            expected: Expected entity text

        Returns:
            Match type: "exact", "substring", "token_overlap", or "no_match"
        """
        if not predicted or not expected:
            return "no_match"

        # Normalize both texts for comparison
        predicted_normalized = self.text_normalizer.normalize(predicted)
        expected_normalized = self.text_normalizer.normalize(expected)

        if not predicted_normalized or not expected_normalized:
            return "no_match"

        # Check match types in order of preference
        if predicted_normalized == expected_normalized:
            return "exact"

        if (
            predicted_normalized in expected_normalized
            or expected_normalized in predicted_normalized
        ):
            return "substring"

        # Check token overlap
        pred_tokens = set(predicted_normalized.split())
        exp_tokens = set(expected_normalized.split())

        if pred_tokens and exp_tokens:
            overlap_ratio = len(pred_tokens & exp_tokens) / len(pred_tokens | exp_tokens)
            if overlap_ratio >= self.threshold:
                return "token_overlap"

        return "no_match"

    def find_best_match(
        self, predicted: str, candidates: list[str]
    ) -> tuple[Optional[str], float]:
        """
        Find the best matching candidate for a predicted entity.

        Args:
            predicted: Predicted entity text
            candidates: List of candidate entity texts to match against

        Returns:
            Tuple of (best_match, score) or (None, 0.0) if no match found
        """
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            score = self.get_match_score(predicted, candidate)
            if score > best_score and score >= self.threshold:
                best_match = candidate
                best_score = score

        return best_match, best_score

    def batch_match(
        self,
        predictions: list[str],
        expectations: list[str],
        threshold: Optional[float] = None,
    ) -> dict:
        """
        Perform batch matching between predictions and expectations.

        Args:
            predictions: List of predicted entity texts
            expectations: List of expected entity texts
            threshold: Override default threshold for this batch

        Returns:
            Dictionary with match results and statistics
        """
        match_threshold = threshold if threshold is not None else self.threshold

        matched_predictions = set()
        matched_expectations = set()
        matches = []

        for i, pred in enumerate(predictions):
            for j, exp in enumerate(expectations):
                if j not in matched_expectations and self.is_match(
                    pred, exp, match_threshold
                ):
                    matched_predictions.add(i)
                    matched_expectations.add(j)
                    matches.append(
                        {
                            "predicted": pred,
                            "expected": exp,
                            "score": self.get_match_score(pred, exp),
                            "type": self.get_match_type(pred, exp),
                        }
                    )
                    break

        return {
            "matches": matches,
            "true_positives": len(matches),
            "false_positives": len(predictions) - len(matched_predictions),
            "false_negatives": len(expectations) - len(matched_expectations),
            "matched_prediction_indices": matched_predictions,
            "matched_expectation_indices": matched_expectations,
        }
