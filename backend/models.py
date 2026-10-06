"""
Database tables (SQLAlchemy ORM models).

Tables:
    users               - staff accounts (password stored as a salted hash)
    sessions            - login tokens
    cases               - prescription / claim rejection cases + analysis results
    documents           - text extracted from uploaded files
    case_documents      - link table between cases and documents
    case_status_history - audit trail of every status change
"""
from datetime import datetime

from sqlalchemy import JSON, Column, Date, DateTime, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from database import Base

CASE_STATUSES = [
    "New",
    "Under Review",
    "PA Required",
    "Waiting for Information",
    "Submitted",
    "Resolved",
]


case_documents = Table(
    "case_documents",
    Base.metadata,
    Column("case_id", Integer, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    full_name = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.now)


class SessionToken(Base):
    __tablename__ = "sessions"

    token = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)

    # Case information entered by staff
    patient_id = Column(String(50), nullable=False, index=True)
    claim_id = Column(String(50), nullable=False, index=True)
    medication = Column(String(120), nullable=False)
    insurance = Column(String(120), nullable=False)
    rejection_code = Column(String(20), default="")
    rejection_message = Column(Text, nullable=False)
    quantity = Column(String(50), nullable=True)
    date_of_service = Column(Date, nullable=True)
    prescriber = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)

    # Analysis results (filled by POST /api/cases/{id}/analyze)
    category = Column(String(60), nullable=True)
    confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    classification_reason = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    possible_reason = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    next_steps = Column(JSON, nullable=True)  # list[str]
    missing_info = Column(JSON, nullable=True)  # list[str]
    policy_matches = Column(JSON, nullable=True)  # list[{source, title, excerpt, score}]
    analysis_source = Column(String(80), nullable=True)  # "rule-based" or "ollama (model)"
    analyzed_at = Column(DateTime, nullable=True)

    # Prior authorization assistant
    pa_checklist = Column(JSON, nullable=True)  # list[{key, label, done, auto, hint}]
    pa_draft = Column(Text, nullable=True)
    pa_draft_source = Column(String(80), nullable=True)
    pa_draft_generated_at = Column(DateTime, nullable=True)

    # Workflow
    status = Column(String(40), default="New", nullable=False, index=True)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    documents = relationship("Document", secondary=case_documents, back_populates="cases")
    history = relationship(
        "StatusHistory",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="StatusHistory.changed_at",
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String(120), nullable=False)
    file_type = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    uploaded_by = Column(String(50), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.now)

    cases = relationship("Case", secondary=case_documents, back_populates="documents")


class StatusHistory(Base):
    __tablename__ = "case_status_history"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    old_status = Column(String(40), nullable=True)
    new_status = Column(String(40), nullable=False)
    note = Column(String(500), nullable=True)
    changed_by = Column(String(50), nullable=True)
    changed_at = Column(DateTime, default=datetime.now)

    case = relationship("Case", back_populates="history")
