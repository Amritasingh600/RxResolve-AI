"""
Pydantic models that define what the API accepts and returns.

Validation rules (required fields, max lengths, allowed statuses) live here so
that bad input is rejected with a clear 422 error before it reaches the database.
"""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

CaseStatus = Literal[
    "New",
    "Under Review",
    "PA Required",
    "Waiting for Information",
    "Submitted",
    "Resolved",
]


class StrictInput(BaseModel):
    """Base class for request bodies: trims whitespace from all strings."""

    model_config = ConfigDict(str_strip_whitespace=True)


# ----------------------------------------------------------------- auth ------
class LoginRequest(StrictInput):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str = ""


class LoginResponse(BaseModel):
    token: str
    user: UserOut


# ---------------------------------------------------------------- cases ------
class CaseCreate(StrictInput):
    patient_id: str = Field(min_length=1, max_length=50)
    claim_id: str = Field(min_length=1, max_length=50)
    medication: str = Field(min_length=1, max_length=120)
    insurance: str = Field(min_length=1, max_length=120)
    rejection_code: str = Field(default="", max_length=20)
    rejection_message: str = Field(min_length=1, max_length=2000)
    quantity: Optional[str] = Field(default=None, max_length=50)
    date_of_service: Optional[date] = None
    prescriber: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=4000)
    # Optional: link a previously uploaded document to the new case
    document_id: Optional[int] = None


class CaseUpdate(StrictInput):
    """All fields optional: only the fields that are sent get updated."""

    patient_id: Optional[str] = Field(default=None, min_length=1, max_length=50)
    claim_id: Optional[str] = Field(default=None, min_length=1, max_length=50)
    medication: Optional[str] = Field(default=None, min_length=1, max_length=120)
    insurance: Optional[str] = Field(default=None, min_length=1, max_length=120)
    rejection_code: Optional[str] = Field(default=None, max_length=20)
    rejection_message: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    quantity: Optional[str] = Field(default=None, max_length=50)
    date_of_service: Optional[date] = None
    prescriber: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=4000)


class StatusUpdate(StrictInput):
    status: CaseStatus
    note: Optional[str] = Field(default=None, max_length=500)


class ChecklistItem(BaseModel):
    key: str = Field(min_length=1, max_length=50)
    label: str = Field(default="", max_length=200)
    done: bool = False
    auto: bool = False
    hint: str = Field(default="", max_length=300)


class ChecklistUpdate(BaseModel):
    items: list[ChecklistItem]


class DraftUpdate(BaseModel):
    pa_draft: str = Field(min_length=1, max_length=20000)


class PolicyMatch(BaseModel):
    source: str
    title: str
    excerpt: str
    score: float


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    uploaded_at: datetime
    uploaded_by: Optional[str] = None


class DocumentOut(DocumentSummary):
    content: str


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    old_status: Optional[str]
    new_status: str
    note: Optional[str]
    changed_by: Optional[str]
    changed_at: datetime


class CaseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: str
    claim_id: str
    medication: str
    insurance: str
    rejection_code: str = ""
    rejection_message: str
    category: Optional[str] = None
    confidence: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CaseDetail(CaseSummary):
    quantity: Optional[str] = None
    date_of_service: Optional[date] = None
    prescriber: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None

    classification_reason: Optional[str] = None
    explanation: Optional[str] = None
    possible_reason: Optional[str] = None
    suggested_action: Optional[str] = None
    next_steps: Optional[list[str]] = None
    missing_info: Optional[list[str]] = None
    policy_matches: Optional[list[PolicyMatch]] = None
    analysis_source: Optional[str] = None
    analyzed_at: Optional[datetime] = None

    pa_checklist: Optional[list[ChecklistItem]] = None
    pa_draft: Optional[str] = None
    pa_draft_source: Optional[str] = None
    pa_draft_generated_at: Optional[datetime] = None

    documents: list[DocumentSummary] = []
    history: list[StatusHistoryOut] = []


# ------------------------------------------------------------ uploads -------
class UploadResponse(BaseModel):
    document: DocumentSummary
    text_preview: str
    extracted_fields: dict[str, Optional[str]]
    suggested_category: str
    linked_case_id: Optional[int] = None


# ----------------------------------------------------------- policies -------
class PolicyInfo(BaseModel):
    filename: str
    title: str
    size_bytes: int


class PolicyContent(PolicyInfo):
    content: str


# ---------------------------------------------------------- dashboard -------
class DashboardOut(BaseModel):
    total_cases: int
    pending_cases: int
    resolved_cases: int
    pa_cases: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    recent_cases: list[CaseSummary]


class AIStatus(BaseModel):
    enabled: bool
    available: bool
    model: str
    mode: str
    detail: str
