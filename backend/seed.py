"""
Demo data: creates the demo users and loads the fictional sample cases from
sample_data/sample_cases.json the first time the app starts.

All patients, payers and medications in the sample data are fictional.
"""
import json
from datetime import date, datetime, timedelta

import config
from auth import hash_password
from models import Case, StatusHistory, User
from routers.cases import run_analysis

DEMO_USERS = [
    {"username": "admin", "password": "admin123", "full_name": "Demo Administrator"},
    {"username": "staff", "password": "staff123", "full_name": "Demo Pharmacy Staff"},
]


def seed_users(db) -> None:
    if db.query(User).count() > 0:
        return
    for user in DEMO_USERS:
        db.add(User(username=user["username"], password_hash=hash_password(user["password"]), full_name=user["full_name"]))
    db.commit()


def seed_cases(db) -> int:
    """Load sample cases if the cases table is empty. Returns the number of cases added."""
    if db.query(Case).count() > 0:
        return 0

    sample_file = config.SAMPLE_DATA_DIR / "sample_cases.json"
    if not sample_file.is_file():
        return 0

    try:
        samples = json.loads(sample_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0

    for index, sample in enumerate(samples):
        # Spread the demo cases over the last few days so "recent cases" looks realistic.
        created_at = datetime.now() - timedelta(days=len(samples) - index, hours=index)
        final_status = sample.pop("status", "New")
        days_ago = sample.pop("days_ago", None)
        should_analyze = sample.pop("analyze", True)

        case = Case(**sample, status="New", created_by="seed", created_at=created_at)
        if days_ago is not None:
            case.date_of_service = date.today() - timedelta(days=days_ago)
        db.add(case)
        db.flush()
        db.add(StatusHistory(case_id=case.id, new_status="New", note="Sample case loaded.", changed_by="seed", changed_at=created_at))

        # Rule-based analysis only, so startup is fast even when Ollama is running.
        # One sample case is left un-analyzed so the "Analyze Rejection" button can be demonstrated.
        if should_analyze:
            run_analysis(db, case, "seed", use_llm=False)

        if final_status != case.status:
            db.add(StatusHistory(case_id=case.id, old_status=case.status, new_status=final_status, note="Sample workflow status.", changed_by="seed"))
            case.status = final_status

    db.commit()
    return len(samples)


def seed_demo_data(db) -> None:
    seed_users(db)
    seed_cases(db)
