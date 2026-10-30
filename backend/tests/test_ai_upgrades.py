import pytest
import numpy as np

from classifier import (
    CATEGORIES,
    ELIGIBILITY,
    MISSING_INFO,
    NOT_COVERED,
    OTHER,
    PRIOR_AUTH,
    QUANTITY_LIMIT,
    REFILL_TOO_SOON,
    STEP_THERAPY,
    classify_rejection,
    get_ml_classifier,
)
from policy_search import get_index, search_policies


def test_ml_classifier_predicts_all_categories_with_high_confidence():
    """Verify that the ML classifier predicts each medical rejection category with >70% confidence."""
    classifier = get_ml_classifier()
    
    test_cases = [
        ("This medication requires prior authorization before approval", PRIOR_AUTH),
        ("Prescription item is not covered on this formulary", NOT_COVERED),
        ("Quantity limit exceeded for 30 days supply", QUANTITY_LIMIT),
        ("Refill too soon, next available fill date is next week", REFILL_TOO_SOON),
        ("Step therapy required: trial of first-line preferred agent necessary", STEP_THERAPY),
        ("Patient coverage terminated, member not active on DOS", ELIGIBILITY),
        ("Missing or invalid prescriber NPI on claim submission", MISSING_INFO),
    ]
    
    for message, expected_cat in test_cases:
        cat, conf = classifier.predict_proba(message)
        assert cat == expected_cat, f"Expected {expected_cat} for '{message}', got {cat}"
        assert conf > 0.70, f"Expected confidence > 0.70 for '{message}', got {conf}"


def test_hybrid_classifier_uses_ml_above_70_percent():
    """Verify that when ML predicts category with >70% confidence, the hybrid classifier uses it."""
    result = classify_rejection("", "Prior authorization required for this specialty prescription")
    assert result.category == PRIOR_AUTH
    assert result.confidence > 0.70
    assert result.model_source in ("ml", "hybrid-ml-code")
    assert "machine learning" in result.reason.lower()


def test_hybrid_classifier_falls_back_to_rules_when_low_confidence():
    """Verify safety guardrail: when ML confidence is low or code-only, falls back to deterministic rules."""
    # When text is empty, code-only is evaluated deterministically
    result = classify_rejection("QL001", "")
    assert result.category == QUANTITY_LIMIT
    assert result.confidence >= 0.80
    assert result.model_source == "rule-guardrail"
    assert "QL001" in result.reason


def test_semantic_vector_search_cosine_similarity():
    """Verify semantic vector search embeds queries and calculates cosine similarity on policy chunks."""
    index = get_index()
    assert len(index.chunks) > 0
    assert len(index.embeddings) == len(index.chunks)
    assert isinstance(index.embeddings, np.ndarray)
    
    # Query for prior authorization
    results = search_policies("Clinical documentation requirements for prior authorization approval", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["source"] == "prior_authorization.txt"
    assert "Prior Authorization" in top["title"]
    assert 0.0 < top["score"] <= 1.0


def test_semantic_vector_search_step_therapy():
    """Verify semantic search retrieves step therapy policy for prerequisite trial queries."""
    results = search_policies("Prerequisite medication trial and first-line failure protocol", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top["source"] == "step_therapy.txt"
    assert "Step Therapy" in top["title"]
    assert top["score"] > 0
