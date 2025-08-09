"""
Generic fund name filtering utilities.

This module provides functionality to identify and filter generic fund names
that are not specific enough for meaningful evaluation or analysis.
"""

import logging
from typing import List, Optional, Set

from .text_normalizer import TextNormalizer


class GenericFundFilter:
    """
    Filter for identifying generic (non-specific) fund names.

    Generic fund names are common fund types that appear frequently in financial
    documents but don't represent specific, named funds (e.g., "money market fund").
    """

    def __init__(
        self,
        custom_patterns: Optional[Set[str]] = None,
        text_normalizer: Optional[TextNormalizer] = None,
    ):
        """
        Initialize the generic fund filter.

        Args:
            custom_patterns: Custom set of generic fund patterns to use instead of default
            text_normalizer: TextNormalizer instance (creates new one if not provided)
        """
        self.text_normalizer = text_normalizer or TextNormalizer()
        self.generic_patterns = custom_patterns or self._get_default_patterns()

        # For tracking predictions to help maintain the generic list
        self._prediction_tracker: Set[str] = set()

    def _get_default_patterns(self) -> Set[str]:
        """Get the default set of generic fund name patterns."""
        return {
            # Basic fund types
            "money fund",
            "money market fund",
            "money market funds",
            "bond fund",
            "bond funds",
            "equity fund",
            "equity funds",
            "stock fund",
            "stock funds",
            "mutual fund",
            "mutual funds",
            "index fund",
            "index funds",
            "etf fund",
            "etf funds",
            "exchange traded fund",
            "exchange traded funds",
            # Investment styles
            "growth fund",
            "growth funds",
            "value fund",
            "value funds",
            "income fund",
            "income funds",
            "dividend fund",
            "dividend funds",
            "yield fund",
            "yield funds",
            "balanced fund",
            "balanced funds",
            # Geographic
            "international fund",
            "international funds",
            "global fund",
            "global funds",
            "domestic fund",
            "domestic funds",
            "foreign fund",
            "foreign funds",
            "emerging market fund",
            "emerging market funds",
            # Size-based
            "large cap fund",
            "large cap funds",
            "mid cap fund",
            "mid cap funds",
            "small cap fund",
            "small cap funds",
            # Sector (generic)
            "sector fund",
            "sector funds",
            "industry fund",
            "industry funds",
            "technology fund",
            "technology funds",
            "healthcare fund",
            "healthcare funds",
            "financial fund",
            "financial funds",
            "energy fund",
            "energy funds",
            # Time-based
            "target date fund",
            "target date funds",
            "retirement fund",
            "retirement funds",
            # Very generic
            "fund",
            "funds",
            "the fund",
            "the funds",
            "investment fund",
            "investment funds",
        }

    def is_generic(self, fund_name: str) -> bool:
        """
        Determine if a fund name is generic (non-specific).

        Args:
            fund_name: Fund name to evaluate

        Returns:
            True if the fund name is considered generic, False if specific
        """
        if not fund_name:
            return True

        normalized = self.text_normalizer.normalize(fund_name)
        if not normalized or len(normalized) <= 3:
            return True

        return normalized in self.generic_patterns

    def filter_predictions(self, predictions: List[str]) -> List[str]:
        """
        Filter out generic fund names from a list of predictions.

        Args:
            predictions: List of fund name predictions

        Returns:
            List of predictions with generic names removed
        """
        filtered = []
        for prediction in predictions:
            if not self.is_generic(prediction):
                filtered.append(prediction)

        return filtered

    def filter_unique_predictions(self, predictions: Set[str]) -> Set[str]:
        """
        Filter out generic fund names from a set of unique predictions.

        Args:
            predictions: Set of unique fund name predictions

        Returns:
            Set of predictions with generic names removed
        """
        return {pred for pred in predictions if not self.is_generic(pred)}

    def track_prediction(self, prediction: str) -> None:
        """
        Track a prediction for analysis and pattern building.

        This is useful for maintaining and updating the generic patterns list
        by collecting all predictions seen during evaluation.

        Args:
            prediction: Fund name prediction to track
        """
        normalized = self.text_normalizer.normalize(prediction)
        if normalized:
            self._prediction_tracker.add(normalized)

    def get_tracked_predictions(self) -> Set[str]:
        """
        Get all tracked predictions.

        Returns:
            Set of all normalized predictions that have been tracked
        """
        return self._prediction_tracker.copy()

    def save_tracked_predictions(self, output_path: str = "all_predictions.txt") -> None:
        """
        Save all tracked predictions to a file for analysis.

        Args:
            output_path: Path to save the predictions file
        """
        if self._prediction_tracker:
            sorted_predictions = sorted(self._prediction_tracker)
            with open(output_path, "w", encoding="utf-8") as f:
                for prediction in sorted_predictions:
                    f.write(f"{prediction}\n")
            logging.info(
                f"Saved {len(sorted_predictions)} unique predictions to {output_path}"
            )
        else:
            logging.warning("No predictions to save")

    def get_filter_stats(self, predictions: List[str]) -> dict:
        """
        Get statistics about filtering for a list of predictions.

        Args:
            predictions: List of fund name predictions

        Returns:
            Dictionary with filtering statistics
        """
        total = len(predictions)
        filtered = self.filter_predictions(predictions)
        generic_count = total - len(filtered)

        return {
            "total_predictions": total,
            "generic_filtered": generic_count,
            "specific_remaining": len(filtered),
            "filter_rate": generic_count / total if total > 0 else 0.0,
        }

    def add_generic_pattern(self, pattern: str) -> None:
        """
        Add a new generic pattern to the filter.

        Args:
            pattern: Normalized generic fund name pattern to add
        """
        normalized = self.text_normalizer.normalize(pattern)
        if normalized:
            self.generic_patterns.add(normalized)

    def remove_generic_pattern(self, pattern: str) -> bool:
        """
        Remove a generic pattern from the filter.

        Args:
            pattern: Pattern to remove

        Returns:
            True if pattern was removed, False if it wasn't found
        """
        normalized = self.text_normalizer.normalize(pattern)
        if normalized in self.generic_patterns:
            self.generic_patterns.remove(normalized)
            return True
        return False
