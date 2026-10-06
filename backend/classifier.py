"""
Rule-based rejection classifier.

This is the part of RxResolveAI that always works, with or without a local
LLM. It looks at two things:

1. The rejection code (e.g. "75" or the demo code "PA001").
2. Keywords / phrases in the rejection message (e.g. "prior authorization").

Each category gets a score. The highest score wins, and the confidence is
derived from how much evidence was found. When nothing matches, the case is
classified as "Other" with the message "Insufficient information — manual
review required."

The guidance text below is generic administrative guidance. It deliberately
does NOT describe any real payer's rules.
"""
from dataclasses import dataclass, field

PRIOR_AUTH = "Prior Authorization Required"
NOT_COVERED = "Drug Not Covered"
QUANTITY_LIMIT = "Quantity Limit"
REFILL_TOO_SOON = "Refill Too Soon"
STEP_THERAPY = "Step Therapy"
ELIGIBILITY = "Eligibility Problem"
MISSING_INFO = "Missing Information"
OTHER = "Other"

CATEGORIES = [
    PRIOR_AUTH,
    NOT_COVERED,
    QUANTITY_LIMIT,
    REFILL_TOO_SOON,
    STEP_THERAPY,
    ELIGIBILITY,
    MISSING_INFO,
    OTHER,
]

INSUFFICIENT_INFO_MESSAGE = "Insufficient information — manual review required."

# Rejection codes -> category.
# The "XX001" codes are demo codes used by the sample data. The numeric codes
# are commonly used NCPDP pharmacy reject codes.
REJECTION_CODE_MAP = {
    # Prior authorization
    "75": PRIOR_AUTH,
    "PA": PRIOR_AUTH,
    "PA001": PRIOR_AUTH,
    # Not covered / non-formulary
    "70": NOT_COVERED,
    "NC001": NOT_COVERED,
    # Plan limitations / quantity
    "76": QUANTITY_LIMIT,
    "QL001": QUANTITY_LIMIT,
    # Refill too soon
    "79": REFILL_TOO_SOON,
    "RT001": REFILL_TOO_SOON,
    # Step therapy
    "608": STEP_THERAPY,
    "ST001": STEP_THERAPY,
    # Eligibility / coverage dates
    "65": ELIGIBILITY,
    "67": ELIGIBILITY,
    "68": ELIGIBILITY,
    "69": ELIGIBILITY,
    "EL001": ELIGIBILITY,
    # Missing / invalid information ("M/I" codes)
    "15": MISSING_INFO,
    "21": MISSING_INFO,
    "25": MISSING_INFO,
    "MI001": MISSING_INFO,
}

# Keywords / phrases found in rejection messages -> category.
KEYWORD_RULES = {
    PRIOR_AUTH: [
        "prior authorization", "prior auth", "authorization required", "pa required",
        "pre-authorization", "preauthorization", "requires authorization", "needs authorization",
    ],
    NOT_COVERED: [
        "not covered", "non-formulary", "nonformulary", "not on formulary", "not on the formulary",
        "plan exclusion", "excluded from coverage", "not a covered benefit", "formulary exclusion",
    ],
    QUANTITY_LIMIT: [
        "quantity limit", "maximum quantity", "exceeds quantity", "quantity exceeds", "qty limit",
        "plan limitations exceeded", "days supply exceeds", "exceeds maximum", "exceeds the maximum",
    ],
    REFILL_TOO_SOON: [
        "refill too soon", "too soon", "early refill", "fill too soon", "next fill date",
        "next available fill",
    ],
    STEP_THERAPY: [
        "step therapy", "prerequisite drug", "first-line", "first line", "trial of",
        "alternate drug therapy required", "try and fail", "trial and failure",
    ],
    ELIGIBILITY: [
        "not eligible", "patient not covered", "member not found", "coverage terminated",
        "coverage expired", "inactive coverage", "coverage not active", "eligibility",
        "insurance coverage issue", "terminated", "not effective",
    ],
    MISSING_INFO: [
        "missing", "m/i", "invalid", "incorrect", "required field", "not provided",
        "incomplete", "does not match", "mismatch",
    ],
}

# Plain-language guidance for each category (shown on the explanation page).
CATEGORY_GUIDANCE = {
    PRIOR_AUTH: {
        "what_happened": "The claim was rejected because the payer requires prior authorization (approval in advance) before it will cover this medication.",
        "possible_reason": "The payer's policy may list this medication, strength or quantity as needing prior authorization.",
        "suggested_action": "Review the applicable policy requirements and prepare the required documentation for a prior authorization request.",
        "next_steps": [
            "Verify the patient's coverage and plan details.",
            "Review the prior authorization requirements in the payer policy.",
            "Collect the required administrative information and supporting documentation from the prescriber.",
            "Prepare the PA request using the PA Assistant and have it reviewed by authorized staff.",
            "Submit the request through the payer's official channel and record the payer's response.",
        ],
        "missing_info_hints": ["Supporting documentation requested by the payer", "Member ID and plan / group number"],
    },
    NOT_COVERED: {
        "what_happened": "The claim was rejected because the medication is not covered by the patient's plan (for example, it is not on the plan's formulary).",
        "possible_reason": "The medication may be excluded from the plan or not listed on the formulary.",
        "suggested_action": "Check the formulary for covered alternatives and contact the prescriber about options, or ask whether a formulary exception request is appropriate.",
        "next_steps": [
            "Confirm the medication name, strength and NDC were entered correctly.",
            "Check the payer's formulary information for covered alternatives.",
            "Contact the prescriber to discuss alternatives or a formulary exception request.",
            "Inform the patient about the status and possible options (e.g. cash price).",
        ],
        "missing_info_hints": ["Formulary alternatives list", "Prescriber decision on alternative or exception"],
    },
    QUANTITY_LIMIT: {
        "what_happened": "The claim was rejected because the quantity or days' supply is above the limit allowed by the plan.",
        "possible_reason": "The plan may limit how much of this medication can be dispensed per fill or per time period.",
        "suggested_action": "Verify the quantity and days' supply, then either adjust the quantity to the allowed limit or prepare a quantity limit exception request.",
        "next_steps": [
            "Verify the prescribed quantity, directions and days' supply.",
            "Check the plan's quantity limit for this medication in the policy.",
            "Contact the prescriber if the quantity needs to be changed or justified.",
            "If an exception is needed, prepare the request and have it reviewed.",
        ],
        "missing_info_hints": ["Allowed quantity per the plan", "Prescriber justification for the higher quantity"],
    },
    REFILL_TOO_SOON: {
        "what_happened": "The claim was rejected because the refill was requested earlier than the plan allows.",
        "possible_reason": "Not enough of the previous supply has been used yet according to the plan's refill rules.",
        "suggested_action": "Check the last fill date and the next eligible fill date. Wait until that date, or document the reason if an early-refill override is needed.",
        "next_steps": [
            "Check the date and days' supply of the previous fill.",
            "Calculate or confirm the next eligible fill date.",
            "Ask the patient whether there is a special reason (e.g. dose change, lost medication, travel).",
            "If appropriate, contact the payer help desk about an override and document the outcome.",
        ],
        "missing_info_hints": ["Previous fill date and days' supply", "Reason for early refill (if any)"],
    },
    STEP_THERAPY: {
        "what_happened": "The claim was rejected because the plan requires the patient to try one or more other medications first (step therapy).",
        "possible_reason": "The payer's policy may require a documented trial of a preferred medication before covering this one.",
        "suggested_action": "Check the patient's medication history for the required prerequisite drugs and contact the prescriber about a step therapy exception if appropriate.",
        "next_steps": [
            "Review the step therapy requirements in the policy.",
            "Check the patient's medication history for prerequisite medications.",
            "Contact the prescriber with the findings.",
            "If the prescriber requests an exception, prepare the request and have it reviewed.",
        ],
        "missing_info_hints": ["History of prerequisite medications", "Prescriber documentation for an exception"],
    },
    ELIGIBILITY: {
        "what_happened": "The claim was rejected because the payer could not confirm that the patient had active coverage for this date of service.",
        "possible_reason": "The coverage may have ended, not started yet, or the member details may not match the payer's records.",
        "suggested_action": "Verify the patient's insurance card and member details, and ask the patient for updated coverage information.",
        "next_steps": [
            "Verify the member ID, name, date of birth and group number with the patient.",
            "Ask whether the patient has new or secondary insurance.",
            "Re-submit with corrected information, or contact the payer help desk.",
        ],
        "missing_info_hints": ["Current insurance card / member ID", "Coverage effective dates"],
    },
    MISSING_INFO: {
        "what_happened": "The claim was rejected because some required information was missing or did not match the payer's records.",
        "possible_reason": "A field on the claim (for example prescriber ID, date or product information) may be empty or incorrect.",
        "suggested_action": "Identify the missing or incorrect field from the rejection message, correct it and re-submit the claim.",
        "next_steps": [
            "Read the rejection message to find which field is missing or invalid.",
            "Correct the information from the prescription or patient record.",
            "Re-submit the claim and confirm the new response.",
        ],
        "missing_info_hints": ["The specific field named in the rejection message"],
    },
    OTHER: {
        "what_happened": "The rejection could not be matched to a known category.",
        "possible_reason": INSUFFICIENT_INFO_MESSAGE,
        "suggested_action": "Manual review required: read the full payer response, and contact the payer help desk if the reason is unclear.",
        "next_steps": [
            "Read the full rejection message and any attached documents.",
            "Contact the payer help desk for clarification.",
            "Update the case with the clarified reason and analyze it again.",
        ],
        "missing_info_hints": ["A clear rejection reason from the payer"],
    },
}


@dataclass
class ClassificationResult:
    category: str
    confidence: float  # 0.0 - 1.0
    reason: str
    matched_code: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    is_ambiguous: bool = False
    insufficient_info: bool = False

    @property
    def confidence_label(self) -> str:
        return confidence_label(self.confidence)


def confidence_label(confidence: float) -> str:
    if confidence >= 0.8:
        return "High"
    if confidence >= 0.55:
        return "Medium"
    return "Low"


def _keyword_matches(text: str, keywords: list[str]) -> list[str]:
    """Find keywords in the text. Longer phrases are checked first, and a keyword that is
    only part of an already-matched phrase ("prior auth" in "prior authorization") is not counted twice."""
    matches = []
    for keyword in sorted(keywords, key=len, reverse=True):
        if keyword in text and not any(keyword in longer for longer in matches):
            matches.append(keyword)
    return matches


def classify_rejection(rejection_code: str = "", rejection_message: str = "") -> ClassificationResult:
    """Classify a rejection using the code and message. Never raises."""
    code = (rejection_code or "").strip().upper()
    text = (rejection_message or "").lower()

    scores = {category: 0 for category in CATEGORIES}
    evidence = {category: [] for category in CATEGORIES}

    # A known rejection code is strong evidence (3 points).
    code_category = REJECTION_CODE_MAP.get(code)
    if code_category:
        scores[code_category] += 3

    # Each keyword adds 1 point; multi-word phrases are more specific (2 points).
    for category, keywords in KEYWORD_RULES.items():
        for keyword in _keyword_matches(text, keywords):
            scores[category] += 2 if " " in keyword or "-" in keyword else 1
            evidence[category].append(keyword)

    ranked = sorted(CATEGORIES, key=lambda c: scores[c], reverse=True)  # stable: ties keep CATEGORIES order
    best, runner_up = ranked[0], ranked[1]

    if scores[best] == 0:
        return ClassificationResult(
            category=OTHER,
            confidence=0.2,
            reason=INSUFFICIENT_INFO_MESSAGE,
            insufficient_info=True,
        )

    confidence = min(0.97, 0.5 + 0.12 * scores[best])
    is_ambiguous = scores[runner_up] == scores[best]
    if is_ambiguous:
        confidence -= 0.2

    # Build a human-readable explanation of the evidence.
    reason_parts = []
    if code_category == best:
        reason_parts.append(f"the rejection code '{code}' is associated with {best}")
    if evidence[best]:
        quoted = ", ".join(f"'{k}'" for k in evidence[best])
        reason_parts.append(f"the rejection message contains {quoted}")
    reason = "Classified as " + best + " because " + " and ".join(reason_parts) + "."
    if is_ambiguous:
        reason += f" The message also matches {runner_up}, so please confirm manually."

    return ClassificationResult(
        category=best,
        confidence=round(confidence, 2),
        reason=reason,
        matched_code=code if code_category == best else "",
        matched_keywords=evidence[best],
        is_ambiguous=is_ambiguous,
    )
