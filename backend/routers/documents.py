"""Document upload: validate the file, extract its text and suggest case fields."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

import config
from auth import get_current_user
from classifier import classify_rejection
from database import get_db
from document_processor import DocumentError, extract_fields, extract_text, validate_upload
from models import Case, Document, User
from schemas import DocumentOut, DocumentSummary, UploadResponse

router = APIRouter(prefix="/api", tags=["documents"])

MAX_STORED_CHARACTERS = 200_000


def read_upload(file: UploadFile) -> bytes:
    """Read at most MAX_UPLOAD_BYTES + 1 bytes so huge files are rejected without loading them fully."""
    content = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,  # "Content Too Large"
            detail=f"File is too large. Maximum size is {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    return content


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    case_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = None
    if case_id is not None:
        case = db.get(Case, case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"Case #{case_id} was not found.")

    content = read_upload(file)
    try:
        filename, extension = validate_upload(file.filename or "", content)
        text = extract_text(content, extension)
    except DocumentError as error:
        raise HTTPException(status_code=400, detail=str(error))

    document = Document(filename=filename, file_type=extension.lstrip("."), content=text[:MAX_STORED_CHARACTERS], uploaded_by=user.username)
    db.add(document)
    if case is not None:
        case.documents.append(document)
    db.commit()
    db.refresh(document)

    fields = extract_fields(text)
    suggested = classify_rejection(fields.get("rejection_code") or "", fields.get("rejection_message") or text[:3000])

    return UploadResponse(
        document=DocumentSummary.model_validate(document),
        text_preview=text[:3000],
        extracted_fields=fields,
        suggested_category=suggested.category,
        linked_case_id=case.id if case else None,
    )


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Document).order_by(Document.uploaded_at.desc()).limit(200).all()


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document #{document_id} was not found.")
    return document
