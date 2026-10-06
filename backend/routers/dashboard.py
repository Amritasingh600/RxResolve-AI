"""Dashboard statistics and AI status."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ai_service import check_ollama
from auth import get_current_user
from classifier import PRIOR_AUTH
from database import get_db
from models import CASE_STATUSES, Case, User
from schemas import AIStatus, DashboardOut

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total = db.query(Case).count()
    resolved = db.query(Case).filter(Case.status == "Resolved").count()
    pa_cases = db.query(Case).filter(or_(Case.category == PRIOR_AUTH, Case.status == "PA Required")).count()

    status_counts = dict(db.query(Case.status, func.count(Case.id)).group_by(Case.status).all())
    by_status = {name: status_counts.get(name, 0) for name in CASE_STATUSES}

    category_rows = db.query(Case.category, func.count(Case.id)).group_by(Case.category).all()
    by_category = {(category or "Not analyzed"): count for category, count in category_rows}

    recent = db.query(Case).order_by(Case.created_at.desc(), Case.id.desc()).limit(6).all()

    return DashboardOut(
        total_cases=total,
        pending_cases=total - resolved,
        resolved_cases=resolved,
        pa_cases=pa_cases,
        by_status=by_status,
        by_category=by_category,
        recent_cases=recent,
    )


@router.get("/ai/status", response_model=AIStatus)
def ai_status(user: User = Depends(get_current_user)):
    return check_ollama()
