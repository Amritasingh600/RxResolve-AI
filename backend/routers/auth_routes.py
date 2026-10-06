"""Login / logout endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import authenticate, create_session, delete_session, get_current_token, get_current_user
from database import get_db
from models import User
from schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    token = create_session(db, user)
    return LoginResponse(token=token, user=UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(get_current_token), db: Session = Depends(get_db)):
    delete_session(db, token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
