import logging
import json
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.models.entities import User, PurchaseVerification

logger = logging.getLogger(__name__)

def verify_google_play_purchase(
    db: Session,
    user: User,
    product_id: str,
    purchase_token: str,
    order_id: str = None
) -> Tuple[bool, str]:
    """
    Verifies purchase token with Google Play Android Publisher API.
    Guards against:
    - Token replay across different users
    - Unverified or cancelled purchases
    - Fake tokens in production environment
    """
    if product_id != settings.LIFETIME_PRODUCT_ID:
        return False, f"Invalid product ID: {product_id}. Expected {settings.LIFETIME_PRODUCT_ID}"

    # Check if this token was already used by another user
    existing_purchase = db.query(PurchaseVerification).filter(
        PurchaseVerification.purchase_token == purchase_token
    ).first()

    if existing_purchase:
        if existing_purchase.user_id != user.id:
            logger.warning(f"Purchase token re-use attempt! Token belongs to user {existing_purchase.user_id}, attempted by user {user.id}")
            return False, "This purchase is already registered to another account."
        elif existing_purchase.verified:
            # Already verified for this same user, restore entitlement
            user.is_premium = True
            db.commit()
            return True, "Purchase already verified. Premium status restored."

    # In Production: Query Google Play Developer API (purchases.products.get)
    if settings.APP_ENV == "production" and settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON:
        try:
            import httpx
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON,
                scopes=["https://www.googleapis.com/auth/androidpublisher"]
            )
            credentials.refresh(Request())
            access_token = credentials.token

            url = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{settings.GOOGLE_PLAY_PACKAGE_NAME}/purchases/products/{product_id}/tokens/{purchase_token}"
            
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers={"Authorization": f"Bearer {access_token}"})
                if res.status_code != 200:
                    logger.error(f"Google Play API error: {res.status_code} {res.text}")
                    return False, f"Google Play could not verify this purchase (Status {res.status_code})."

                payload = res.json()
                # purchaseState: 0 = Purchased, 1 = Canceled, 2 = Pending
                purchase_state = payload.get("purchaseState", -1)
                consumption_state = payload.get("consumptionState", -1)
                
                if purchase_state != 0:
                    return False, f"Purchase is not completed. Purchase state: {purchase_state}"

                # Acknowledge purchase if not acknowledged
                ack_state = payload.get("acknowledgementState", 0)
                if ack_state == 0:
                    ack_url = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{settings.GOOGLE_PLAY_PACKAGE_NAME}/purchases/products/{product_id}/tokens/{purchase_token}:acknowledge"
                    client.post(ack_url, headers={"Authorization": f"Bearer {access_token}"}, json={})

                # Save record
                verification = PurchaseVerification(
                    user_id=user.id,
                    order_id=payload.get("orderId", order_id),
                    purchase_token=purchase_token,
                    product_id=product_id,
                    purchase_time_millis=str(payload.get("purchaseTimeMillis", "")),
                    purchase_state=purchase_state,
                    verified=True,
                    verification_payload=json.dumps(payload)
                )
                db.add(verification)
                user.is_premium = True
                db.commit()
                return True, "Lifetime Premium verified and unlocked successfully!"

        except Exception as e:
            logger.error(f"Failed to connect to Google Play Publisher API: {e}")
            return False, "Failed to verify purchase with Google Play servers. Please try again."

    # Development / Staging Mode:
    # Allows sandbox and emulator testing with recognized test tokens
    if settings.APP_ENV != "production":
        logger.info(f"Running purchase verification in {settings.APP_ENV} mode for user {user.id}")
        
        # Verify that purchase_token is non-trivial
        if not purchase_token or len(purchase_token) < 8:
            return False, "Invalid test purchase token."

        verification = PurchaseVerification(
            user_id=user.id,
            order_id=order_id or f"GPA.DEV-{user.id}-12345",
            purchase_token=purchase_token,
            product_id=product_id,
            purchase_time_millis="1700000000000",
            purchase_state=0,
            verified=True,
            verification_payload=json.dumps({"mode": "sandbox", "productId": product_id})
        )
        db.add(verification)
        user.is_premium = True
        db.commit()
        return True, "Development purchase verified successfully! Premium unlocked."

    return False, "Production Google Play service credentials not configured on backend."
