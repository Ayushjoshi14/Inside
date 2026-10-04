import pytest
import datetime
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.database.session import Base, get_db
from backend.app.ocr.processor import process_raw_label, split_into_ingredients, clean_raw_ocr
from backend.app.services.normalization import normalize_ingredient_name
from backend.app.services.analysis_engine import evaluate_personalized_status, analyze_ingredients_list
from backend.app.models.entities import UserProfile, Ingredient

# Test database
TEST_DB_URL = "sqlite:///./test_inside.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    # Seed test ingredients
    db = TestingSessionLocal()
    if db.query(Ingredient).count() == 0:
        db.add(Ingredient(
            name="Sugar",
            normalized_name="Sugar",
            category="Sugar",
            caution_level="CAUTION",
            vegetarian_status="YES",
            vegan_status="YES",
            explanation="Added caloric sweetener."
        ))
        db.add(Ingredient(
            name="Citric Acid",
            normalized_name="Citric Acid",
            ins_number="330",
            e_number="E330",
            category="Acidity regulator",
            caution_level="GOOD",
            vegetarian_status="YES",
            vegan_status="YES",
            explanation="Naturally occurring acidulant."
        ))
        db.add(Ingredient(
            name="Gelatin",
            normalized_name="Gelatin",
            category="Thickener",
            caution_level="CAUTION",
            vegetarian_status="NO",
            vegan_status="NO",
            explanation="Animal collagen derived additive."
        ))
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)

client = TestClient(app)

# 1. OCR Unit Tests
def test_ocr_cleaner_and_parenthesis_splitting():
    raw_label = "INGREDIENTS: Refined Wheat Flour (52%), Palm Oil, Sugar, Citric Acd, INS 322, Salt. Contains Added Flavour."
    ingredients, section = process_raw_label(raw_label)
    assert len(ingredients) >= 4
    # Check that parenthesis was preserved
    assert any("Refined Wheat Flour" in item for item in ingredients)
    assert any("Palm Oil" in item for item in ingredients)
    assert any("Citric Acd" in item for item in ingredients)

def test_ocr_packaging_noise_removal():
    raw_clutter = "BEST BEFORE 12 MONTHS FROM MFG. BATCH NO: B123. INGREDIENTS: Whole Wheat Flour, Water, Salt. MRP RS 50.00"
    ingredients, section = process_raw_label(raw_clutter)
    assert "BATCH NO" not in section
    assert "MRP" not in section
    assert len(ingredients) == 3
    assert "Whole Wheat Flour" in ingredients[0]

# 2. Normalization Unit Tests
def test_normalization_ins_code():
    display, norm, conf = normalize_ingredient_name("Emulsifier (INS 322i)")
    assert "Lecithin" in display
    assert "Lecithin" in norm
    assert conf == "HIGH"

def test_normalization_typo_correction():
    display, norm, conf = normalize_ingredient_name("Citric Acd")
    assert "Citric Acid" in norm
    assert conf == "MEDIUM"

# 3. Personalization Engine Unit Tests
def test_personalization_vegetarian():
    profile = UserProfile(diet_preference="VEGETARIAN", avoid_ingredients="[]", allergens="[]")
    status, reason = evaluate_personalized_status(
        base_status="GOOD",
        base_reason="Common thickener",
        veg_status="NO",
        vegan_status="NO",
        allergen_info="Bovine",
        ingredient_name="Gelatin",
        profile=profile
    )
    assert status == "AVOID"
    assert "Non-vegetarian" in reason

def test_personalization_custom_avoid_list():
    profile = UserProfile(diet_preference="NONE", avoid_ingredients='["Palm Oil"]', allergens="[]")
    status, reason = evaluate_personalized_status(
        base_status="CAUTION",
        base_reason="Tropical oil",
        veg_status="YES",
        vegan_status="YES",
        allergen_info=None,
        ingredient_name="Palm Oil",
        profile=profile
    )
    assert status == "AVOID"
    assert "custom avoid list" in reason

# 4. API Endpoints Tests
def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["app"] == "Inside"

def test_auth_registration_and_login():
    reg_data = {
        "email": "testuser@insideapp.in",
        "password": "securepassword123",
        "name": "Alex"
    }
    res = client.post("/auth/register", json=reg_data)
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert token is not None

    login_res = client.post("/auth/login", json={
        "email": "testuser@insideapp.in",
        "password": "securepassword123"
    })
    assert login_res.status_code == 200
    assert login_res.json()["name"] == "Alex"

def test_scan_and_analysis_endpoint():
    # Register a new user
    reg = client.post("/auth/register", json={"email": "scanner@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    scan_res = client.post("/scan", headers=headers, json={
        "product_name": "Test Orange Drink",
        "ocr_text": "INGREDIENTS: Water, Sugar, Citric Acid, Artificial Flavour."
    })
    assert scan_res.status_code == 200
    data = scan_res.json()
    assert data["product_name"] == "Test Orange Drink"
    assert data["score"] > 0
    assert len(data["ingredients"]) >= 3
    assert data["overall_status"] in ["GOOD", "CAUTION", "AVOID"]

def test_billing_verification():
    reg = client.post("/auth/register", json={"email": "buyer@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify lifetime premium purchase
    bill_res = client.post("/billing/verify", headers=headers, json={
        "product_id": "premium_lifetime",
        "purchase_token": "test-play-token-xyz-12345678",
        "order_id": "GPA.1234-5678-9012"
    })
    assert bill_res.status_code == 200
    assert bill_res.json()["is_premium"] is True

    # Check status
    status_res = client.get("/billing/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["is_premium"] is True
    assert status_res.json()["price_inr"] == 199


# 5. Product Name & Category Detection Tests
def test_category_normalization():
    from backend.app.services.product_detector import normalize_category
    assert normalize_category("en:biscuits") == "Biscuits"
    assert normalize_category("en:salty-snacks, en:crisps") == "Chips & Snacks"
    assert normalize_category("en:carbonated-drinks") == "Soft Drink"
    assert normalize_category("en:fruit-juices") == "Juice"
    assert normalize_category("en:dairies, en:cheeses") == "Dairy"
    assert normalize_category("en:instant-noodles") == "Noodles"
    assert normalize_category("en:breakfast-cereals") == "Breakfast Cereal"
    assert normalize_category("en:chocolates") == "Chocolate"
    assert normalize_category("unknown_xyz") == "Food Product"
    assert normalize_category(None) == "Food Product"


def test_product_name_and_category_detection_priorities():
    from backend.app.services.product_detector import resolve_product_name_and_category

    # Priority 1: Valid provided barcode lookup name & category
    name1, cat1 = resolve_product_name_and_category(
        provided_name="Britannia NutriChoice Digestive",
        provided_category="Biscuits",
        ocr_text="INGREDIENTS: Wheat flour, Palm oil, Sugar.",
        parsed_ingredients=["Wheat flour", "Palm oil", "Sugar"]
    )
    assert name1 == "Britannia NutriChoice Digestive"
    assert cat1 == "Biscuits"

    # Priority 2: Recognizable brand/product in OCR text before ingredients
    ocr_sample = "Britannia NutriChoice Digestive\nBATCH NO: 123\nINGREDIENTS: Refined Wheat Flour, Palm Oil, Sugar, Salt."
    name2, cat2 = resolve_product_name_and_category(
        provided_name=None,
        provided_category=None,
        ocr_text=ocr_sample,
        parsed_ingredients=["Refined Wheat Flour", "Palm Oil", "Sugar", "Salt"]
    )
    assert "Britannia NutriChoice" in name2
    assert cat2 == "Biscuits"

    # Priority 3: Ingredient heuristic detection (Soft drink ingredients)
    name3, cat3 = resolve_product_name_and_category(
        provided_name=None,
        provided_category=None,
        ocr_text=None,
        parsed_ingredients=["Carbonated Water", "Sugar", "Acidity Regulator 338", "Caffeine"]
    )
    assert name3 == "Carbonated Soft Drink"
    assert cat3 == "Soft Drink"

    # Priority 4: Insufficient evidence fallback
    name4, cat4 = resolve_product_name_and_category(
        provided_name=None,
        provided_category=None,
        ocr_text=None,
        parsed_ingredients=["Ingredient X", "Ingredient Y"]
    )
    assert name4 == "Unknown Product"
    assert cat4 == "Food Product"


# 6. History Endpoints & Migration Tests
def test_history_crud_and_product_category():
    from backend.app.database.session import apply_db_migrations

    # Test database migration runner
    apply_db_migrations(test_engine)

    # Register user
    reg = client.post("/auth/register", json={"email": "historytester@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Perform scan
    scan_res = client.post("/scan", headers=headers, json={
        "product_name": "Coca-Cola",
        "product_category": "Soft Drink",
        "ocr_text": "INGREDIENTS: Carbonated Water, Sugar, Acidity Regulator 338, Caffeine."
    })
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert scan_data["product_name"] == "Coca-Cola"
    assert scan_data["product_category"] == "Soft Drink"
    scan_id = scan_data["scan_id"]
    assert scan_id is not None

    # Get history list
    hist_res = client.get("/history", headers=headers)
    assert hist_res.status_code == 200
    hist_items = hist_res.json()
    assert len(hist_items) >= 1
    first_item = hist_items[0]
    assert first_item["product_name"] == "Coca-Cola"
    assert first_item["product_category"] == "Soft Drink"
    assert first_item["overall_status"] in ["GOOD", "CAUTION", "AVOID"]
    assert first_item["ingredient_count"] >= 3

    # Get single scan detail
    detail_res = client.get(f"/history/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["product_name"] == "Coca-Cola"
    assert detail_data["product_category"] == "Soft Drink"

    # Delete single scan
    del_res = client.delete(f"/history/{scan_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Clear all history
    clear_res = client.delete("/history", headers=headers)
    assert clear_res.status_code == 200
    assert clear_res.json()["success"] is True

    # Verify history is now empty
    empty_hist = client.get("/history", headers=headers)
    assert empty_hist.status_code == 200
    assert len(empty_hist.json()) == 0


# 7. Atomic Database Transaction & Free Scan Counter Tests
def test_free_scans_lifecycle_and_limits():
    """
    Test scenarios:
    1. User with 0 scans -> scan succeeds -> count = 1 -> one history record
    2. User with 2 scans -> scan succeeds -> count = 3
    3. User with 3 scans -> scan rejected with 403 (FREE_SCANS_EXHAUSTED) -> count remains 3 -> no history
    """
    from backend.app.models.entities import User, ScanHistory

    # Register brand new user
    reg = client.post("/auth/register", json={"email": "scantester@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. User with 0 scans: Scan 1
    scan1 = client.post("/scan", headers=headers, json={
        "product_name": "Product 1",
        "ocr_text": "INGREDIENTS: Wheat Flour, Sugar, Salt."
    })
    assert scan1.status_code == 200

    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 1
    assert u.scans_count == 1
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 1
    db.close()

    # Scan 2
    scan2 = client.post("/scan", headers=headers, json={
        "product_name": "Product 2",
        "ocr_text": "INGREDIENTS: Milk, Cocoa Powder, Sugar."
    })
    assert scan2.status_code == 200

    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 2
    db.close()

    # 2. User with 2 scans: Scan 3 (reaching the limit of 3)
    scan3 = client.post("/scan", headers=headers, json={
        "product_name": "Product 3",
        "ocr_text": "INGREDIENTS: Oats, Almonds, Honey."
    })
    assert scan3.status_code == 200

    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 3
    assert u.scans_count == 3
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 3
    db.close()

    # 3. User with 3 scans: Scan 4 should be rejected with 403 FREE_SCANS_EXHAUSTED
    scan4 = client.post("/scan", headers=headers, json={
        "product_name": "Product 4",
        "ocr_text": "INGREDIENTS: Rice, Salt, Oil."
    })
    assert scan4.status_code == 403
    err_detail = scan4.json()["detail"]
    assert err_detail.get("error") == "FREE_SCANS_EXHAUSTED"

    # Verify count remains 3 and no 4th history record was created
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 3
    assert u.scans_count == 3
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 3
    db.close()


def test_failed_ocr_and_ai_analysis_rollback():
    """
    Scenario 4: Failed AI / OCR analysis -> count unchanged -> no history record.
    """
    from backend.app.models.entities import User, ScanHistory

    reg = client.post("/auth/register", json={"email": "failedocr@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt scan with unparseable gibberish symbols that contain 0 ingredients
    res = client.post("/scan", headers=headers, json={
        "product_name": "Bad Product",
        "ocr_text": "!@# $%^ &*() =+"
    })
    assert res.status_code == 422  # Unprocessable Entity

    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 0
    assert u.scans_count == 0
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 0
    db.close()


def test_failed_history_insertion_rollback():
    """
    Scenario 5: Failed history insertion -> transaction rollback -> count unchanged.
    """
    from unittest.mock import patch
    from backend.app.models.entities import User, ScanHistory

    reg = client.post("/auth/register", json={"email": "dberror@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate database commit error during scan history insertion
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Database I/O disk failure")):
        res = client.post("/scan", headers=headers, json={
            "product_name": "Test Item",
            "ocr_text": "INGREDIENTS: Sugar, Salt, Water."
        })
        assert res.status_code == 500

    # Verify count is rolled back to 0 and no history record committed
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 0
    assert u.scans_count == 0
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 0
    db.close()


def test_concurrent_scans_at_limit():
    """
    Scenario 6: Two simultaneous requests when count = 2 -> exactly ONE succeeds,
    exactly ONE is rejected -> final count = 3 -> exactly ONE new history record.
    """
    import concurrent.futures
    from backend.app.models.entities import User, ScanHistory

    reg = client.post("/auth/register", json={"email": "concurrency@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set user count to 2
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    u.free_scans_used = 2
    u.scans_count = 2
    db.commit()
    db.close()

    def do_scan(item_num):
        return client.post("/scan", headers=headers, json={
            "product_name": f"Concurrent Product {item_num}",
            "ocr_text": f"INGREDIENTS: Wheat Flour {item_num}, Sugar, Palm Oil."
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_scan, 1)
        f2 = executor.submit(do_scan, 2)
        res1 = f1.result()
        res2 = f2.result()

    statuses = [res1.status_code, res2.status_code]
    # Exactly one must succeed (200) and one must be rejected (403)
    assert 200 in statuses, f"Expected a 200 status, got {statuses}"
    assert 403 in statuses, f"Expected a 403 status, got {statuses}"

    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 3, f"Expected free_scans_used to be 3, got {u.free_scans_used}"
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 1, f"Expected exactly 1 history record, got {h_count}"
    db.close()


def test_premium_user_unlimited_scans():
    """
    Scenario 7: Premium user has unlimited scans -> free_scans_used remains 0.
    """
    from backend.app.models.entities import User, ScanHistory

    reg = client.post("/auth/register", json={"email": "premuser@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Grant premium
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    u.is_premium = True
    db.commit()
    db.close()

    # Perform 5 scans (more than free limit of 3)
    for i in range(5):
        res = client.post("/scan", headers=headers, json={
            "product_name": f"Premium Product {i}",
            "ocr_text": f"INGREDIENTS: Ingredient_{i}, Water, Salt."
        })
        assert res.status_code == 200

    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.is_premium is True
    assert u.free_scans_used == 0  # Does not consume free scans
    assert u.scans_count == 5
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 5
    db.close()


def test_idempotent_retry_prevents_duplicate_and_charge():
    """
    Scenario 8: Retry the same request with idempotency_key -> returns same scan
    without incrementing free_scans_used or creating duplicate history record.
    """
    from backend.app.models.entities import User, ScanHistory

    reg = client.post("/auth/register", json={"email": "idempotent@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    idempotency_key = "scan-req-uuid-998877"

    # Request 1
    res1 = client.post("/scan", headers=headers, json={
        "product_name": "Idempotent Biscuits",
        "ocr_text": "INGREDIENTS: Whole Wheat, Oats, Sugar.",
        "idempotency_key": idempotency_key
    })
    assert res1.status_code == 200
    scan1_id = res1.json()["scan_id"]

    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 1
    assert u.scans_count == 1
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 1
    db.close()

    # Request 2 (Retry with exact same idempotency_key)
    res2 = client.post("/scan", headers=headers, json={
        "product_name": "Idempotent Biscuits",
        "ocr_text": "INGREDIENTS: Whole Wheat, Oats, Sugar.",
        "idempotency_key": idempotency_key
    })
    assert res2.status_code == 200
    assert res2.json()["scan_id"] == scan1_id

    # Verify no additional scan consumed and no duplicate record created
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 1
    assert u.scans_count == 1
    h_count = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).count()
    assert h_count == 1
    db.close()


# 8. Razorpay Payment Gateway Integration Tests
def test_razorpay_create_order_backend_determined_amount():
    """
    Test 3: Backend creates Razorpay order for exactly 19900 paise (₹199), currency INR.
    """
    from unittest.mock import patch, MagicMock
    from backend.app.models.entities import User, Payment

    reg = client.post("/auth/register", json={"email": "payuser1@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Mock real Razorpay API returning order_live_12345
    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_live_payuser1_123",
        "amount": 19900,
        "currency": "INR",
        "status": "created"
    }
    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        res = client.post("/payments/create-order", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["amount"] == 19900  # Must strictly be 19900 paise
        assert data["currency"] == "INR"
        assert data["product"] == "inside_premium_lifetime"
        assert data["order_id"] == "order_live_payuser1_123"
        assert "key_id" in data

    # Verify payment record in DB
    db = TestingSessionLocal()
    pay_rec = db.query(Payment).filter(Payment.razorpay_order_id == "order_live_payuser1_123").first()
    assert pay_rec is not None
    assert pay_rec.user_id == user_id
    assert pay_rec.amount == 19900
    assert pay_rec.status == "CREATED"
    db.close()

    # Re-tapping button reuses existing active order rather than duplicating
    res2 = client.post("/payments/create-order", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["order_id"] == "order_live_payuser1_123"


def test_razorpay_create_order_api_failure_returns_502_no_mock_fallback():
    """
    Test: If Razorpay API fails, backend returns 502 Bad Gateway and NEVER returns fake order_test_...
    """
    from unittest.mock import patch, MagicMock
    reg = client.post("/auth/register", json={"email": "failpay@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    mock_client = MagicMock()
    mock_client.order.create.side_effect = Exception("Razorpay API Connection Timeout")
    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        res = client.post("/payments/create-order", headers=headers)
        assert res.status_code == 502
        assert "order_test" not in res.text


def test_razorpay_verify_valid_signature_unlocks_premium():
    """
    Test 5: Valid Razorpay signature and payment verification unlocks lifetime premium.
    """
    from unittest.mock import patch, MagicMock
    from backend.app.models.entities import User, Payment
    from backend.app.services.razorpay_service import generate_test_signature

    reg = client.post("/auth/register", json={"email": "payuser2@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Create order with mock live response
    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_live_payuser2_456",
        "amount": 19900,
        "currency": "INR",
        "status": "created"
    }
    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        order_res = client.post("/payments/create-order", headers=headers)
        assert order_res.status_code == 200
        order_id = order_res.json()["order_id"]

    # Step 2: Simulate Razorpay checkout success callback
    payment_id = f"pay_live_{int(datetime.datetime.now().timestamp())}"
    valid_sig = generate_test_signature(order_id, payment_id)

    # Step 3: Verify payment with backend
    verify_res = client.post("/payments/verify", headers=headers, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": valid_sig
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["success"] is True
    assert verify_res.json()["is_premium"] is True

    # Step 4: Verify DB state
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.is_premium is True
    assert u.premium_granted_at is not None

    pay_rec = db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()
    assert pay_rec.status == "CAPTURED"
    assert pay_rec.razorpay_payment_id == payment_id
    db.close()

    # Check status endpoint
    status_res = client.get("/payments/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["is_premium"] is True
    assert status_res.json()["scans_left"] == 999999


def test_razorpay_verify_idempotency():
    """
    Test 6: Repeating verification request with same payment is idempotent.
    """
    from unittest.mock import patch, MagicMock
    from backend.app.models.entities import User, Payment
    from backend.app.services.razorpay_service import generate_test_signature

    reg = client.post("/auth/register", json={"email": "idempay@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_live_idempay_789",
        "amount": 19900,
        "currency": "INR",
        "status": "created"
    }
    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        order_res = client.post("/payments/create-order", headers=headers)
        order_id = order_res.json()["order_id"]

    payment_id = "pay_live_idempotent_999"
    valid_sig = generate_test_signature(order_id, payment_id)

    # First verification
    v1 = client.post("/payments/verify", headers=headers, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": valid_sig
    })
    assert v1.status_code == 200

    # Repeat verification
    v2 = client.post("/payments/verify", headers=headers, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": valid_sig
    })
    assert v2.status_code == 200
    assert v2.json()["success"] is True
    assert v2.json()["is_premium"] is True

    # Ensure exactly 1 payment record exists for this order
    db = TestingSessionLocal()
    pay_count = db.query(Payment).filter(Payment.razorpay_order_id == order_id).count()
    assert pay_count == 1
    db.close()


def test_razorpay_verify_invalid_signature_rejected():
    """
    Test 8: Invalid / forged cryptographic signature is rejected.
    """
    from unittest.mock import patch, MagicMock
    from backend.app.models.entities import User, Payment

    reg = client.post("/auth/register", json={"email": "forger@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_live_forger_001",
        "amount": 19900,
        "currency": "INR",
        "status": "created"
    }
    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        order_res = client.post("/payments/create-order", headers=headers)
        order_id = order_res.json()["order_id"]

    # Send forged signature
    res = client.post("/payments/verify", headers=headers, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": "pay_fake_12345",
        "razorpay_signature": "fake_invalid_sha256_hash_value"
    })
    assert res.status_code == 400

    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.is_premium is False
    pay_rec = db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()
    assert pay_rec.status == "CREATED"  # Not verified
    db.close()


def test_razorpay_user_isolation_prevent_theft():
    """
    Test 10: User A's payment details cannot be redeemed by User B.
    """
    from unittest.mock import patch, MagicMock
    from backend.app.models.entities import User, Payment
    from backend.app.services.razorpay_service import generate_test_signature

    # User A creates order
    regA = client.post("/auth/register", json={"email": "usera@insideapp.in", "password": "pass123456"})
    tokenA = regA.json()["access_token"]

    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_live_usera_002",
        "amount": 19900,
        "currency": "INR",
        "status": "created"
    }
    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        order_res = client.post("/payments/create-order", headers={"Authorization": f"Bearer {tokenA}"})
        order_id = order_res.json()["order_id"]

    # User B tries to verify User A's order
    regB = client.post("/auth/register", json={"email": "userb@insideapp.in", "password": "pass123456"})
    tokenB = regB.json()["access_token"]
    payment_id = "pay_test_usera_theft"
    sig = generate_test_signature(order_id, payment_id)

    steal_res = client.post("/payments/verify", headers={"Authorization": f"Bearer {tokenB}"}, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": sig
    })
    assert steal_res.status_code == 403  # Forbidden

    db = TestingSessionLocal()
    uB = db.query(User).filter(User.id == regB.json()["user_id"]).first()
    assert uB.is_premium is False
    db.close()


def test_razorpay_webhook_server_reconciliation():
    """
    Test 11 & 15: Razorpay Webhook reconciles payment and grants premium even if client disconnected.
    """
    import hmac
    import hashlib
    from unittest.mock import patch, MagicMock
    from backend.app.models.entities import User, Payment
    from backend.app.config import settings

    reg = client.post("/auth/register", json={"email": "webhookuser@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create order
    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_live_webhook_rec_123",
        "amount": 19900,
        "currency": "INR",
        "status": "created"
    }
    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        order_res = client.post("/payments/create-order", headers=headers)
        order_id = order_res.json()["order_id"]

    payment_id = "pay_webhook_reconciled_123"

    # Construct webhook event payload
    event_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "amount": 19900,
                    "currency": "INR",
                    "status": "captured"
                }
            }
        }
    }
    body_bytes = json.dumps(event_payload).encode("utf-8")
    secret = settings.RAZORPAY_WEBHOOK_SECRET or settings.RAZORPAY_KEY_SECRET
    sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    # Post webhook
    hook_res = client.post(
        "/payments/webhook",
        content=body_bytes,
        headers={"X-Razorpay-Signature": sig, "Content-Type": "application/json"}
    )
    assert hook_res.status_code == 200
    assert hook_res.json()["status"] == "ok"

    # Verify user received premium
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.is_premium is True
    pay_rec = db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()
    assert pay_rec.status == "CAPTURED"
    assert pay_rec.razorpay_payment_id == payment_id
    db.close()


def test_free_scans_exhausted_then_unlocked_via_razorpay():
    """
    End-to-End Flow:
    1. User uses all 3 free scans
    2. 4th scan is blocked (403 FREE_SCANS_EXHAUSTED)
    3. User purchases Lifetime Premium via Razorpay
    4. 4th scan succeeds with unlimited access
    """
    from unittest.mock import patch, MagicMock
    from backend.app.models.entities import User, Payment
    from backend.app.services.razorpay_service import generate_test_signature

    reg = client.post("/auth/register", json={"email": "e2e_premium@insideapp.in", "password": "pass123456"})
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Consume 3 free scans
    for i in range(1, 4):
        s = client.post("/scan", headers=headers, json={
            "product_name": f"Scan {i}",
            "ocr_text": f"INGREDIENTS: Ingredient_{i}, Sugar, Salt."
        })
        assert s.status_code == 200

    # 4th scan blocked
    s4_blocked = client.post("/scan", headers=headers, json={
        "product_name": "Scan 4",
        "ocr_text": "INGREDIENTS: Flour, Palm Oil, Water."
    })
    assert s4_blocked.status_code == 403
    assert s4_blocked.json()["detail"]["error"] == "FREE_SCANS_EXHAUSTED"

    # User taps Unlock Premium -> creates Razorpay order
    mock_client = MagicMock()
    mock_client.order.create.return_value = {
        "id": "order_live_e2e_verified_123",
        "amount": 19900,
        "currency": "INR",
        "status": "created"
    }
    with patch("backend.app.services.razorpay_service.get_razorpay_client", return_value=mock_client):
        order_res = client.post("/payments/create-order", headers=headers)
        assert order_res.status_code == 200
        order_id = order_res.json()["order_id"]

    # Razorpay Checkout completes
    payment_id = "pay_e2e_lifetime_verified"
    sig = generate_test_signature(order_id, payment_id)

    verify_res = client.post("/payments/verify", headers=headers, json={
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": sig
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["is_premium"] is True

    # 4th scan now succeeds!
    s4_success = client.post("/scan", headers=headers, json={
        "product_name": "Scan 4",
        "ocr_text": "INGREDIENTS: Flour, Palm Oil, Water."
    })
    assert s4_success.status_code == 200
    assert s4_success.json()["product_name"] == "Scan 4"



