from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import User
from backend.app.schemas.api_schemas import BillingVerifyRequest, BillingVerifyResponse, PremiumStatusResponse
from backend.app.security.auth import get_current_user
from backend.app.billing.play_service import verify_google_play_purchase
from backend.app.config import settings

router = APIRouter(prefix="/billing", tags=["Billing & Premium"])

@router.post("/verify", response_model=BillingVerifyResponse)
def verify_purchase(
    request: BillingVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success, message = verify_google_play_purchase(
        db=db,
        user=user,
        product_id=request.product_id,
        purchase_token=request.purchase_token,
        order_id=request.order_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return BillingVerifyResponse(
        success=True,
        is_premium=user.is_premium,
        message=message,
        order_id=request.order_id
    )

@router.get("/status", response_model=PremiumStatusResponse)
def get_premium_status(user: User = Depends(get_current_user)):
    scans_left = 999999 if user.is_premium else max(0, settings.FREE_SCAN_LIMIT - user.free_scans_used)
    return PremiumStatusResponse(
        is_premium=user.is_premium,
        free_scans_used=user.free_scans_used,
        scans_count=user.scans_count,
        scans_left=scans_left,
        product_id=settings.LIFETIME_PRODUCT_ID,
        price_inr=199
    )
