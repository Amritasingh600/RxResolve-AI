"""
Hybrid rejection classifier combining Machine Learning (scikit-learn) with deterministic rules.

This module provides state-of-the-art rejection classification for RxResolveAI:
1. A machine learning model (TF-IDF + Multinomial Naive Bayes / Logistic Regression pipeline)
   trained on medical claim rejection text representing the 8 rejection categories.
2. If the ML model predicts a category with confidence > 70% (0.70), that prediction is used.
3. If the ML model's confidence is low (<= 70%) or the message is empty/uninformative,
   the classifier falls back to deterministic regex keyword and NCPDP rejection code rules
   as a safety guardrail.

The guidance text below is generic administrative guidance. It deliberately
does NOT describe any real payer's rules.
"""
import math
import re
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

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

# Medical rejection classification training dataset
MOCK_MEDICAL_TRAINING_DATA: list[tuple[str, str]] = [
    # Prior Authorization Required
    ("prior authorization required", PRIOR_AUTH),
    ("PA required for this product", PRIOR_AUTH),
    ("prior authorization required by health plan", PRIOR_AUTH),
    ("claim requires prior authorization approval", PRIOR_AUTH),
    ("medication requires prior auth before dispensing", PRIOR_AUTH),
    ("prior auth required from insurance payer", PRIOR_AUTH),
    ("pre-authorization required for specialty medication", PRIOR_AUTH),
    ("preauthorization required by insurance", PRIOR_AUTH),
    ("requires authorization from insurance provider", PRIOR_AUTH),
    ("needs authorization from pharmacy benefits manager", PRIOR_AUTH),
    ("prior auth criteria not met, documentation required", PRIOR_AUTH),
    ("prescriber must submit prior authorization form", PRIOR_AUTH),
    ("approval required in advance before claim coverage", PRIOR_AUTH),
    ("authorization required prior to coverage", PRIOR_AUTH),
    ("drug requires clinical prior authorization", PRIOR_AUTH),

    # Drug Not Covered
    ("product/service not covered", NOT_COVERED),
    ("product not covered", NOT_COVERED),
    ("non-formulary drug", NOT_COVERED),
    ("medication not covered under patient plan benefit", NOT_COVERED),
    ("drug excluded from formulary", NOT_COVERED),
    ("plan exclusion non covered medication", NOT_COVERED),
    ("not on formulary list, non-preferred product", NOT_COVERED),
    ("not on the formulary", NOT_COVERED),
    ("excluded from coverage by benefit plan", NOT_COVERED),
    ("not a covered benefit under this plan", NOT_COVERED),
    ("formulary exclusion consult formulary for alternatives", NOT_COVERED),
    ("medication not covered by prescription policy", NOT_COVERED),
    ("benefit exclusion product not covered", NOT_COVERED),
    ("nonformulary medication requested", NOT_COVERED),

    # Quantity Limit
    ("quantity limit exceeded", QUANTITY_LIMIT),
    ("maximum quantity is 60 per 30 days", QUANTITY_LIMIT),
    ("exceeds plan maximum quantity allowed", QUANTITY_LIMIT),
    ("days supply exceeds plan limitation", QUANTITY_LIMIT),
    ("quantity exceeds maximum allowable dose per fill", QUANTITY_LIMIT),
    ("plan limitations exceeded requested quantity too high", QUANTITY_LIMIT),
    ("exceeds allowable quantity limit for this dosage form", QUANTITY_LIMIT),
    ("cumulative daily dose exceeds plan maximum limits", QUANTITY_LIMIT),
    ("prescribed quantity exceeds benefit limits", QUANTITY_LIMIT),
    ("qty limit exceeded for requested duration", QUANTITY_LIMIT),
    ("maximum allowable units reached", QUANTITY_LIMIT),
    ("dose exceeds maximum limit per fill", QUANTITY_LIMIT),

    # Refill Too Soon
    ("refill too soon", REFILL_TOO_SOON),
    ("early refill attempt 75 percent not used", REFILL_TOO_SOON),
    ("fill too soon next available fill date is next week", REFILL_TOO_SOON),
    ("refill requested prior to authorized next fill date", REFILL_TOO_SOON),
    ("early refill rejected by payer rules", REFILL_TOO_SOON),
    ("refill too soon previous fill still active", REFILL_TOO_SOON),
    ("next fill date has not arrived yet", REFILL_TOO_SOON),
    ("early refill denial wait until permissible window", REFILL_TOO_SOON),
    ("patient has sufficient days supply remaining on hand", REFILL_TOO_SOON),
    ("too soon to refill this prescription", REFILL_TOO_SOON),
    ("early refill next eligible fill date required", REFILL_TOO_SOON),

    # Step Therapy
    ("step therapy required", STEP_THERAPY),
    ("trial of prerequisite drug required first", STEP_THERAPY),
    ("first-line agent must be tried and failed before coverage", STEP_THERAPY),
    ("step therapy protocol requires prior trial of preferred generic", STEP_THERAPY),
    ("alternative drug therapy required prior to approval", STEP_THERAPY),
    ("patient must try step 1 medication before step 2 coverage", STEP_THERAPY),
    ("prerequisite drug therapy not documented in claim history", STEP_THERAPY),
    ("requires trial and failure of tier 1 alternative", STEP_THERAPY),
    ("step therapy criteria not satisfied", STEP_THERAPY),
    ("must try and fail first-line therapy first", STEP_THERAPY),
    ("step therapy edit triggered prerequisite trial missing", STEP_THERAPY),

    # Eligibility Problem
    ("patient not covered - coverage terminated", ELIGIBILITY),
    ("patient not covered coverage terminated", ELIGIBILITY),
    ("member not found in payer eligibility file", ELIGIBILITY),
    ("coverage expired or inactive on date of service", ELIGIBILITY),
    ("patient insurance coverage is not active", ELIGIBILITY),
    ("member eligibility terminated prior to service date", ELIGIBILITY),
    ("cardholder id not eligible for benefits", ELIGIBILITY),
    ("insurance policy cancelled or not effective", ELIGIBILITY),
    ("eligibility problem patient coverage not found", ELIGIBILITY),
    ("member not enrolled on specified date of service", ELIGIBILITY),
    ("dependent not covered under subscriber policy", ELIGIBILITY),
    ("coverage not active on submitted date", ELIGIBILITY),
    ("patient not eligible", ELIGIBILITY),

    # Missing Information
    ("M/I Prescriber ID", MISSING_INFO),
    ("missing or invalid prescriber NPI", MISSING_INFO),
    ("required field missing patient date of birth", MISSING_INFO),
    ("missing DEA number or provider identifier", MISSING_INFO),
    ("invalid NDC number submitted on claim", MISSING_INFO),
    ("missing or invalid diagnosis code", MISSING_INFO),
    ("incomplete claim submission required field empty", MISSING_INFO),
    ("missing prescriber phone number or address", MISSING_INFO),
    ("invalid days supply or metric decimal quantity", MISSING_INFO),
    ("M/I member ID check card number and re-submit", MISSING_INFO),
    ("required field missing or invalid", MISSING_INFO),

    # Other
    ("claim could not be processed. contact help desk.", OTHER),
    ("claim could not be processed contact help desk", OTHER),
    ("system error during adjudication, please retry later", OTHER),
    ("unspecified claim transaction failure", OTHER),
    ("general processing error contact payer support line", OTHER),
    ("network communication error with pharmacy benefit manager", OTHER),
    ("host system unavailable transaction rejected", OTHER),
    ("unknown rejection code or unclassified transaction", OTHER),
    ("internal payer adjudication timeout", OTHER),
    ("unable to determine coverage status manual review needed", OTHER),
    ("administrative error please call provider services", OTHER),
]


class MedicalRejectionMLClassifier:
    """
    Machine Learning Classifier for prescription claim rejections.
    Uses scikit-learn Pipeline (TfidfVectorizer + MultinomialNB) when available,
    with a pure Python/NumPy TF-IDF Naive Bayes fallback to ensure maximum robustness
    and CPU-friendly execution without runtime crashes.
    """

    def __init__(self, training_data: list[tuple[str, str]]):
        self.training_data = training_data
        self.categories = CATEGORIES
        self.sklearn_pipeline = None
        self._init_model()

    def _init_model(self):
        # Attempt scikit-learn pipeline initialization
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB
            from sklearn.pipeline import Pipeline

            X = [text for text, _ in self.training_data]
            y = [cat for _, cat in self.training_data]
            pipeline = Pipeline([
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True)),
                ("clf", MultinomialNB(alpha=0.1)),
            ])
            pipeline.fit(X, y)
            self.sklearn_pipeline = pipeline
        except Exception:
            self.sklearn_pipeline = None

        # Build fallback TF-IDF Multinomial Naive Bayes model
        self._build_fallback_model()

    def _build_fallback_model(self):
        self.vocab = set()
        self.class_doc_counts = Counter()
        self.class_word_counts = {c: Counter() for c in self.categories}
        self.total_docs = len(self.training_data)

        for text, cat in self.training_data:
            tokens = self._tokenize(text)
            self.vocab.update(tokens)
            self.class_doc_counts[cat] += 1
            self.class_word_counts[cat].update(tokens)

        self.vocab_size = max(1, len(self.vocab))
        self.alpha = 0.1

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        words = re.findall(r"[a-z0-9]+", (text or "").lower())
        bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words) - 1)]
        return words + bigrams

    def predict_proba(self, text: str) -> tuple[str, float]:
        """
        Predict rejection category and associated confidence score [0.0, 1.0].
        """
        clean_text = (text or "").strip()
        if not clean_text:
            return OTHER, 0.0

        # Use scikit-learn pipeline if available
        if self.sklearn_pipeline is not None:
            try:
                probs = self.sklearn_pipeline.predict_proba([clean_text])[0]
                classes = list(self.sklearn_pipeline.classes_)
                best_idx = int(probs.argmax())
                return classes[best_idx], float(probs[best_idx])
            except Exception:
                pass

        # Fallback pure-python Multinomial Naive Bayes
        tokens = self._tokenize(clean_text)
        if not tokens:
            return OTHER, 0.0

        log_probs = {}
        for c in self.categories:
            prior = (
                math.log(self.class_doc_counts[c] / self.total_docs)
                if self.class_doc_counts[c] > 0
                else -10.0
            )
            total_words = sum(self.class_word_counts[c].values())
            denom = total_words + self.alpha * self.vocab_size
            likelihood = sum(
                math.log((self.class_word_counts[c].get(t, 0) + self.alpha) / denom)
                for t in tokens
            )
            log_probs[c] = prior + likelihood

        max_log = max(log_probs.values())
        exps = {c: math.exp(v - max_log) for c, v in log_probs.items()}
        sum_exps = sum(exps.values())
        probs = {c: exps[c] / sum_exps for c in self.categories}
        best_category = max(probs, key=lambda c: probs[c])
        return best_category, probs[best_category]


_ml_classifier: Optional[MedicalRejectionMLClassifier] = None
_ml_lock = threading.Lock()


def get_ml_classifier() -> MedicalRejectionMLClassifier:
    """Return the singleton instance of the medical rejection ML classifier."""
    global _ml_classifier
    with _ml_lock:
        if _ml_classifier is None:
            _ml_classifier = MedicalRejectionMLClassifier(MOCK_MEDICAL_TRAINING_DATA)
    return _ml_classifier


@dataclass
class ClassificationResult:
    category: str
    confidence: float  # 0.0 - 1.0
    reason: str
    matched_code: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    is_ambiguous: bool = False
    insufficient_info: bool = False
    model_source: str = "hybrid"

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
    """
    Classify a rejection using the hybrid ML + deterministic rule system.
    Never raises exceptions.
    
    1. Runs ML model on rejection text.
    2. If ML confidence > 0.70 (70%), returns that category.
    3. If ML confidence is low (<= 0.70) or uninformative, falls back to deterministic regex rules.
    """
    code = (rejection_code or "").strip().upper()
    text = (rejection_message or "").strip().lower()

    # Deterministic scoring
    scores = {category: 0 for category in CATEGORIES}
    evidence = {category: [] for category in CATEGORIES}

    code_category = REJECTION_CODE_MAP.get(code)
    if code_category:
        scores[code_category] += 3

    for category, keywords in KEYWORD_RULES.items():
        for keyword in _keyword_matches(text, keywords):
            scores[category] += 2 if " " in keyword or "-" in keyword else 1
            evidence[category].append(keyword)

    ranked = sorted(CATEGORIES, key=lambda c: scores[c], reverse=True)
    best_rule_cat, runner_up = ranked[0], ranked[1]
    is_ambiguous = scores[runner_up] == scores[best_rule_cat] and scores[best_rule_cat] > 0

    # Query ML classifier if message text contains meaningful words
    ml_category = OTHER
    ml_confidence = 0.0
    if any(c.isalpha() for c in text):
        try:
            classifier = get_ml_classifier()
            ml_category, ml_confidence = classifier.predict_proba(text)
        except Exception:
            ml_category, ml_confidence = OTHER, 0.0

    # UPGRADE 2 HYBRID LOGIC:
    # If ML model confidence is > 70% (0.70)
    if ml_confidence > 0.70:
        # Check if the rejection message is an unknown/manual review notice
        if ml_category == OTHER and scores[best_rule_cat] == 0:
            return ClassificationResult(
                category=OTHER,
                confidence=0.2,
                reason=INSUFFICIENT_INFO_MESSAGE,
                insufficient_info=True,
                model_source="ml-other",
            )

        target_cat = ml_category
        # If code matches deterministic category and agrees with ML
        if code_category and code_category == ml_category:
            final_conf = max(ml_confidence, min(0.97, 0.5 + 0.12 * scores[code_category]))
            reason_parts = [
                f"the machine learning classifier identified this category with {int(ml_confidence * 100)}% confidence",
                f"the rejection code '{code}' is associated with {ml_category}",
            ]
            if evidence[ml_category]:
                quoted = ", ".join(f"'{k}'" for k in evidence[ml_category])
                reason_parts.append(f"the rejection message contains {quoted}")
            reason = "Classified as " + ml_category + " because " + " and ".join(reason_parts) + "."
            return ClassificationResult(
                category=ml_category,
                confidence=round(final_conf, 2),
                reason=reason,
                matched_code=code,
                matched_keywords=evidence[ml_category],
                model_source="hybrid-ml-code",
            )

        # If code is provided but conflicts with ML, check if code is a strong indicator
        if code_category and code_category != ml_category and scores[code_category] >= 3:
            # Deterministic code safety guardrail
            pass
        else:
            reason_parts = [
                f"the machine learning classifier identified this category with {int(ml_confidence * 100)}% confidence"
            ]
            if code_category == ml_category:
                reason_parts.append(f"the rejection code '{code}' is associated with {ml_category}")
            if evidence[ml_category]:
                quoted = ", ".join(f"'{k}'" for k in evidence[ml_category])
                reason_parts.append(f"the rejection message contains {quoted}")
            reason = "Classified as " + ml_category + " because " + " and ".join(reason_parts) + "."
            return ClassificationResult(
                category=ml_category,
                confidence=round(ml_confidence, 2),
                reason=reason,
                matched_code=code if code_category == ml_category else "",
                matched_keywords=evidence[ml_category],
                model_source="ml",
            )

    # SAFETY GUARDRAIL FALLBACK:
    # Use deterministic regex keyword rules and rejection code lookup
    if scores[best_rule_cat] == 0:
        return ClassificationResult(
            category=OTHER,
            confidence=0.2,
            reason=INSUFFICIENT_INFO_MESSAGE,
            insufficient_info=True,
            model_source="rule-fallback",
        )

    confidence = min(0.97, 0.5 + 0.12 * scores[best_rule_cat])
    if is_ambiguous:
        confidence -= 0.2

    reason_parts = []
    if code_category == best_rule_cat:
        reason_parts.append(f"the rejection code '{code}' is associated with {best_rule_cat}")
    if evidence[best_rule_cat]:
        quoted = ", ".join(f"'{k}'" for k in evidence[best_rule_cat])
        reason_parts.append(f"the rejection message contains {quoted}")
    reason = "Classified as " + best_rule_cat + " because " + " and ".join(reason_parts) + "."
    if is_ambiguous:
        reason += f" The message also matches {runner_up}, so please confirm manually."

    return ClassificationResult(
        category=best_rule_cat,
        confidence=round(confidence, 2),
        reason=reason,
        matched_code=code if code_category == best_rule_cat else "",
        matched_keywords=evidence[best_rule_cat],
        is_ambiguous=is_ambiguous,
        model_source="rule-guardrail",
    )
