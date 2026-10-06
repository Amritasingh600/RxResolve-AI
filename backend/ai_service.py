"""
AI analysis pipeline.

    rejection -> classify (rule-based) -> search policies -> explain -> next steps

The classification is ALWAYS rule-based, so results are predictable and
explainable. If Ollama (a free, local LLM runtime) is running, the local model
is only used to:
  * write a friendlier plain-language explanation, grounded in the policy excerpts
  * suggest a category when the rules find nothing (clearly labelled, low confidence)
  * write the request paragraph of a PA draft (see pa_assistant.py)

If Ollama is not installed or not running, every step falls back to templates.
"""
import time

import httpx

import config
from classifier import (
    CATEGORIES,
    CATEGORY_GUIDANCE,
    INSUFFICIENT_INFO_MESSAGE,
    OTHER,
    classify_rejection,
)
from policy_search import search_policies

STATUS_CACHE_SECONDS = 30
_status_cache = {"checked_at": 0.0, "result": None}

SYSTEM_PROMPT = (
    "You are an administrative assistant for pharmacy staff. You help explain prescription claim "
    "rejections in plain language. Rules: use ONLY the facts and policy excerpts you are given; never "
    "invent insurance rules, coverage criteria, prices or approval decisions; never give clinical or "
    "medical advice; if the information is not enough, say that manual review is required."
)


# ------------------------------------------------------------------ Ollama ---
def check_ollama(force: bool = False) -> dict:
    """Return {enabled, available, model, mode, detail}. Cached for a few seconds."""
    now = time.time()
    if not force and _status_cache["result"] and now - _status_cache["checked_at"] < STATUS_CACHE_SECONDS:
        return _status_cache["result"]

    result = {"enabled": config.USE_OLLAMA, "available": False, "model": config.OLLAMA_MODEL, "mode": "rule-based", "detail": ""}
    if not config.USE_OLLAMA:
        result["detail"] = "Ollama is disabled (RXR_USE_OLLAMA=0). Using rule-based analysis."
    else:
        try:
            response = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=httpx.Timeout(2.0, connect=1.0))
            response.raise_for_status()
            installed = [m.get("name", "") for m in response.json().get("models", [])]
            if any(name == config.OLLAMA_MODEL or name.startswith(config.OLLAMA_MODEL + ":") for name in installed):
                result.update(available=True, mode="ollama", detail=f"Using local model '{config.OLLAMA_MODEL}' via Ollama.")
            else:
                result["detail"] = (
                    f"Ollama is running but model '{config.OLLAMA_MODEL}' is not installed "
                    f"(run: ollama pull {config.OLLAMA_MODEL}). Using rule-based analysis."
                )
        except Exception:
            result["detail"] = "Ollama is not running. Using rule-based analysis."

    _status_cache.update(checked_at=now, result=result)
    return result


def reset_status_cache():
    _status_cache.update(checked_at=0.0, result=None)


def is_ollama_available() -> bool:
    return check_ollama()["available"]


def generate_text(prompt: str) -> str | None:
    """Ask the local model for text. Returns None on any error (caller falls back)."""
    try:
        response = httpx.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=config.OLLAMA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        text = (response.json().get("response") or "").strip()
        return text or None
    except Exception:
        return None


def ai_source_label() -> str:
    return f"ollama ({config.OLLAMA_MODEL})"


# ---------------------------------------------------------------- helpers ---
def format_policy_context(policy_matches: list[dict]) -> str:
    if not policy_matches:
        return "No matching policy excerpt was found in the local knowledge base."
    return "\n\n".join(f"[{m['source']}]\n{m['excerpt']}" for m in policy_matches)


def find_missing_fields(case: dict) -> list[str]:
    """List administrative fields that are empty on the case."""
    checks = [
        ("rejection_code", "Rejection code"),
        ("quantity", "Quantity dispensed / requested"),
        ("date_of_service", "Date of service"),
        ("prescriber", "Prescriber name and contact information"),
    ]
    return [label for key, label in checks if not case.get(key)]


def _llm_explanation(case: dict, category: str, policy_matches: list[dict]) -> str | None:
    prompt = f"""A pharmacy claim was rejected. Explain to non-technical pharmacy staff what the rejection means
and why it may have happened, in 3 to 5 short sentences. Do not use bullet points.

Rejection category (determined by rules): {category}
Medication: {case.get('medication')}
Payer: {case.get('insurance')}
Rejection code: {case.get('rejection_code') or 'not provided'}
Rejection message: {case.get('rejection_message')}

Relevant excerpts from the local (sample) policy documents:
{format_policy_context(policy_matches)}

Only use the information above. If the excerpts do not cover this payer or medication, say that the
policy should be confirmed with the payer."""
    return generate_text(prompt)


def _llm_suggest_category(case: dict) -> str | None:
    options = ", ".join(c for c in CATEGORIES if c != OTHER)
    prompt = f"""Classify this pharmacy claim rejection message into exactly one of these categories:
{options}, Other.

Rejection code: {case.get('rejection_code') or 'none'}
Rejection message: {case.get('rejection_message')}

Answer with the category name only."""
    answer = generate_text(prompt) or ""
    # Only accept an answer that is exactly one of our categories.
    for category in CATEGORIES:
        if category.lower() in answer.lower():
            return category if category != OTHER else None
    return None


# ------------------------------------------------------------ main entry ---
def analyze_case(case: dict, use_llm: bool = True) -> dict:
    """
    Analyze a rejection. `case` is a dict with the case fields.
    Returns a dict with all analysis fields that are stored on the case.
    """
    classification = classify_rejection(case.get("rejection_code", ""), case.get("rejection_message", ""))
    category = classification.category
    confidence = classification.confidence
    reason = classification.reason
    llm_ready = use_llm and is_ollama_available()
    source = "rule-based"

    # If the rules found nothing, the local model may suggest a category.
    if category == OTHER and llm_ready:
        suggested = _llm_suggest_category(case)
        if suggested:
            category = suggested
            confidence = 0.5
            reason = (
                f"No rejection code or keyword rule matched. The local AI model suggested '{suggested}'. "
                "This is a low-confidence suggestion — please verify manually."
            )
            source = ai_source_label()

    guidance = CATEGORY_GUIDANCE[category]

    query = " ".join(
        str(part) for part in [category, case.get("rejection_message"), case.get("medication"), case.get("insurance")] if part
    )
    # Only keep excerpts that are close in relevance to the best one, to avoid misleading matches.
    policy_matches = search_policies(query, top_k=3, relative_cutoff=0.7) if category != OTHER else []

    explanation = guidance["what_happened"]
    if llm_ready and category != OTHER:
        llm_text = _llm_explanation(case, category, policy_matches)
        if llm_text:
            explanation = llm_text
            source = ai_source_label()

    possible_reason = guidance["possible_reason"]
    if policy_matches:
        possible_reason += f" See the related section of '{policy_matches[0]['title']}' in the Policy Information below."
    elif category != OTHER:
        possible_reason += " No matching policy was found in the local knowledge base — confirm the requirement with the payer."

    missing_info = find_missing_fields(case) + guidance["missing_info_hints"]
    if category == OTHER:
        missing_info = [INSUFFICIENT_INFO_MESSAGE] + missing_info

    return {
        "category": category,
        "confidence": confidence,
        "classification_reason": reason,
        "explanation": explanation,
        "possible_reason": possible_reason,
        "suggested_action": guidance["suggested_action"],
        "next_steps": guidance["next_steps"],
        "missing_info": missing_info,
        "policy_matches": policy_matches,
        "analysis_source": source,
    }
