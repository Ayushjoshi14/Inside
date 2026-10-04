import datetime
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import User, Payment
from backend.app.schemas.api_schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    PremiumStatusResponse
)
from backend.app.security.auth import get_current_user
from backend.app.config import settings
from backend.app.services.razorpay_service import (
    create_order,
    verify_payment_signature,
    verify_webhook_signature
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Razorpay Payments"])

@router.post("/create-order", response_model=CreateOrderResponse)
def create_payment_order(
    request: Optional[CreateOrderRequest] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a Razorpay Order for ₹199 Lifetime Premium (19900 paise) or custom validated amount (min 100 paise).
    Amount is strictly governed and validated by the backend.
    """
    if user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account already has Inside Lifetime Premium activated."
        )

    target_amount = request.amount if (request and request.amount is not None) else settings.PREMIUM_PRICE_PAISE
    target_currency = request.currency if (request and request.currency) else settings.PREMIUM_CURRENCY
    target_product = request.product if (request and request.product) else settings.PREMIUM_PRODUCT_ID

    # Minimum amount validation (100 paise = ₹1.00)
    if target_amount < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum order amount is 100 paise (₹1.00)."
        )

    # Check for an existing pending CREATED order in the last 15 minutes with matching parameters (ignoring fake IDs)
    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=15)
    existing_order = db.query(Payment).filter(
        Payment.user_id == user.id,
        Payment.status == "CREATED",
        Payment.amount == target_amount,
        Payment.product == target_product,
        ~Payment.razorpay_order_id.like("order_test_%"),
        Payment.created_at >= cutoff_time
    ).order_by(Payment.created_at.desc()).first()

    if existing_order:
        logger.info(f"Reusing active pending order: {existing_order.razorpay_order_id} for user {user.id}")
        return CreateOrderResponse(
            order_id=existing_order.razorpay_order_id,
            amount=existing_order.amount,
            currency=existing_order.currency,
            key_id=settings.RAZORPAY_KEY_ID,
            product=existing_order.product
        )

    # Create fresh authentic order with Razorpay service API
    try:
        order_data = create_order(
            user_id=user.id,
            amount_paise=target_amount,
            currency=target_currency
        )
    except Exception as e:
        logger.error(f"Failed to create Razorpay order for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment gateway error: Could not create Razorpay order. ({str(e)})"
        )

    new_payment = Payment(
        user_id=user.id,
        razorpay_order_id=order_data["order_id"],
        amount=target_amount,
        currency=target_currency,
        status="CREATED",
        product=target_product,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    return CreateOrderResponse(
        order_id=new_payment.razorpay_order_id,
        amount=new_payment.amount,
        currency=new_payment.currency,
        key_id=settings.RAZORPAY_KEY_ID,
        product=new_payment.product
    )

@router.post("/verify", response_model=PaymentVerifyResponse)
@router.post("/verify-payment", response_model=PaymentVerifyResponse)
def verify_payment(
    request: PaymentVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifies Razorpay payment signature and order attributes atomically.
    Unlocks Inside Lifetime Premium upon genuine verification.
    """
    # 1. Validate required fields
    if not request.razorpay_order_id or not request.razorpay_order_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required parameter: razorpay_order_id.")
    if not request.razorpay_payment_id or not request.razorpay_payment_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required parameter: razorpay_payment_id.")
    if not request.razorpay_signature or not request.razorpay_signature.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required parameter: razorpay_signature.")

    # 2. Verify cryptographic signature with Razorpay Secret
    is_valid_sig = verify_payment_signature(
        razorpay_order_id=request.razorpay_order_id.strip(),
        razorpay_payment_id=request.razorpay_payment_id.strip(),
        razorpay_signature=request.razorpay_signature.strip()
    )

    if not is_valid_sig:
        logger.warning(f"Payment verification rejected: Invalid signature for user {user.id}, order={request.razorpay_order_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed: Invalid cryptographic signature."
        )

    # 2. Atomic database verification & activation
    try:
        # Row lock payment record
        payment = db.query(Payment).filter(
            Payment.razorpay_order_id == request.razorpay_order_id
        ).with_for_update().first()

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment order record not found in system."
            )

        # Ensure order belongs to the authenticated user
        if payment.user_id != user.id:
            logger.error(f"Security Alert: User {user.id} tried to claim payment belonging to User {payment.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This payment order belongs to a different user account."
            )

        # Verify order parameters
        if payment.product != settings.PREMIUM_PRODUCT_ID or payment.amount != settings.PREMIUM_PRICE_PAISE or payment.currency != settings.PREMIUM_CURRENCY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment order parameter tampering detected."
            )

        # Idempotency check: Already processed?
        if payment.status in ["VERIFIED", "CAPTURED"]:
            logger.info(f"Idempotent verification replay for payment {payment.razorpay_payment_id}")
            return PaymentVerifyResponse(
                success=True,
                is_premium=True,
                message="Inside Lifetime Premium is already active.",
                order_id=payment.razorpay_order_id,
                payment_id=payment.razorpay_payment_id
            )

        # Mark payment as CAPTURED and activate Premium
        payment.razorpay_payment_id = request.razorpay_payment_id
        payment.razorpay_signature = request.razorpay_signature
        payment.status = "CAPTURED"
        payment.updated_at = datetime.datetime.now(datetime.timezone.utc)

        # Lock and update user record
        locked_user = db.query(User).filter(User.id == user.id).with_for_update().first()
        locked_user.is_premium = True
        locked_user.premium_granted_at = datetime.datetime.now(datetime.timezone.utc)

        db.commit()
        db.refresh(locked_user)
        logger.info(f"Premium activated successfully for user {user.id} via Razorpay payment {request.razorpay_payment_id}")

        return PaymentVerifyResponse(
            success=True,
            is_premium=True,
            message="Inside Lifetime Premium activated! Unlimited scans unlocked.",
            order_id=payment.razorpay_order_id,
            payment_id=payment.razorpay_payment_id
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Payment verification transaction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed due to database error: {str(e)}"
        )

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature")
):
    """
    Razorpay Webhook handler for server-to-server confirmation of payments.
    Ensures payment recovery and idempotent activation even if client disconnected.
    """
    body_bytes = await request.body()
    
    if not x_razorpay_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header."
        )

    is_valid = verify_webhook_signature(body_bytes, x_razorpay_signature)
    if not is_valid:
        logger.warning("Razorpay webhook signature verification failed.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature."
        )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
        event = payload.get("event")
        logger.info(f"Received verified Razorpay webhook event: {event}")

        if event in ["payment.captured", "order.paid"]:
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")

            if order_id:
                payment = db.query(Payment).filter(
                    Payment.razorpay_order_id == order_id
                ).with_for_update().first()

                if payment and payment.status != "CAPTURED":
                    payment.razorpay_payment_id = payment_id
                    payment.status = "CAPTURED"
                    payment.updated_at = datetime.datetime.now(datetime.timezone.utc)

                    user = db.query(User).filter(User.id == payment.user_id).with_for_update().first()
                    if user:
                        user.is_premium = True
                        user.premium_granted_at = datetime.datetime.now(datetime.timezone.utc)

                    db.commit()
                    logger.info(f"Webhook successfully updated payment and unlocked premium for user {payment.user_id}")

        return {"status": "ok", "message": "Webhook processed successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing Razorpay webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing error: {str(e)}"
        )

@router.get("/status", response_model=PremiumStatusResponse)
def get_payment_status(user: User = Depends(get_current_user)):
    """
    Retrieves the authoritative premium and pricing status.
    """
    scans_left = 999999 if user.is_premium else max(0, settings.FREE_SCAN_LIMIT - user.free_scans_used)
    return PremiumStatusResponse(
        is_premium=user.is_premium,
        free_scans_used=user.free_scans_used,
        scans_count=user.scans_count,
        scans_left=scans_left,
        product_id=settings.PREMIUM_PRODUCT_ID,
        price_inr=199,
        price_paise=settings.PREMIUM_PRICE_PAISE,
        currency=settings.PREMIUM_CURRENCY,
        key_id=settings.RAZORPAY_KEY_ID
    )
