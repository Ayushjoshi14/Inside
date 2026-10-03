import pytest
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
