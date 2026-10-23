
import datetime
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database.session import get_db
from backend.app.models.entities import User

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(
        password.encode("utf-8"), salt
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[datetime.timedelta] = None,
) -> str:
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError:
        return None


def _resolve_user(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
) -> Optional[User]:
    if not credentials or not credentials.credentials:
        return None

    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    user = _resolve_user(credentials, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_strict_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    return get_current_user(credentials, db)


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security_scheme
    ),
    db: Session = Depends(get_db),
) -> Optional[User]:
    return _resolve_user(credentials, db)
