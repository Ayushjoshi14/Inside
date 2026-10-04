import json
import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import User, UserProfile, ScanHistory
from backend.app.schemas.api_schemas import ScanTextRequest, ScanAnalysisResult, IngredientItemAnalysis
from backend.app.security.auth import get_optional_user
from backend.app.ocr.processor import process_raw_label
from backend.app.services.analysis_engine import analyze_ingredients_list
from backend.app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scanning & Analysis"])

@router.post("/scan", response_model=ScanAnalysisResult)
def scan_and_analyze(
    request: ScanTextRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    # Quick sanity check on OCR text input
    if not request.ocr_text or len(request.ocr_text.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image or text isn't clear enough. Please ensure the ingredient list is readable."
        )

    # 1. Handle Idempotency (Retry protection)
    if user and request.idempotency_key:
        existing_scan = db.query(ScanHistory).filter(
            ScanHistory.user_id == user.id,
            ScanHistory.idempotency_key == request.idempotency_key
        ).first()

        if existing_scan:
            logger.info(f"Idempotent retry detected for key: {request.idempotency_key}. Returning cached scan.")
            try:
                details = json.loads(existing_scan.ingredient_details) if existing_scan.ingredient_details else []
                warns = json.loads(existing_scan.warnings) if existing_scan.warnings else []
                recs = json.loads(existing_scan.recommendations) if existing_scan.recommendations else []
            except Exception:
                details, warns, recs = [], [], []

            formatted_ingredients = [
                IngredientItemAnalysis(
                    name=ing.get("name", "Unknown"),
                    normalized_name=ing.get("normalized_name", "Unknown"),
                    status=ing.get("status", "GOOD"),
                    reason=ing.get("reason", ""),
                    category=ing.get("category", "General"),
                    vegetarian_status=ing.get("vegetarian_status", "YES"),
                    vegan_status=ing.get("vegan_status", "YES"),
                    allergen_info=ing.get("allergen_info")
                )
                for ing in details
            ]

            return ScanAnalysisResult(
                scan_id=existing_scan.id,
                product_name=existing_scan.product_name,
                product_category=existing_scan.product_category or "Food Product",
                ingredient_count=existing_scan.ingredient_count or len(formatted_ingredients),
                overall_status=existing_scan.overall_status,
                score=existing_scan.overall_score,
                summary=existing_scan.summary or "",
                ingredients=formatted_ingredients,
                warnings=warns,
                recommendations=recs,
                raw_ocr_text=existing_scan.raw_ocr_text,
                created_at=existing_scan.created_at.isoformat()
            )

    scan_id = None
    detected_product_name = "Food Product"
    detected_product_category = "Food Product"
    cleaned_section = request.ocr_text
    analysis_data = None

    # 2. Single Atomic Database Transaction
    try:
        locked_user = None
        user_profile = None

        if user:
            # Step 1 & 2: Lock the authenticated user's row & re-read authoritative values
            locked_user = (
                db.query(User)
                .filter(User.id == user.id)
                .with_for_update()
                .first()
            )
            if not locked_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User account not found."
                )

            # Step 3: Check scan permission under lock
            if not locked_user.is_premium and locked_user.free_scans_used >= settings.FREE_SCAN_LIMIT:
                logger.warning(f"Scan rejected: User {locked_user.id} has exhausted all {settings.FREE_SCAN_LIMIT} free scans.")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "FREE_SCANS_EXHAUSTED",
                        "message": f"You've used all {settings.FREE_SCAN_LIMIT} free scans. Upgrade to Inside Lifetime Premium for unlimited scans."
                    }
                )

            user_profile = db.query(UserProfile).filter(UserProfile.user_id == locked_user.id).first()

        # Step 4: Perform OCR and AI analysis
        parsed_ingredients, cleaned_section = process_raw_label(request.ocr_text)

        if not parsed_ingredients:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not detect any ingredient items. Try adjusting camera angle or lighting."
            )

        analysis_data = analyze_ingredients_list(
            db=db,
            raw_ingredients=parsed_ingredients,
            profile=user_profile,
            provided_product_name=request.product_name,
            provided_product_category=request.product_category,
            raw_ocr_text=request.ocr_text
        )

        detected_product_name = analysis_data["product_name"]
        detected_product_category = analysis_data["product_category"]

        # Step 5: After analysis succeeds, create ScanHistory record in the same transaction
        if locked_user:
            ingredient_count = len(analysis_data["ingredients"])
            history_entry = ScanHistory(
                user_id=locked_user.id,
                product_name=detected_product_name,
                product_category=detected_product_category,
                ingredient_count=ingredient_count,
                idempotency_key=request.idempotency_key,
                raw_ocr_text=cleaned_section[:2000],
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

            # Step 6: Atomically increment free_scans_used for non-premium under condition
            if not locked_user.is_premium:
                rows_updated = db.query(User).filter(
                    User.id == locked_user.id,
                    User.free_scans_used < settings.FREE_SCAN_LIMIT
                ).update(
                    {
                        User.free_scans_used: User.free_scans_used + 1,
                        User.scans_count: User.scans_count + 1
                    },
                    synchronize_session="fetch"
                )
                if rows_updated == 0:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error": "FREE_SCANS_EXHAUSTED",
                            "message": f"You've used all {settings.FREE_SCAN_LIMIT} free scans. Upgrade to Inside Lifetime Premium for unlimited scans."
                        }
                    )
            else:
                db.query(User).filter(User.id == locked_user.id).update(
                    {User.scans_count: User.scans_count + 1},
                    synchronize_session="fetch"
                )

            # Step 7: Commit the atomic transaction
            db.commit()
            db.refresh(history_entry)
            scan_id = history_entry.id
            logger.info(f"Scan completed atomically: user={locked_user.id}, free_scans_used={locked_user.free_scans_used}, scan_id={scan_id}")

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        # If a concurrent race hit the database CHECK constraint (e.g. check_free_scans_limit)
        err_msg = str(e)
        if "check_free_scans_limit" in err_msg or "CHECK constraint failed" in err_msg:
            logger.warning(f"Concurrent scan limit enforced by DB constraint: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "FREE_SCANS_EXHAUSTED",
                    "message": f"You've used all {settings.FREE_SCAN_LIMIT} free scans. Upgrade to Inside Lifetime Premium for unlimited scans."
                }
            )
        logger.error(f"Scan analysis/transaction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed during processing: {str(e)}"
        )

    # Step 8: Return the successful scan result
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
        product_name=detected_product_name,
        product_category=detected_product_category,
        ingredient_count=len(formatted_ingredients),
        overall_status=analysis_data["overall_status"],
        score=analysis_data["score"],
        summary=analysis_data["summary"],
        ingredients=formatted_ingredients,
        warnings=analysis_data["warnings"],
        recommendations=analysis_data["recommendations"],
        raw_ocr_text=cleaned_section,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
