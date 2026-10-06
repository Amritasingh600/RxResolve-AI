"""
Simple local authentication.

- Passwords are hashed with PBKDF2-SHA256 and a random salt (Python standard
  library, no extra dependency).
- After login the user receives a random token that is stored in the
  `sessions` table. The frontend sends it back as `Authorization: Bearer <token>`.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

import config
from database import get_db
from models import SessionToken, User

PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        _algorithm, iterations, salt, expected = stored_hash.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
    except (ValueError, TypeError):
        return False
    # compare_digest avoids leaking information through timing differences
    return hmac.compare_digest(digest.hex(), expected)


def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, user: User) -> str:
    # Remove this user's expired sessions so the table does not grow forever.
    db.query(SessionToken).filter(
        SessionToken.user_id == user.id, SessionToken.expires_at < datetime.now()
    ).delete()

    token = secrets.token_hex(32)
    db.add(SessionToken(token=token, user_id=user.id, expires_at=datetime.now() + timedelta(hours=config.SESSION_HOURS)))
    db.commit()
    return token


def delete_session(db: Session, token: str) -> None:
    db.query(SessionToken).filter(SessionToken.token == token).delete()
    db.commit()


def _token_from_header(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in.")
    return authorization.removeprefix("Bearer ").strip()


def get_current_token(authorization: Optional[str] = Header(default=None)) -> str:
    return _token_from_header(authorization)


def get_current_user(
    token: str = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: returns the logged-in user or raises 401."""
    session = db.get(SessionToken, token)
    if session is None or session.expires_at < datetime.now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please log in again.")
    return session.user
