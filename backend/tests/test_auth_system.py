"""
Tests for the Login/Sign Up authentication system.
Uses the shared test DB via conftest.py.
Covers: registration, login, duplicate email, wrong password,
        inactive account, /auth/me, /auth/forgot-password, and user-data isolation.
"""
import json as json_lib
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.entities import (
    User, UserProfile, ScanHistory, Payment, PurchaseVerification
)
# Import shared session from conftest via direct import (conftest injects it)
from backend.tests.conftest import TestingSessionLocal

client = TestClient(app)


# ---------- Fixtures ----------

@pytest.fixture(autouse=True)
def clear_auth_data():
    """Wipe auth-related rows before and after each auth test."""
    def _wipe():
        db = TestingSessionLocal()
        try:
            db.query(PurchaseVerification).delete()
            db.query(Payment).delete()
            db.query(ScanHistory).delete()
            db.query(UserProfile).delete()
            db.query(User).delete()
            db.commit()
        finally:
            db.close()

    _wipe()
    yield
    _wipe()


# ---------- Helper ----------

def _register(email="alice@test.com", password="pass123", name="Alice"):
    return client.post("/auth/register", json={"email": email, "password": password, "name": name})


# ---------- Registration tests ----------

def test_register_success():
    res = _register()
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data
    assert data["email"] == "alice@test.com"
    assert data["name"] == "Alice"
    assert data["is_premium"] is False


def test_register_duplicate_email():
    r1 = _register()
    assert r1.status_code == 200, r1.text
    r2 = _register()  # same email
    assert r2.status_code == 400
    assert "already registered" in r2.json()["detail"].lower()


def test_register_short_password():
    res = _register(password="abc")
    assert res.status_code == 422  # pydantic validation


def test_register_invalid_email():
    res = _register(email="notanemail")
    assert res.status_code == 422


def test_register_without_name_defaults_to_friend():
    res = client.post("/auth/register", json={"email": "bob@test.com", "password": "pass123"})
    assert res.status_code == 200, res.text
    assert res.json()["name"] == "Friend"


# ---------- Login tests ----------

def test_login_success():
    r = _register()
    assert r.status_code == 200, r.text
    res = client.post("/auth/login", json={"email": "alice@test.com", "password": "pass123"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data
    assert data["email"] == "alice@test.com"


def test_login_wrong_password():
    r = _register()
    assert r.status_code == 200, r.text
    res = client.post("/auth/login", json={"email": "alice@test.com", "password": "wrongpass"})
    assert res.status_code == 401
    assert "incorrect" in res.json()["detail"].lower()


def test_login_unknown_email():
    res = client.post("/auth/login", json={"email": "nobody@test.com", "password": "pass123"})
    assert res.status_code == 401


def test_login_inactive_account():
    reg = _register()
    assert reg.status_code == 200, reg.text
    user_id = reg.json()["user_id"]
    # Deactivate the user directly in DB
    db = TestingSessionLocal()
    try:
        u = db.query(User).filter(User.id == user_id).first()
        u.is_active = False
        db.commit()
    finally:
        db.close()
    res = client.post("/auth/login", json={"email": "alice@test.com", "password": "pass123"})
    assert res.status_code == 400
    assert "deactivated" in res.json()["detail"].lower()


# ---------- /auth/me ----------

def test_me_with_valid_token():
    reg = _register()
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    assert res.json()["email"] == "alice@test.com"


def test_me_without_token_returns_401():
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_with_invalid_token_returns_401():
    res = client.get("/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
    assert res.status_code == 401


# ---------- Forgot password ----------

def test_forgot_password_returns_503():
    res = client.post("/auth/forgot-password")
    assert res.status_code == 503
    assert "email service" in res.json()["detail"].lower()


# ---------- User-data isolation ----------

def test_scan_history_isolated_per_user():
    """Two registered users cannot see each other's scan history."""
    # Register user A
    reg_a = _register(email="a@test.com")
    assert reg_a.status_code == 200, reg_a.text
    token_a = reg_a.json()["access_token"]
    user_a_id = reg_a.json()["user_id"]

    # Register user B
    reg_b = _register(email="b@test.com")
    assert reg_b.status_code == 200, reg_b.text
    token_b = reg_b.json()["access_token"]

    # Seed a scan for user A directly in DB
    db = TestingSessionLocal()
    try:
        scan = ScanHistory(
            user_id=user_a_id,
            product_name="User A Biscuits",
            product_category="Snack",
            overall_status="GOOD",
            overall_score=80,
            extracted_ingredients=json_lib.dumps(["sugar"]),
            ingredient_details=json_lib.dumps([]),
            warnings=json_lib.dumps([]),
            recommendations=json_lib.dumps([]),
            ingredient_count=1,
        )
        db.add(scan)
        db.commit()
    finally:
        db.close()

    # User B fetches history — should not see user A's scan
    res_b = client.get("/history", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    names_b = [i["product_name"] for i in res_b.json()]
    assert "User A Biscuits" not in names_b

    # User A fetches history — should see their scan
    res_a = client.get("/history", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    names_a = [i["product_name"] for i in res_a.json()]
    assert "User A Biscuits" in names_a
