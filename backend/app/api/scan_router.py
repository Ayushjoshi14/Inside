import json
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import User, UserProfile, ScanHistory
from backend.app.schemas.api_schemas import ScanTextRequest, ScanAnalysisResult, IngredientItemAnalysis
from backend.app.security.auth import get_optional_user
from backend.app.ocr.processor import process_raw_label
from backend.app.services.analysis_engine import analyze_ingredients_list
from backend.app.config import settings

router = APIRouter(tags=["Scanning & Analysis"])

@router.post("/scan", response_model=ScanAnalysisResult)
def scan_and_analyze(
    request: ScanTextRequest,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    if not request.ocr_text or len(request.ocr_text.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image or text isn't clear enough. Please ensure the ingredient list is readable."
        )

    profile = None
    if user:
        # Check free tier limits
        if not user.is_premium and user.scans_count >= settings.FREE_SCAN_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"You have used your {settings.FREE_SCAN_LIMIT} free scans. Upgrade to Inside Lifetime Premium for unlimited scans."
            )
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

    # Process OCR text
    parsed_ingredients, cleaned_section = process_raw_label(request.ocr_text)

    if not parsed_ingredients:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not detect any ingredient items. Try adjusting camera angle or lighting."
        )

    # Run hybrid analysis engine
    analysis_data = analyze_ingredients_list(db, parsed_ingredients, profile)

    # Save to history if user is authenticated
    scan_id = None
    if user:
        history_entry = ScanHistory(
            user_id=user.id,
            product_name=request.product_name or "Scanned Product",
            raw_ocr_text=request.ocr_text[:2000],  # Truncate internal raw debug text
            extracted_ingredients=json.dumps(parsed_ingredients),
            overall_status=analysis_data["overall_status"],
            overall_score=analysis_data["score"],
            summary=analysis_data["summary"],
            ingredient_details=json.dumps(analysis_data["ingredients"]),
            warnings=json.dumps(analysis_data["warnings"]),
            recommendations=json.dumps(analysis_data["recommendations"]),
            created_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(history_entry)
        user.scans_count += 1
        db.commit()
        db.refresh(history_entry)
        scan_id = history_entry.id

    formatted_ingredients = [
        IngredientItemAnalysis(
            name=ing["name"],
            normalized_name=ing["normalized_name"],
            status=ing["status"],
            reason=ing["reason"],
            category=ing["category"],
            vegetarian_status=ing.get("vegetarian_status", "YES"),
            vegan_status=ing.get("vegan_status", "YES"),
            allergen_info=ing.get("allergen_info")
        )
        for ing in analysis_data["ingredients"]
    ]

    return ScanAnalysisResult(
        scan_id=scan_id,
        product_name=request.product_name or "Scanned Product",
        overall_status=analysis_data["overall_status"],
        score=analysis_data["score"],
        summary=analysis_data["summary"],
        ingredients=formatted_ingredients,
        warnings=analysis_data["warnings"],
        recommendations=analysis_data["recommendations"],
        raw_ocr_text=cleaned_section,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
