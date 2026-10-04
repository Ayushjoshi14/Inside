import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import User, UserProfile
from backend.app.schemas.api_schemas import ProfileUpdateRequest, ProfileResponse
from backend.app.security.auth import get_current_user
from backend.app.config import settings

router = APIRouter(tags=["User Profile"])

@router.get("/profile", response_model=ProfileResponse)
def get_user_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id, name="Friend")
        db.add(profile)
        db.commit()
        db.refresh(profile)

    scans_left = 999999 if user.is_premium else max(0, settings.FREE_SCAN_LIMIT - user.free_scans_used)

    return ProfileResponse(
        user_id=user.id,
        email=user.email,
        name=profile.name,
        diet_preference=profile.diet_preference or "NONE",
        avoid_ingredients=profile.avoid_list,
        allergens=profile.allergens_list,
        is_premium=user.is_premium,
        free_scans_used=user.free_scans_used,
        scans_count=user.scans_count,
        scans_left=scans_left
    )

@router.put("/profile", response_model=ProfileResponse)
def update_user_profile(
    data: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)

    if data.name is not None:
        profile.name = data.name.strip()
    if data.diet_preference is not None:
        valid_diets = ["NONE", "VEGETARIAN", "VEGAN"]
        diet_upper = data.diet_preference.upper().strip()
        if diet_upper in valid_diets:
            profile.diet_preference = diet_upper
    if data.avoid_ingredients is not None:
        profile.avoid_ingredients = json.dumps(data.avoid_ingredients)
    if data.allergens is not None:
        profile.allergens = json.dumps(data.allergens)

    db.commit()
    db.refresh(profile)

    scans_left = 999999 if user.is_premium else max(0, settings.FREE_SCAN_LIMIT - user.free_scans_used)

    return ProfileResponse(
        user_id=user.id,
        email=user.email,
        name=profile.name,
        diet_preference=profile.diet_preference,
        avoid_ingredients=profile.avoid_list,
        allergens=profile.allergens_list,
        is_premium=user.is_premium,
        free_scans_used=user.free_scans_used,
        scans_count=user.scans_count,
        scans_left=scans_left
    )

@router.delete("/account")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Deletes account, profile, scan history, and all stored user data
    per Google Play Account Deletion policy and user privacy rights.
    """
    db.delete(user)
    db.commit()
    return {"success": True, "message": "Your account and all associated scan data have been permanently deleted."}
