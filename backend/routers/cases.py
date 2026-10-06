"""
Case endpoints: create / list / search / view / update / delete, plus the
analysis, status tracking and PA assistant actions for a single case.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

import pa_assistant
from ai_service import analyze_case
from auth import get_current_user
from classifier import PRIOR_AUTH
from database import get_db
from models import Case, Document, StatusHistory, User
from schemas import (
    CaseCreate,
    CaseDetail,
    CaseSummary,
    CaseUpdate,
    ChecklistUpdate,
    DraftUpdate,
    StatusUpdate,
)

router = APIRouter(prefix="/api/cases", tags=["cases"])

REQUIRED_FIELDS = {"patient_id", "claim_id", "medication", "insurance", "rejection_message"}


# ----------------------------------------------------------------- helpers ---
def get_case_or_404(db: Session, case_id: int) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case #{case_id} was not found.")
    return case


def record_status_change(db: Session, case: Case, new_status: str, changed_by: str, note: str | None = None):
    """Change the status and write an entry to the status history table."""
    db.add(StatusHistory(case_id=case.id, old_status=case.status, new_status=new_status, note=note, changed_by=changed_by))
    case.status = new_status


def case_fields(case: Case) -> dict:
    return {
        "patient_id": case.patient_id,
        "claim_id": case.claim_id,
        "medication": case.medication,
        "insurance": case.insurance,
        "rejection_code": case.rejection_code or "",
        "rejection_message": case.rejection_message,
        "quantity": case.quantity,
        "date_of_service": case.date_of_service,
        "prescriber": case.prescriber,
    }


def run_analysis(db: Session, case: Case, username: str, use_llm: bool = True):
    """Analyze the case, store the results and move a 'New' case into the workflow."""
    result = analyze_case(case_fields(case), use_llm=use_llm)
    for key, value in result.items():
        setattr(case, key, value)
    case.analyzed_at = datetime.now()

    if case.status == "New":
        new_status = "PA Required" if case.category == PRIOR_AUTH else "Under Review"
        record_status_change(db, case, new_status, username, f"Set automatically after analysis ({case.category}).")

    case.pa_checklist = pa_assistant.build_checklist(case)


# --------------------------------------------------------------- endpoints ---
@router.get("", response_model=list[CaseSummary])
def list_cases(
    q: Optional[str] = Query(default=None, max_length=100, description="Search patient ID, case ID, claim ID, medication, insurance, category"),
    status_filter: Optional[str] = Query(default=None, alias="status", max_length=40),
    category: Optional[str] = Query(default=None, max_length=60),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Case)
    if status_filter:
        query = query.filter(Case.status == status_filter)
    if category:
        query = query.filter(Case.category == category)
    if q and q.strip():
        term = q.strip()
        like = f"%{term}%"
        conditions = [
            Case.patient_id.ilike(like),
            Case.claim_id.ilike(like),
            Case.medication.ilike(like),
            Case.insurance.ilike(like),
            Case.category.ilike(like),
            Case.rejection_code.ilike(like),
        ]
        case_number = term.lstrip("#")
        if case_number.isdigit():
            conditions.append(Case.id == int(case_number))
        query = query.filter(or_(*conditions))
    return query.order_by(Case.created_at.desc(), Case.id.desc()).limit(500).all()


@router.post("", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = Case(**payload.model_dump(exclude={"document_id"}), status="New", created_by=user.username)

    if payload.document_id is not None:
        document = db.get(Document, payload.document_id)
        if document is None:
            raise HTTPException(status_code=400, detail=f"Document #{payload.document_id} was not found.")
        case.documents.append(document)

    db.add(case)
    db.flush()  # assigns case.id
    db.add(StatusHistory(case_id=case.id, old_status=None, new_status="New", note="Case created.", changed_by=user.username))
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_case_or_404(db, case_id)


@router.put("/{case_id}", response_model=CaseDetail)
def update_case(case_id: int, payload: CaseUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = get_case_or_404(db, case_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key in REQUIRED_FIELDS and value is None:
            raise HTTPException(status_code=422, detail=f"'{key}' cannot be empty.")
        setattr(case, key, value)
    if case.pa_checklist is not None:
        case.pa_checklist = pa_assistant.build_checklist(case)  # auto items may have changed
    db.commit()
    db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = get_case_or_404(db, case_id)
    db.delete(case)
    db.commit()


@router.put("/{case_id}/status", response_model=CaseDetail)
def update_status(case_id: int, payload: StatusUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = get_case_or_404(db, case_id)
    if payload.status != case.status:
        record_status_change(db, case, payload.status, user.username, payload.note)
        db.commit()
        db.refresh(case)
    return case


@router.post("/{case_id}/analyze", response_model=CaseDetail)
def analyze(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = get_case_or_404(db, case_id)
    run_analysis(db, case, user.username)
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/pa-draft", response_model=CaseDetail)
def generate_pa_draft(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = get_case_or_404(db, case_id)
    if not case.category:
        run_analysis(db, case, user.username)  # the draft needs the category and policy matches

    draft, source = pa_assistant.generate_draft(case)
    case.pa_draft = draft
    case.pa_draft_source = source
    case.pa_draft_generated_at = datetime.now()
    case.pa_checklist = pa_assistant.build_checklist(case)
    db.commit()
    db.refresh(case)
    return case


@router.put("/{case_id}/pa-draft", response_model=CaseDetail)
def save_pa_draft(case_id: int, payload: DraftUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Save a draft that staff edited by hand."""
    case = get_case_or_404(db, case_id)
    case.pa_draft = payload.pa_draft
    case.pa_draft_source = f"edited by {user.username}"
    db.commit()
    db.refresh(case)
    return case


@router.put("/{case_id}/pa-checklist", response_model=CaseDetail)
def update_checklist(case_id: int, payload: ChecklistUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = get_case_or_404(db, case_id)
    case.pa_checklist = pa_assistant.apply_manual_updates(case, [item.model_dump() for item in payload.items])
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/documents/{document_id}", response_model=CaseDetail)
def link_document(case_id: int, document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = get_case_or_404(db, case_id)
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document #{document_id} was not found.")
    if document not in case.documents:
        case.documents.append(document)
        db.commit()
        db.refresh(case)
    return case
