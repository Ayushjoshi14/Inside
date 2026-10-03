from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import User, UserProfile
from backend.app.schemas.api_schemas import UserRegister, UserLogin, TokenResponse
from backend.app.security.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    new_user = User(
        email=data.email.lower().strip(),
        hashed_password=hash_password(data.password),
        is_active=True,
        is_premium=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create default user profile
    profile = UserProfile(
        user_id=new_user.id,
        name=data.name or "Friend",
        diet_preference="NONE",
        avoid_ingredients="[]",
        allergens="[]"
    )
    db.add(profile)
    db.commit()

    token = create_access_token({"sub": str(new_user.id), "email": new_user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=new_user.id,
        email=new_user.email,
        name=profile.name,
        is_premium=new_user.is_premium
    )

@router.post("/login", response_model=TokenResponse)
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is deactivated")

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    name = profile.name if profile else "Friend"

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        name=name,
        is_premium=user.is_premium
    )
