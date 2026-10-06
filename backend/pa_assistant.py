"""
Prior Authorization (PA) Assistant.

Builds a checklist and a draft request for a case. The draft is ALWAYS labelled
as an AI-generated draft that requires human review, and it is never sent
anywhere — staff copy it into the payer's official process themselves.

Bracketed text such as "[Prescriber to complete]" in the draft marks fields the
staff member must fill in; the system never invents clinical information.
"""
import textwrap
from datetime import date

import ai_service
from classifier import NOT_COVERED, PRIOR_AUTH, QUANTITY_LIMIT, STEP_THERAPY

DRAFT_LABEL = "AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW"

DRAFT_TITLES = {
    PRIOR_AUTH: "Prior Authorization Request",
    STEP_THERAPY: "Step Therapy Exception Request",
    QUANTITY_LIMIT: "Quantity Limit Exception Request",
    NOT_COVERED: "Formulary Exception Request",
}
DEFAULT_DRAFT_TITLE = "Claim Rejection Follow-up Request"

# Items that are checked automatically from the case data (staff cannot tick them manually).
AUTO_ITEMS = [
    ("patient_info", "Patient information", "Patient ID is recorded on the case."),
    ("medication_info", "Medication information (name and quantity)", "Medication name and quantity are recorded."),
    ("insurance_info", "Insurance / payer information", "Payer name is recorded on the case."),
    ("rejection_info", "Rejection information (code and message)", "Both rejection code and message are recorded."),
    ("prescriber_info", "Prescriber information", "Add the prescriber on the case details page."),
]

# Items that staff confirm manually.
MANUAL_ITEMS = [
    ("policy_reviewed", "Applicable policy requirements reviewed", "Read the matching policy excerpt on the case page."),
    ("required_documentation", "Required documentation collected", "Documents requested by the payer's PA process."),
    ("supporting_info", "Supporting information from prescriber", "Clinical rationale must come from the prescriber — RxResolveAI does not generate it."),
    ("staff_review", "Draft reviewed and approved by authorized staff", "Required before anything is sent to a payer."),
]


def _auto_item_done(case, key: str) -> bool:
    if key == "patient_info":
        return bool(case.patient_id)
    if key == "medication_info":
        return bool(case.medication and case.quantity)
    if key == "insurance_info":
        return bool(case.insurance)
    if key == "rejection_info":
        return bool(case.rejection_code and case.rejection_message)
    if key == "prescriber_info":
        return bool(case.prescriber)
    return False


def build_checklist(case) -> list[dict]:
    """Recompute automatic items and keep the staff's previous choices for manual items."""
    previous = {item["key"]: item.get("done", False) for item in (case.pa_checklist or [])}
    items = [
        {"key": key, "label": label, "done": _auto_item_done(case, key), "auto": True, "hint": hint}
        for key, label, hint in AUTO_ITEMS
    ]
    items += [
        {"key": key, "label": label, "done": bool(previous.get(key, False)), "auto": False, "hint": hint}
        for key, label, hint in MANUAL_ITEMS
    ]
    return items


def apply_manual_updates(case, submitted_items: list[dict]) -> list[dict]:
    """Apply ticks from the UI. Only manual items can be changed by the user."""
    submitted = {item["key"]: item["done"] for item in submitted_items}
    checklist = build_checklist(case)
    for item in checklist:
        if not item["auto"] and item["key"] in submitted:
            item["done"] = bool(submitted[item["key"]])
    return checklist


def _template_request_paragraph(case, title: str) -> str:
    return (
        f"We are requesting a review ({title.lower()}) for the medication listed above. The claim was "
        f"rejected by {case.insurance} with the message: \"{case.rejection_message.strip()}\". "
        "The required documentation and the prescriber's supporting information are listed below."
    )


def _llm_request_paragraph(case, title: str) -> str | None:
    prompt = f"""Write one short, professional paragraph (3-4 sentences) for a {title} letter from a pharmacy to a payer.
Facts you may use:
- Medication: {case.medication}
- Quantity: {case.quantity or 'not provided'}
- Payer: {case.insurance}
- Rejection code: {case.rejection_code or 'not provided'}
- Rejection message: {case.rejection_message}
Do not include patient names, diagnoses, clinical justification, or any promise of approval.
Do not add a greeting or signature. Only output the paragraph."""
    return ai_service.generate_text(prompt)


def generate_draft(case, use_llm: bool = True) -> tuple[str, str]:
    """Return (draft_text, source). Source is 'template' or 'ollama (model)'."""
    title = DRAFT_TITLES.get(case.category, DEFAULT_DRAFT_TITLE)

    source = "template"
    request_paragraph = None
    if use_llm and ai_service.is_ollama_available():
        request_paragraph = _llm_request_paragraph(case, title)
        if request_paragraph:
            source = ai_service.ai_source_label()
    if not request_paragraph:
        request_paragraph = _template_request_paragraph(case, title)

    policy_lines = [
        f"- {m['title']} ({m['source']}): {textwrap.shorten(m['excerpt'].splitlines()[-1], 220, placeholder=' …')}"
        for m in (case.policy_matches or [])[:2]
    ] or ["- [No matching policy in the local knowledge base — confirm requirements with the payer]"]

    attachment_lines = [f"- {doc.filename}" for doc in case.documents] or [
        "- [No documents attached yet — add the documentation required by the payer]"
    ]

    date_of_service = case.date_of_service.isoformat() if case.date_of_service else "[Date of service]"

    draft = f"""*** {DRAFT_LABEL} ***
Prepared by RxResolveAI (demo system). This draft has NOT been submitted to any payer.
An authorized staff member must review, complete and submit it through the payer's official process.

{title.upper()} — DRAFT
Date prepared: {date.today().isoformat()}
To: {case.insurance} — Prior Authorization / Exceptions Department

CASE INFORMATION
Patient ID: {case.patient_id}
Claim / Prescription ID: {case.claim_id}
Medication: {case.medication}
Quantity: {case.quantity or '[Quantity]'}
Date of service: {date_of_service}
Prescriber: {case.prescriber or '[Prescriber name and NPI — to be completed by staff]'}
Rejection code: {case.rejection_code or '[Not provided]'}
Rejection message: {case.rejection_message.strip()}

REQUEST
{request_paragraph}

CLINICAL JUSTIFICATION
[To be completed by the prescriber. RxResolveAI does not generate clinical information.]

RELEVANT POLICY REFERENCE (sample knowledge base)
{chr(10).join(policy_lines)}

ATTACHMENTS
{chr(10).join(attachment_lines)}

CONTACT
[Pharmacy / clinic name, phone and fax — to be completed by staff]

*** {DRAFT_LABEL} ***"""
    return draft, source
