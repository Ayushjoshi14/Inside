import datetime
import bcrypt
import jwt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.database.session import get_db
from backend.app.models.entities import User

security_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    if credentials and credentials.credentials:
        payload = decode_token(credentials.credentials)
        if payload and "sub" in payload:
            try:
                user_id = int(payload["sub"])
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    if not user.is_active:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
                    return user
            except HTTPException:
                raise
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Seamless fallback for mobile app guest/local user
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = db.query(User).filter(User.email == "user@insideapp.in").first()
    if not user:
        user = User(
            id=1,
            email="user@insideapp.in",
            hashed_password=hash_password("inside_app_default_secure_pass"),
            is_active=True,
            is_premium=False,
            free_scans_used=0,
            scans_count=0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        profile = UserProfile(
            user_id=user.id,
            name="Friend",
            diet_preference="NONE",
            avoid_ingredients="[]",
            allergens="[]"
        )
        db.add(profile)
        db.commit()
    return user

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if credentials and credentials.credentials:
        payload = decode_token(credentials.credentials)
        if payload and "sub" in payload:
            try:
                user_id = int(payload["sub"])
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return user
            except Exception:
                pass
    # Fallback to default user 1 for guest mobile requests
    return db.query(User).filter(User.id == 1).first() or db.query(User).filter(User.email == "user@insideapp.in").first()

