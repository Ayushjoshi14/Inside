import pytest
import json
from fastapi.testclient import TestClient
from backend.tests.test_backend import client, TestingSessionLocal, test_engine
from backend.app.database.session import Base, apply_db_migrations
from backend.app.ocr.processor import (
    process_food_label,
    extract_nutrition_facts,
    extract_ingredient_section,
    split_into_ingredients,
    clean_ingredient_token,
)
from backend.app.models.entities import User, ScanHistory, Ingredient

@pytest.fixture(scope="session", autouse=True)
def ensure_db():
    Base.metadata.create_all(bind=test_engine)
    apply_db_migrations()
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
        db.commit()
    db.close()

def _create_user(email="universal_user@insideapp.in", password="password123"):
    reg = client.post("/auth/register", json={"email": email, "password": password})
    if reg.status_code == 200:
        token = reg.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    # If already registered, login
    login_res = client.post("/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# =========================================================================
# UNIVERSAL INGREDIENT EXTRACTION TEST SUITE
# =========================================================================

def test_category_1_packaged_biscuits_with_nutrition_panel():
    """
    Test Category 1: Packaged Biscuits / Cookies (e.g., Britannia / Oreo).
    Verifies:
    1. Rich ingredient list with percentages and INS additives.
    2. Excised nutrition facts into separate structured dictionary.
    3. Brand names (Britannia, Oreo) removed from ingredients.
    4. Nutrition values not contaminating ingredients.
    """
    label_text = """
    BRITANNIA GOOD DAY BUTTER COOKIES
    RICH COOKIES
    INGREDIENTS: Refined Wheat Flour (Maida) (58%), Sugar, Edible Vegetable Oil (Palm Oil), Butter (2.5%), Milk Solids, Invert Sugar Syrup, Raising Agents (INS 503(ii), INS 500(ii)), Iodised Salt, Emulsifiers (INS 322, INS 471), Nature Identical Flavouring Substances.
    Allergen Advice: Contains Wheat and Milk. May contain traces of Soy and Nuts.
    NUTRITION INFORMATION
    Per 100g (Approx.):
    Energy 492 kcal
    Protein 6.5g
    Carbohydrate 69.5g
    Total Sugars 22.0g
    Added Sugars 21.0g
    Total Fat 21.0g
    Saturated Fat 10.5g
    Cholesterol 8mg
    Sodium 350mg
    Mfg Date: 12/03/2026. Lic. No. 10015043001129. Net Wt. 200g. MRP Rs. 35.00
    Manufactured by Britannia Industries Ltd.
    """
    ingredients, nutrition_facts, section = process_food_label(label_text)

    # Ingredients verification
    assert len(ingredients) >= 7
    # Brand name excluded
    assert not any("britannia" in ing.lower() for ing in ingredients)
    assert not any("good day" in ing.lower() for ing in ingredients)
    # Category heading excluded
    assert not any(ing.lower() == "rich cookies" for ing in ingredients)
    # INS additives and nested parentheses kept intact
    assert any("Refined Wheat Flour (Maida) (58%)" in ing or "Wheat Flour" in ing for ing in ingredients)
    assert any("503(ii)" in ing or "Raising Agents" in ing for ing in ingredients)
    assert any("Butter" in ing for ing in ingredients)

    # Nutrition facts verification
    assert nutrition_facts.get("energy_kcal") == 492.0
    assert nutrition_facts.get("protein_g") == 6.5
    assert nutrition_facts.get("carbohydrates_g") == 69.5
    assert nutrition_facts.get("total_sugars_g") == 22.0
    assert nutrition_facts.get("added_sugars_g") == 21.0
    assert nutrition_facts.get("total_fat_g") == 21.0
    assert nutrition_facts.get("sodium_mg") == 350.0

    # No nutrition rows in ingredients
    for ing in ingredients:
        assert "kcal" not in ing.lower()
        assert not ing.lower().startswith("energy")
        assert not ing.lower().startswith("protein")


def test_category_2_chocolates_and_confectionery_with_allergens():
    """
    Test Category 2: Chocolates (e.g., Cadbury Dairy Milk).
    Verifies:
    1. Allergen advice and licensing cutoff before contaminating ingredient list.
    2. Clean separation of ingredients.
    """
    label_text = """
    CADBURY DAIRY MILK SILK
    Ingredients: Sugar, Milk Solids (20%), Cocoa Butter, Cocoa Solids, Emulsifiers (INS 442, INS 476), Flavours (Natural and Nature Identical Vanilla).
    Contains Added Flavour (Vanilla).
    ALLERGEN DECLARATION: CONTAINS MILK. MAY CONTAIN TREE NUTS, SOY AND WHEAT.
    NUTRITIONAL VALUES (Per 100g):
    Energy: 534 kcal
    Protein: 7.8g
    Carbohydrates: 59.2g
    Total Sugars: 57.0g
    Total Fat: 31.4g
    Saturated Fat: 19.8g
    Sodium: 152mg
    Marketed by Mondelez India Foods Pvt Ltd.
    Lic No: 10014022002711. FSSAI certified. Best before 9 months from packaging.
    """
    ingredients, nutrition_facts, _ = process_food_label(label_text)

    # Ensure allergens and company details do not become ingredients
    assert len(ingredients) >= 4
    for ing in ingredients:
        assert "mondelez" not in ing.lower()
        assert "cadbury" not in ing.lower()
        assert "allergen" not in ing.lower()
        assert "fssai" not in ing.lower()
        assert "lic" not in ing.lower()

    assert any("Sugar" in ing for ing in ingredients)
    assert any("Cocoa Butter" in ing for ing in ingredients)
    assert any("Cocoa Solids" in ing for ing in ingredients)

    assert nutrition_facts.get("energy_kcal") == 534.0
    assert nutrition_facts.get("protein_g") == 7.8
    assert nutrition_facts.get("total_fat_g") == 31.4


def test_category_3_savory_snacks_with_nested_seasoning():
    """
    Test Category 3: Savory chips / namkeen with multi-level nested parentheses.
    Verifies nested parenthesis tokenizer preserves compound seasoning structures.
    """
    label_text = """
    LAY'S INDIA'S MAGIC MASALA
    POTATO CHIPS
    Ingredients: Potato (52%), Edible Vegetable Oil (Palmolein Oil), Seasoning (Spices and Condiments, Iodised Salt, Maltodextrin, Black Salt, Sugar, Acidity Regulators (INS 330, INS 296), Flavour Enhancers (INS 627, INS 631), Anticaking Agent (INS 551)).
    May contain Wheat and Milk.
    Nutrition Facts per 100g:
    Energy: 544 kcal
    Protein: 6.7g
    Carbohydrate: 53.2g
    Total Sugars: 2.5g
    Total Fat: 33.7g
    Sodium: 790mg
    Packed by PepsiCo India Holdings Pvt Ltd.
    """
    ingredients, nutrition_facts, _ = process_food_label(label_text)

    # Find the seasoning token
    seasoning_token = next((ing for ing in ingredients if "Seasoning" in ing), None)
    assert seasoning_token is not None, "Compound Seasoning should be kept together"
    # Ensure nested parentheses inside Seasoning were not broken apart
    assert "INS 330" in seasoning_token
    assert "INS 631" in seasoning_token

    # Brand and heading excluded
    assert not any("lay's" in ing.lower() for ing in ingredients)
    assert not any("potato chips" == ing.lower() for ing in ingredients)

    assert nutrition_facts.get("energy_kcal") == 544.0
    assert nutrition_facts.get("sodium_mg") == 790.0


def test_category_4_beverages_per_100ml_basis():
    """
    Test Category 4: Bottled beverages and soft drinks.
    Verifies liquid basis (per 100ml) is extracted properly into nutrition_facts.
    """
    label_text = """
    THUMS UP CARBONATED BEVERAGE
    INGREDIENTS: Carbonated Water, Sugar, Acidity Regulator (INS 338), Colour (INS 150d), Flavours (Natural Flavouring Substances), Caffeine.
    NUTRITION FACTS Per 100 ml:
    Energy: 40 kcal
    Carbohydrates: 10g
    Total Sugars: 10g
    Added Sugars: 10g
    Total Fat: 0g
    Protein: 0g
    Sodium: 3mg
    Caffeine Content: 10 mg / 100 ml.
    Manufactured by Coca-Cola India Pvt Ltd.
    """
    ingredients, nutrition_facts, _ = process_food_label(label_text)

    assert len(ingredients) >= 4
    assert any("Carbonated Water" in ing for ing in ingredients)
    assert any("Caffeine" in ing for ing in ingredients)
    assert not any("thums up" in ing.lower() for ing in ingredients)
    assert not any("coca-cola" in ing.lower() for ing in ingredients)

    assert nutrition_facts.get("per_unit") == "Per 100 Ml"
    assert nutrition_facts.get("energy_kcal") == 40.0
    assert nutrition_facts.get("total_sugars_g") == 10.0
    assert nutrition_facts.get("total_fat_g") == 0.0


def test_category_5_multilingual_packaging_headers():
    """
    Test Category 5: International/bilingual packaging with non-English headers (e.g., Ingrédients, Zutaten, Composition).
    """
    label_text = """
    ARTISAN CRACKERS
    Composition: Farine de blé enrichie (65%), Huile d'olive vierge extra (12%), Sel de mer, Romarin séché (1.5%), Levure boulangère.
    Ingrédients: Farine de blé, Huile d'olive, Sel, Romarin, Levure.
    Fabriqué en France.
    """
    ingredients, _, _ = process_food_label(label_text)

    assert len(ingredients) >= 3
    assert any("Farine de" in ing for ing in ingredients)
    assert any("Huile" in ing for ing in ingredients)
    assert any("Romarin" in ing for ing in ingredients)


def test_category_6_missing_ingredient_list_rejected_safely():
    """
    Test Category 6: Front-of-box marketing claims with no real ingredient list.
    Must return empty parsed ingredients, triggering HTTP 422 UNABLE_TO_IDENTIFY
    in the API without inventing fake ingredients or generating a health score.
    """
    front_box_text = """
    CRUNCHY OAT CRUNCH BITES!
    100% Real Whole Grain Goodness
    High in Protein & Dietary Fiber
    Rich in Calcium and Iron
    Zero Trans Fat, No Added Preservatives
    Net Wt: 400g
    Best Before 6 Months From Manufacture
    MRP Rs 150 (Incl. of all taxes)
    Manufactured by Healthy Foods Inc.
    """
    # 1. Direct processor check
    ingredients, nutrition_facts, _ = process_food_label(front_box_text)
    assert len(ingredients) == 0, "No fake ingredients should be extracted from pure marketing claims"

    # 2. Endpoint check via /scan
    response = client.post("/scan", json={"ocr_text": front_box_text})
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["error"] in ["UNABLE_TO_IDENTIFY", "INCOMPATIBLE_PRODUCT"]


def test_shared_scan_pipeline_camera_and_gallery_equivalence():
    """
    Test that both simulated camera live scan and gallery photo upload
    route through the identical shared /scan endpoint with the exact same
    universal extraction logic.
    """
    sample_ocr = """
    KISSAN FRESH TOMATO KETCHUP
    INGREDIENTS: Water, Tomato Paste (28%), Sugar, Salt, Acidity Regulator (INS 260), Thickeners (INS 1422, INS 415), Onion Powder, Garlic Powder, Spices and Condiments, Preservative (INS 211).
    NUTRITION INFORMATION Per 100g:
    Energy: 132 kcal
    Protein: 1.4g
    Carbohydrates: 31.2g
    Total Sugars: 26.5g
    Total Fat: 0.1g
    Sodium: 920mg
    """
    # Simulate Camera Scan payload
    cam_res = client.post("/scan", json={
        "ocr_text": sample_ocr,
        "product_name": "Tomato Ketchup",
        "product_category": "Condiments",
    })
    assert cam_res.status_code == 200
    cam_data = cam_res.json()

    # Simulate Gallery Upload payload
    gal_res = client.post("/scan", json={
        "ocr_text": sample_ocr,
        "product_name": None,
        "product_category": None,
    })
    assert gal_res.status_code == 200
    gal_data = gal_res.json()

    # Verify identical extracted ingredients and nutrition facts
    assert len(cam_data["ingredients"]) == len(gal_data["ingredients"])
    assert cam_data["nutrition_facts"] == gal_data["nutrition_facts"]
    assert cam_data["nutrition_facts"]["energy_kcal"] == 132.0
    assert cam_data["nutrition_facts"]["sodium_mg"] == 920.0
    assert cam_data["is_compatible"] is True
    assert cam_data["compatibility_status"] == "COMPATIBLE"


def test_scan_history_persists_and_retrieves_nutrition_facts():
    """
    Test that authenticated scan persists nutrition_facts in database
    and GET /history returns it properly structured for the client.
    """
    headers = _create_user("universal_history_user@insideapp.in")

    sample_ocr = """
    AMUL TAZA FRESH TONED MILK
    Ingredients: Toned Milk, Vitamin A, Vitamin D.
    Nutrition Facts Per 100ml:
    Energy: 58 kcal
    Protein: 3.1g
    Carbohydrate: 4.7g
    Total Fat: 3.0g
    Calcium: 120mg
    """

    scan_res = client.post("/scan", json={"ocr_text": sample_ocr}, headers=headers)
    assert scan_res.status_code == 200
    scan_id = scan_res.json()["scan_id"]
    assert scan_id is not None

    # Retrieve history
    hist_res = client.get("/history", headers=headers)
    assert hist_res.status_code == 200
    items = hist_res.json()
    matched = next((item for item in items if item["id"] == scan_id), None)
    assert matched is not None
    assert matched["nutrition_facts"] is not None
    assert matched["nutrition_facts"].get("energy_kcal") == 58.0
    assert matched["nutrition_facts"].get("protein_g") == 3.1
