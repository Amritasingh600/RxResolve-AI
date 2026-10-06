import pytest

from classifier import (
    ELIGIBILITY,
    INSUFFICIENT_INFO_MESSAGE,
    MISSING_INFO,
    NOT_COVERED,
    OTHER,
    PRIOR_AUTH,
    QUANTITY_LIMIT,
    REFILL_TOO_SOON,
    STEP_THERAPY,
    classify_rejection,
)


@pytest.mark.parametrize(
    "code, message, expected",
    [
        ("PA001", "Prior authorization required", PRIOR_AUTH),
        ("", "PA required for this product", PRIOR_AUTH),
        ("70", "Product/service not covered", NOT_COVERED),
        ("", "Non-formulary drug", NOT_COVERED),
        ("", "Quantity limit exceeded", QUANTITY_LIMIT),
        ("", "Maximum quantity is 60 per 30 days", QUANTITY_LIMIT),
        ("", "Refill too soon", REFILL_TOO_SOON),
        ("", "Step therapy required", STEP_THERAPY),
        ("65", "Patient not covered - coverage terminated", ELIGIBILITY),
        ("", "M/I Prescriber ID", MISSING_INFO),
    ],
)
def test_classifies_common_rejections(code, message, expected):
    assert classify_rejection(code, message).category == expected


def test_demo_prior_authorization_has_high_confidence():
    result = classify_rejection("PA001", "Prior authorization required")
    assert result.category == PRIOR_AUTH
    assert result.confidence >= 0.9
    assert result.confidence_label == "High"
    assert "PA001" in result.reason


def test_code_only_is_enough():
    result = classify_rejection("79", "")
    assert result.category == REFILL_TOO_SOON
    assert result.confidence_label == "High"


def test_unknown_message_requires_manual_review():
    result = classify_rejection("", "Claim could not be processed. Contact help desk.")
    assert result.category == OTHER
    assert result.insufficient_info is True
    assert result.reason == INSUFFICIENT_INFO_MESSAGE
    assert result.confidence_label == "Low"


def test_empty_input_does_not_crash():
    result = classify_rejection(None, None)
    assert result.category == OTHER


def test_prior_auth_wins_over_generic_missing_keyword():
    result = classify_rejection("75", "Prior authorization required. Missing clinical documentation.")
    assert result.category == PRIOR_AUTH
