"""Policy knowledge base endpoints: list, read, search and add sample policy documents."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

import config
from auth import get_current_user
from document_processor import DocumentError, extract_text, validate_upload
from models import User
from policy_search import list_policies, read_policy, search_policies
from routers.documents import read_upload
from schemas import PolicyContent, PolicyInfo, PolicyMatch

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=list[PolicyInfo])
def get_policies(user: User = Depends(get_current_user)):
    return list_policies()


@router.get("/search", response_model=list[PolicyMatch])
def search(q: str = Query(min_length=1, max_length=300), top_k: int = Query(default=5, ge=1, le=20), user: User = Depends(get_current_user)):
    return search_policies(q, top_k=top_k)


@router.get("/{filename}", response_model=PolicyContent)
def get_policy(filename: str, user: User = Depends(get_current_user)):
    policy = read_policy(filename)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy document '{filename}' was not found.")
    return policy


@router.post("/upload", response_model=PolicyInfo, status_code=status.HTTP_201_CREATED)
def upload_policy(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Add a (fictional / sample) policy to the knowledge base. The text is saved as a .txt file."""
    content = read_upload(file)
    try:
        filename, extension = validate_upload(file.filename or "", content)
        text = extract_text(content, extension)
    except DocumentError as error:
        raise HTTPException(status_code=400, detail=str(error))

    policy_dir = Path(config.POLICY_DIR)
    policy_dir.mkdir(parents=True, exist_ok=True)
    target = policy_dir / (Path(filename).stem + ".txt")
    if target.exists():
        raise HTTPException(status_code=409, detail=f"A policy named '{target.name}' already exists. Rename the file and try again.")

    target.write_text(text, encoding="utf-8")
    return read_policy(target.name)
