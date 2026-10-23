import hmac
import hashlib
import logging
import datetime
from typing import Dict, Any, Optional, Tuple
import razorpay
from backend.app.config import settings

logger = logging.getLogger(__name__)

def get_sanitized_credentials() -> Tuple[str, str]:
    """
    Retrieves and sanitizes Razorpay Key ID and Key Secret from settings.
    Strips leading/trailing whitespace, accidental quotes, and newline characters.
    """
    key_id = (settings.RAZORPAY_KEY_ID or "").strip().strip("'\"")
    key_secret = (settings.RAZORPAY_KEY_SECRET or "").strip().strip("'\"")
    return key_id, key_secret

def get_key_mode(key_id: str) -> str:
    """Returns 'TEST', 'LIVE', or 'UNKNOWN' based on the Key ID prefix."""
    if key_id.startswith("rzp_test_"):
        return "TEST"
    elif key_id.startswith("rzp_live_"):
        return "LIVE"
    return "UNKNOWN"

def get_razorpay_client() -> razorpay.Client:
    """
    Returns an initialized Razorpay Client instance with sanitized credentials.
    Raises ValueError if keys are empty or unconfigured.
    """
    key_id, key_secret = get_sanitized_credentials()
    if not key_id or not key_secret:
        logger.error("[Razorpay Service] Credentials missing: Key ID or Key Secret is empty.")
        raise ValueError("Razorpay Key ID or Secret is not configured. Please check your environment variables.")

    mode = get_key_mode(key_id)
    if mode == "UNKNOWN":
        logger.warning(f"[Razorpay Service] Key ID does not use standard prefix: {key_id[:8]}...")

    return razorpay.Client(auth=(key_id, key_secret))

def create_order(
    user_id: int,
    amount_paise: int = 19900,
    currency: str = "INR",
    receipt: Optional[str] = None,
    notes: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Creates an authentic order on Razorpay.
    Amount is strictly governed by the backend (default ₹199 = 19900 paise).
    Never logs or exposes secret credentials.
    """
    key_id, key_secret = get_sanitized_credentials()
    if not key_id or not key_secret:
        raise ValueError("Razorpay credentials are not configured.")

    client = get_razorpay_client()
    timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    order_receipt = receipt if (receipt and receipt.strip()) else f"rcpt_inside_{user_id}_{timestamp}"
    
    order_notes = {
        "user_id": str(user_id),
        "product": settings.PREMIUM_PRODUCT_ID,
        "app": settings.APP_NAME
    }
    if notes:
        order_notes.update(notes)

    order_data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": order_receipt,
        "notes": order_notes
    }

    mode = get_key_mode(key_id)

    try:
        logger.info(
            f"[Razorpay Service] Creating order for user_id={user_id}, amount={amount_paise} paise ({currency}), "
            f"mode={mode}, receipt={order_receipt}"
        )
        rzp_order = client.order.create(data=order_data)
        if not rzp_order or "id" not in rzp_order:
            logger.error("[Razorpay Service] Invalid order response received from gateway.")
            raise RuntimeError("Razorpay API returned an empty or invalid order response.")
        
        logger.info(f"[Razorpay Service] Order created successfully: order_id={rzp_order.get('id')}, status={rzp_order.get('status')}")
        return {
            "order_id": rzp_order["id"],
            "amount": rzp_order["amount"],
            "currency": rzp_order["currency"],
            "key_id": key_id,
            "product": settings.PREMIUM_PRODUCT_ID
        }
    except Exception as e:
        err_str = str(e)
        is_auth_failure = "authentication failed" in err_str.lower() or "unauthorized" in err_str.lower()
        is_conn_failure = "connection" in err_str.lower() or "timeout" in err_str.lower()

        # Log sanitized diagnostic without exposing keys or secrets
        if is_auth_failure:
            logger.error(
                f"[Razorpay Service] Authentication Failed with Razorpay API. "
                f"Diagnostic: mode={mode}, key_id_len={len(key_id)}, secret_len={len(key_secret)}. "
                "Verify that RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET match the same Razorpay mode (test vs live) and are active."
            )
            raise RuntimeError("Razorpay API authentication failed: Invalid or mismatched merchant credentials.")
        elif is_conn_failure:
            logger.error(f"[Razorpay Service] Network failure connecting to Razorpay API: {err_str}")
            raise RuntimeError("Razorpay API connection failed: Network timeout.")
        else:
            logger.error(f"[Razorpay Service] Order creation failed: {type(e).__name__} - {err_str}")
            raise RuntimeError(f"Razorpay API order creation failed: {err_str}")

def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> bool:
    """
    Cryptographically verifies the Razorpay payment signature using HMAC-SHA256
    with the sanitized RAZORPAY_KEY_SECRET.
    Never trusts frontend claims without signature verification.
    """
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return False

    _, secret = get_sanitized_credentials()
    if not secret:
        logger.error("[Razorpay Service] Cannot verify Razorpay signature: RAZORPAY_KEY_SECRET is empty.")
        return False

    # Formula: signature = HMAC_SHA256(order_id + "|" + payment_id, secret)
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_signature, razorpay_signature)
    if not is_valid:
        logger.warning(f"[Razorpay Service] Invalid signature for order={razorpay_order_id}, payment={razorpay_payment_id}")
    return is_valid

def generate_test_signature(razorpay_order_id: str, razorpay_payment_id: str) -> str:
    """
    Generates a valid test signature for automated testing using the configured secret.
    """
    _, secret = get_sanitized_credentials()
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

def verify_webhook_signature(body_bytes: bytes, signature_header: str) -> bool:
    """
    Verifies the webhook signature sent in X-Razorpay-Signature header
    using RAZORPAY_WEBHOOK_SECRET or RAZORPAY_KEY_SECRET.
    """
    webhook_secret = (settings.RAZORPAY_WEBHOOK_SECRET or "").strip().strip("'\"")
    _, key_secret = get_sanitized_credentials()
    secret = webhook_secret or key_secret

    if not secret or not signature_header:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)
