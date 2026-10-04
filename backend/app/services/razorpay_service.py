import hmac
import hashlib
import logging
import datetime
from typing import Dict, Any, Optional
import razorpay
from backend.app.config import settings

logger = logging.getLogger(__name__)

def get_razorpay_client() -> razorpay.Client:
    """
    Returns an initialized Razorpay Client instance with configured LIVE / TEST credentials from .env.
    Raises ValueError if Razorpay keys are not configured.
    """
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ValueError("Razorpay Key ID or Secret is not configured. Please check your .env file.")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_order(user_id: int, amount_paise: int = 19900, currency: str = "INR") -> Dict[str, Any]:
    """
    Creates a real order on Razorpay for Inside Premium Lifetime (₹199 = 19900 paise).
    Communicates directly with the Razorpay API using credentials loaded from .env.
    """
    client = get_razorpay_client()
    timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    receipt = f"rcpt_inside_{user_id}_{timestamp}"
    
    order_data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt,
        "notes": {
            "user_id": str(user_id),
            "product": settings.PREMIUM_PRODUCT_ID,
            "app": settings.APP_NAME
        }
    }

    try:
        logger.info(f"[Razorpay Service] Creating order with Razorpay API for user_id={user_id}, amount={amount_paise} paise ({currency}), receipt={receipt}")
        rzp_order = client.order.create(data=order_data)
        if not rzp_order or "id" not in rzp_order:
            logger.error(f"[Razorpay Service] Invalid order response received: {rzp_order}")
            raise RuntimeError("Razorpay API returned an empty or invalid order response.")
        
        logger.info(f"[Razorpay Service] Order created successfully: order_id={rzp_order.get('id')}, amount={rzp_order.get('amount')}, status={rzp_order.get('status')}")
        return {
            "order_id": rzp_order["id"],
            "amount": rzp_order["amount"],
            "currency": rzp_order["currency"],
            "key_id": settings.RAZORPAY_KEY_ID,
            "product": settings.PREMIUM_PRODUCT_ID
        }
    except Exception as e:
        logger.error(f"[Razorpay Service] Order creation failed for user {user_id}: {type(e).__name__} - {str(e)}", exc_info=True)
        raise RuntimeError(f"Razorpay API order creation failed: {e}")

def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> bool:
    """
    Cryptographically verifies the Razorpay payment signature using HMAC SHA256
    with the RAZORPAY_KEY_SECRET.
    Never trusts frontend claims without signature verification.
    """
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False

    secret = settings.RAZORPAY_KEY_SECRET
    if not secret:
        logger.error("Cannot verify Razorpay signature: RAZORPAY_KEY_SECRET is empty.")
        return False

    # Official Razorpay Signature Formula:
    # signature = HMAC_SHA256(order_id + "|" + payment_id, secret)
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_signature, razorpay_signature)
    if not is_valid:
        logger.warning(f"Invalid Razorpay signature for order={razorpay_order_id}, payment={razorpay_payment_id}")
    return is_valid

def generate_test_signature(razorpay_order_id: str, razorpay_payment_id: str) -> str:
    """
    Generates a valid test signature for automated testing using the configured secret.
    """
    secret = settings.RAZORPAY_KEY_SECRET
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

def verify_webhook_signature(body_bytes: bytes, signature_header: str) -> bool:
    """
    Verifies the webhook signature sent in X-Razorpay-Signature header
    using RAZORPAY_WEBHOOK_SECRET.
    """
    secret = settings.RAZORPAY_WEBHOOK_SECRET or settings.RAZORPAY_KEY_SECRET
    if not secret or not signature_header:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)
