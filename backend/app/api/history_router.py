import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import User, ScanHistory
from backend.app.schemas.api_schemas import (
    HistoryItemResponse,
    ScanAnalysisResult,
    IngredientItemAnalysis,
    UpdateScanDecisionRequest,
)
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

        ing_count = s.ingredient_count if (s.ingredient_count is not None and s.ingredient_count > 0) else len(ing_list)

        try:
            nutri = json.loads(s.nutrition_facts) if getattr(s, 'nutrition_facts', None) and s.nutrition_facts else {}
        except Exception:
            nutri = {}

        result.append(HistoryItemResponse(
            id=s.id,
            product_name=s.product_name,
            product_category=s.product_category or "Food Product",
            overall_status=s.overall_status,
            overall_score=s.overall_score,
            summary=s.summary,
            ingredient_count=ing_count,
            created_at=s.created_at.isoformat(),
            custom_product_name=s.custom_product_name,
            purchase_decision=s.purchase_decision,
            nutrition_facts=nutri,
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
        product_category=scan.product_category or "Food Product",
        overall_status=scan.overall_status,
        score=scan.overall_score,
        summary=scan.summary or "",
        ingredients=formatted_ingredients,
        warnings=warns,
        recommendations=recs,
        raw_ocr_text=scan.raw_ocr_text,
        created_at=scan.created_at.isoformat(),
        is_compatible=True,
        compatibility_status="COMPATIBLE",
        custom_product_name=scan.custom_product_name,
        purchase_decision=scan.purchase_decision,
        nutrition_facts=json.loads(scan.nutrition_facts) if getattr(scan, 'nutrition_facts', None) and scan.nutrition_facts else {},
    )

@router.patch("/{scan_id}")
def update_scan_decision_or_name(
    scan_id: int,
    payload: UpdateScanDecisionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    scan = db.query(ScanHistory).filter(
        ScanHistory.id == scan_id,
        ScanHistory.user_id == user.id
    ).first()

    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    if payload.custom_product_name is not None:
        name = payload.custom_product_name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Custom product name cannot be empty"
            )
        scan.custom_product_name = name

    if payload.purchase_decision is not None:
        decision = payload.purchase_decision.strip().upper()
        if decision not in ("YES", "NO"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Purchase decision must be 'YES' or 'NO'"
            )
        scan.purchase_decision = decision

    db.commit()
    db.refresh(scan)
    return {
        "success": True,
        "scan_id": scan.id,
        "custom_product_name": scan.custom_product_name,
        "purchase_decision": scan.purchase_decision,
        "product_name": scan.product_name,
        "product_category": scan.product_category,
        "score": scan.overall_score,
    }

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
