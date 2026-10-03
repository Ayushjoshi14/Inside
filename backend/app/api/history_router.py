import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import User, ScanHistory
from backend.app.schemas.api_schemas import HistoryItemResponse, ScanAnalysisResult, IngredientItemAnalysis
from backend.app.security.auth import get_current_user

router = APIRouter(prefix="/history", tags=["Scan History"])

@router.get("", response_model=List[HistoryItemResponse])
def get_user_scan_history(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    scans = db.query(ScanHistory).filter(
        ScanHistory.user_id == user.id
    ).order_by(ScanHistory.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for s in scans:
        try:
            ing_list = json.loads(s.extracted_ingredients) if s.extracted_ingredients else []
        except Exception:
            ing_list = []

        result.append(HistoryItemResponse(
            id=s.id,
            product_name=s.product_name,
            overall_status=s.overall_status,
            overall_score=s.overall_score,
            summary=s.summary,
            ingredient_count=len(ing_list),
            created_at=s.created_at.isoformat()
        ))
    return result

@router.get("/{scan_id}", response_model=ScanAnalysisResult)
def get_scan_detail(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    scan = db.query(ScanHistory).filter(
        ScanHistory.id == scan_id,
        ScanHistory.user_id == user.id
    ).first()

    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    try:
        details = json.loads(scan.ingredient_details) if scan.ingredient_details else []
        warns = json.loads(scan.warnings) if scan.warnings else []
        recs = json.loads(scan.recommendations) if scan.recommendations else []
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
        scan_id=scan.id,
        product_name=scan.product_name,
        overall_status=scan.overall_status,
        score=scan.overall_score,
        summary=scan.summary or "",
        ingredients=formatted_ingredients,
        warnings=warns,
        recommendations=recs,
        raw_ocr_text=scan.raw_ocr_text,
        created_at=scan.created_at.isoformat()
    )

@router.delete("/{scan_id}")
def delete_single_scan(
    scan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    scan = db.query(ScanHistory).filter(
        ScanHistory.id == scan_id,
        ScanHistory.user_id == user.id
    ).first()

    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    db.delete(scan)
    db.commit()
    return {"success": True, "message": "Scan deleted successfully"}

@router.delete("")
def clear_all_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(ScanHistory).filter(ScanHistory.user_id == user.id).delete()
    db.commit()
    return {"success": True, "message": "All scan history cleared successfully"}
