import os
import hmac
import hashlib
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.database.session import SessionLocal
from backend.app.models.entities import User, Payment

client = TestClient(app)

def get_auth_headers(email_prefix="rzp_test"):
    email = f"{email_prefix}_{uuid.uuid4().hex[:8]}@insideapp.in"
    reg = client.post("/auth/register", json={"email": email, "password": "pass123456"})
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_order_success_with_amount_and_currency():
    """
    Test Step 1: POST /api/create-order calls Razorpay API and returns order_id, amount, currency.
    """
    headers = get_auth_headers("create_success")
    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_test_rzp_std_001",
        "amount": 19900,
        "currency": "INR",
        "status": "created"
    }

    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        res = client.post("/api/create-order", headers=headers, json={
            "amount": 19900,
            "currency": "INR",
            "receipt": "rcpt_test_std_001"
        })
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["order_id"] == "order_test_rzp_std_001"
        assert data["amount"] == 19900
        assert data["currency"] == "INR"
        assert "key_id" in data

        # Verify Razorpay SDK client was called with correct arguments
        mock_client.order.create.assert_called_once()
        call_payload = mock_client.order.create.call_args[1]["data"]
        assert call_payload["amount"] == 19900
        assert call_payload["currency"] == "INR"
        assert call_payload["receipt"] == "rcpt_test_std_001"

def test_create_order_validation_minimum_amount():
    """
    Test Error Handling: POST /api/create-order returns 400 if amount < 100 paise.
    """
    headers = get_auth_headers("min_amount")
    res = client.post("/api/create-order", headers=headers, json={
        "amount": 99,  # Below 100 paise
        "currency": "INR"
    })
    assert res.status_code == 400
    assert "Minimum order amount is 100 paise" in res.text

def test_create_order_handles_razorpay_api_error_returns_500():
    """
    Test Error Handling: POST /api/create-order returns 500 when Razorpay API fails.
    """
    headers = get_auth_headers("api_error")
    mock_client = MagicMock()
    mock_client.order.create.side_effect = Exception("Razorpay API network timeout")

    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        res = client.post("/api/create-order", headers=headers, json={
            "amount": 19900,
            "currency": "INR"
        })
        assert res.status_code == 500
        assert "Payment gateway error" in res.text

def test_create_order_auth_failure_returns_401():
    """
    Test Error Handling: Invalid authentication token returns 401 Unauthorized.
    """
    headers = {"Authorization": "Bearer invalid_or_expired_jwt_token"}
    res = client.post("/api/create-order", headers=headers, json={"amount": 19900})
    assert res.status_code == 401

def test_verify_payment_success_with_valid_signature():
    """
    Test Step 3: POST /api/verify-payment verifies HMAC-SHA256 signature and returns success.
    """
    headers = get_auth_headers("verify_success")
    order_id = "order_test_rzp_std_verify_002"
    payment_id = "pay_test_rzp_std_verify_002"
    
    # Calculate genuine HMAC-SHA256 signature
    secret = settings.RAZORPAY_KEY_SECRET
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_signature = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    res = client.post("/api/verify-payment", headers=headers, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": valid_signature
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert data["order_id"] == order_id
    assert data["payment_id"] == payment_id

def test_verify_payment_invalid_signature_returns_400():
    """
    Test Error Handling: Signature mismatch returns 400 Bad Request and does NOT mark as paid.
    """
    headers = get_auth_headers("verify_invalid")
    order_id = "order_test_rzp_forged_003"
    payment_id = "pay_test_rzp_forged_003"
    forged_signature = "bad_forged_signature_hash_00000000000000000000000000000000"

    res = client.post("/api/verify-payment", headers=headers, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": forged_signature
    })
    assert res.status_code == 400
    assert "Invalid cryptographic signature" in res.text

def test_verify_payment_missing_fields_returns_400():
    """
    Test Error Handling: Missing required fields in verification request returns 400.
    """
    headers = get_auth_headers("verify_missing")
    # Missing razorpay_signature
    res1 = client.post("/api/verify-payment", headers=headers, json={
        "razorpay_order_id": "order_123",
        "razorpay_payment_id": "pay_123",
        "razorpay_signature": ""
    })
    assert res1.status_code == 400

    # Missing razorpay_payment_id
    res2 = client.post("/api/verify-payment", headers=headers, json={
        "razorpay_order_id": "order_123",
        "razorpay_payment_id": "",
        "razorpay_signature": "sig_123"
    })
    assert res2.status_code == 400

def test_checkout_frontend_page_served():
    """
    Test Step 2: GET /checkout serves HTML page with Razorpay checkout.js and checkout button.
    """
    res = client.get("/checkout")
    assert res.status_code == 200
    html = res.text
    assert "https://checkout.razorpay.com/v1/checkout.js" in html
    assert "pay-button" in html
    assert "/api/create-order" in html
    assert "/api/verify-payment" in html
    assert "payment.failed" in html
    assert "ondismiss" in html


def test_create_order_missing_credentials_returns_error():
    """Missing Razorpay credentials return a 500 error without exposing internal secrets."""
    headers = get_auth_headers("no_creds_user")
    with patch("backend.app.config.settings.RAZORPAY_KEY_ID", ""):
        res = client.post("/api/create-order", headers=headers, json={"amount": 19900})
        assert res.status_code == 500
        assert "Payment gateway error" in res.text


def test_create_order_auth_failure_sanitized_message():
    """Razorpay 401 Authentication failure returns user-friendly message without secrets."""
    headers = get_auth_headers("auth_fail_user")
    mock_client = MagicMock()
    mock_client.order.create.side_effect = Exception("401 Client Error: Authentication failed for url: https://api.razorpay.com/v1/orders")

    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        res = client.post("/api/create-order", headers=headers, json={"amount": 19900})
        assert res.status_code == 500
        assert "Payment gateway error: Razorpay API authentication failed" in res.text
        # Ensure secret key is NEVER exposed
        assert settings.RAZORPAY_KEY_SECRET not in res.text


def test_sanitized_credentials_strips_quotes_and_whitespace():
    """Credentials enclosed in accidental quotes or whitespace are stripped correctly."""
    from backend.app.services.razorpay_service import get_sanitized_credentials, get_key_mode
    with patch("backend.app.config.settings.RAZORPAY_KEY_ID", '  "rzp_test_clean123"  '), \
         patch("backend.app.config.settings.RAZORPAY_KEY_SECRET", "  'secret_clean456'  "):
        key_id, secret = get_sanitized_credentials()
        assert key_id == "rzp_test_clean123"
        assert secret == "secret_clean456"
        assert get_key_mode(key_id) == "TEST"

