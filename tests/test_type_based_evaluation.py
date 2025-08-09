"""
Test for type-based evaluation algorithm.

This test verifies that the new type-based evaluation correctly handles
duplicate entity predictions and focuses on unique fund names rather than positions.
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


def test_type_based_evaluation_with_duplicates(text_normalizer, partial_matcher):
    """Test that duplicate predictions are handled correctly in type-based evaluation."""

    # Mock predicted entities (same fund mentioned multiple times)
    predicted_entity_texts = [
        "American Growth Fund",
        "American Growth Fund",  # duplicate
        "Global Fund",  # False positive
        "Technology Fund",
    ]

    # Mock expected entities (unique fund names)
    expected_entity_texts = [
        "American Growth Fund",
        "Leuthold Global Fund",  # Partial match
        "Value Fund",  # Missed
    ]

    # Simulate the type-based evaluation logic
    # Convert to unique entity sets (case-insensitive)
    predicted_unique = set()
    expected_unique = set()

    for entry in predicted_entity_texts:
        predicted_unique.add(text_normalizer.normalize(entry))

    for entry in expected_entity_texts:
        expected_unique.add(text_normalizer.normalize(entry))

    # Use partial matching to find overlaps between unique sets
    matched_predictions = set()
    matched_expectations = set()

    matcher = PartialMatcher()
    for pred_text in predicted_unique:
        for exp_text in expected_unique:
            if exp_text not in matched_expectations and matcher.is_match(
                pred_text, exp_text
            ):
                matched_predictions.add(pred_text)
                matched_expectations.add(exp_text)
                break

    true_positives = len(matched_predictions)
    false_positives = len(predicted_unique) - len(matched_predictions)
    false_negatives = len(expected_unique) - len(matched_expectations)

    # Verify results
    print(f"Predicted unique: {predicted_unique}")
    print(f"Expected unique: {expected_unique}")
    print(f"Matched predictions: {matched_predictions}")
    print(f"Matched expectations: {matched_expectations}")

    # Expected results:
    # - predicted_unique: {"american growth fund", "global fund", "technology fund"} (3 unique) # noqa E501
    # - expected_unique: {"american growth fund", "leuthold global fund", "value fund"} (3 unique) # noqa E501
    # - matched_predictions: {"american growth fund", "global fund"} (2 matches)
    # - matched_expectations: {"american growth fund", "leuthold global fund"} (2 matches)
    # - TP=2, FP=1, FN=1

    assert len(predicted_unique) == 3, (
        f"Expected 3 unique predictions, got {len(predicted_unique)}"
    )
    assert len(expected_unique) == 3, (
        f"Expected 3 unique expectations, got {len(expected_unique)}"
    )
    assert true_positives == 2, f"Expected 2 TP, got {true_positives}"
    assert false_positives == 1, f"Expected 1 FP, got {false_positives}"
    assert false_negatives == 1, f"Expected 1 FN, got {false_negatives}"

    # Verify precision and recall
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )

    expected_precision = 2 / 3  # 2 correct out of 3 unique predictions
    expected_recall = 2 / 3  # 2 found out of 3 unique expectations

    assert abs(precision - expected_precision) < 0.001, (
        f"Expected precision {expected_precision}, got {precision}"
    )
    assert abs(recall - expected_recall) < 0.001, (
        f"Expected recall {expected_recall}, got {recall}"
    )


def test_no_duplicates_same_result(text_normalizer, partial_matcher):
    """Test that evaluation works correctly when there are no duplicate predictions."""

    # Mock predicted entities (no duplicates)
    predicted_entity_texts = [
        "American Growth Fund",
        "Technology Fund",
    ]

    # Mock expected entities
    expected_entity_texts = [
        "American Growth Fund",
    ]

    def mock_is_partial_match(pred, exp):
        return text_normalizer.normalize(pred) == text_normalizer.normalize(exp)

    # Simulate evaluation logic
    predicted_unique = {text_normalizer.normalize(ent) for ent in predicted_entity_texts}
    expected_unique = {text_normalizer.normalize(ent) for ent in expected_entity_texts}

    matched_predictions = set()
    matched_expectations = set()

    for pred_text in predicted_unique:
        for exp_text in expected_unique:
            if exp_text not in matched_expectations and mock_is_partial_match(
                pred_text, exp_text
            ):
                matched_predictions.add(pred_text)
                matched_expectations.add(exp_text)
                break

    true_positives = len(matched_predictions)
    false_positives = len(predicted_unique) - len(matched_predictions)
    false_negatives = len(expected_unique) - len(matched_expectations)

    # Expected: TP=1, FP=1, FN=0
    assert true_positives == 1
    assert false_positives == 1
    assert false_negatives == 0
