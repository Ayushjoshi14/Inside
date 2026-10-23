import pytest
import uuid
from backend.tests.test_backend import client, TestingSessionLocal, test_engine
from backend.app.database.session import Base
from backend.app.models.entities import User, ScanHistory, Ingredient

@pytest.fixture(autouse=True)
def ensure_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    if db.query(Ingredient).count() == 0:
        db.add(Ingredient(
            name="Sugar",
            normalized_name="Sugar",
            category="Sugar",
            caution_level="CAUTION",
            vegetarian_status="YES",
            vegan_status="YES",
            explanation="Sweetener."
        ))
        db.commit()
    db.close()
    yield

def _get_auth_headers():
    unique_email = f"pd_{uuid.uuid4().hex[:8]}@insideapp.in"
    reg = client.post("/auth/register", json={"email": unique_email, "password": "pass123456"})
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_purchase_decision_yes_with_custom_name():
    """
    Scenario: User scans a product, selects 'Yes', and enters a custom name.
    1. Scan creates a history record.
    2. PATCH /history/{scan_id} updates purchase_decision='YES' and custom_product_name.
    3. GET /history returns updated custom_product_name and purchase_decision.
    """
    headers = _get_auth_headers()

    # Step 1: Perform a valid food scan
    scan_res = client.post("/scan", headers=headers, json={
        "product_name": "Britannia Good Day Butter Cookies",
        "ocr_text": "Britannia Good Day Butter Cookies. INGREDIENTS: Refined Wheat Flour, Butter, Sugar, Palm Oil, Salt. Net Wt 120g."
    })
    assert scan_res.status_code == 200, scan_res.text
    scan_id = scan_res.json()["scan_id"]
    assert scan_id is not None
    assert scan_res.json()["custom_product_name"] is None
    assert scan_res.json()["purchase_decision"] is None

    # Step 2: PATCH purchase decision YES with custom product name
    patch_res = client.patch(f"/history/{scan_id}", headers=headers, json={
        "purchase_decision": "YES",
        "custom_product_name": "My favourite biscuits"
    })
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    assert patch_data["scan_id"] == scan_id
    assert patch_data["purchase_decision"] == "YES"
    assert patch_data["custom_product_name"] == "My favourite biscuits"
    assert patch_data["product_name"] == "Britannia Good Day Butter Cookies"
    assert "score" in patch_data

    # Step 3: Verify GET /history/{scan_id}
    item_res = client.get(f"/history/{scan_id}", headers=headers)
    assert item_res.status_code == 200
    item_data = item_res.json()
    assert item_data["purchase_decision"] == "YES"
    assert item_data["custom_product_name"] == "My favourite biscuits"

    # Step 4: Verify GET /history list
    hist_res = client.get("/history", headers=headers)
    assert hist_res.status_code == 200
    items = hist_res.json()
    matching = [i for i in items if i["id"] == scan_id]
    assert len(matching) == 1
    assert matching[0]["purchase_decision"] == "YES"
    assert matching[0]["custom_product_name"] == "My favourite biscuits"

def test_purchase_decision_no_without_custom_name():
    """
    Scenario: User selects 'No'.
    1. purchase_decision is saved as 'NO'.
    2. custom_product_name is not required and remains unchanged/None.
    """
    headers = _get_auth_headers()

    scan_res = client.post("/scan", headers=headers, json={
        "product_name": "Sugary Drink",
        "ocr_text": "Carbonated Soft Drink. INGREDIENTS: Carbonated Water, Sugar, Acidity Regulator 330, Caffeine. Net 300ml."
    })
    assert scan_res.status_code == 200, scan_res.text
    scan_id = scan_res.json()["scan_id"]

    patch_res = client.patch(f"/history/{scan_id}", headers=headers, json={
        "purchase_decision": "NO"
    })
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["purchase_decision"] == "NO"
    assert data["custom_product_name"] is None

def test_rename_product_updates_name_and_preserves_score():
    """
    Scenario: User renames a product from history screen.
    - Health score and ingredient analysis remain completely preserved.
    """
    headers = _get_auth_headers()

    scan_res = client.post("/scan", headers=headers, json={
        "product_name": "Original Granola",
        "ocr_text": "Healthy Granola. INGREDIENTS: Whole Rolled Oats, Honey, Almonds, Dried Cranberries. Net Wt 400g."
    })
    assert scan_res.status_code == 200, scan_res.text
    scan_data = scan_res.json()
    scan_id = scan_data["scan_id"]
    original_score = scan_data["score"]

    # Rename product
    patch_res = client.patch(f"/history/{scan_id}", headers=headers, json={
        "custom_product_name": "Almond & Honey Granola Bar"
    })
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["custom_product_name"] == "Almond & Honey Granola Bar"
    assert updated_data["score"] == original_score

    # Verify score also preserved in GET /history/{scan_id}
    item_res = client.get(f"/history/{scan_id}", headers=headers)
    assert item_res.status_code == 200
    assert item_res.json()["score"] == original_score
    assert item_res.json()["custom_product_name"] == "Almond & Honey Granola Bar"

def test_reject_empty_custom_name_or_invalid_decision():
    """
    Validation:
    - Empty or whitespace-only name must be rejected with 422.
    - Invalid decision (e.g. 'MAYBE') must be rejected with 422.
    """
    headers = _get_auth_headers()

    scan_res = client.post("/scan", headers=headers, json={
        "product_name": "Milk Chocolate",
        "ocr_text": "Cadbury Dairy Milk. INGREDIENTS: Sugar, Milk Solids, Cocoa Butter, Cocoa Solids. Net 50g."
    })
    assert scan_res.status_code == 200, scan_res.text
    scan_id = scan_res.json()["scan_id"]

    # Test empty name
    res_empty = client.patch(f"/history/{scan_id}", headers=headers, json={
        "custom_product_name": "   "
    })
    assert res_empty.status_code == 422

    # Test invalid decision
    res_invalid_dec = client.patch(f"/history/{scan_id}", headers=headers, json={
        "purchase_decision": "MAYBE"
    })
    assert res_invalid_dec.status_code == 422
