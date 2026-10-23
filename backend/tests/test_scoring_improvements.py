import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.analysis_engine import analyze_ingredients_list
from backend.app.ai.gemini_service import fallback_heuristic_analyzer
from backend.app.models.entities import Ingredient, User
from backend.tests.conftest import TestingSessionLocal

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def seed_scoring_ingredients():
    db = TestingSessionLocal()
    test_items = [
        ("Oats", "Oats", "Cereal", "GOOD", "YES", "YES", "Wholesome whole grain oats."),
        ("Almonds", "Almonds", "Nut", "GOOD", "YES", "YES", "Nutrient-rich whole nuts."),
        ("Refined Palm Oil", "Palm Oil", "Fat/oil", "CAUTION", "YES", "YES", "High in saturated fat."),
        ("High Fructose Corn Syrup", "High Fructose Corn Syrup", "Sweetener", "AVOID", "YES", "YES", "Excessive fructose linked to metabolic concerns."),
        ("Partially Hydrogenated Soybean Oil", "Partially Hydrogenated Soybean Oil", "Fat/oil", "AVOID", "YES", "YES", "Artificial trans fats."),
        ("Curcumin", "Curcumin", "Natural Colour", "GOOD", "YES", "YES", "Natural turmeric pigment."),
        ("Beetroot Red", "Beetroot Red", "Natural Colour", "GOOD", "YES", "YES", "Natural vegetable extract."),
    ]
    for name, norm, cat, caution, veg, vegan, exp in test_items:
        existing = db.query(Ingredient).filter(Ingredient.name == name).first()
        if not existing:
            db.add(Ingredient(
                name=name,
                normalized_name=norm,
                category=cat,
                caution_level=caution,
                vegetarian_status=veg,
                vegan_status=vegan,
                explanation=exp
            ))
    db.commit()
    db.close()


def test_clean_label_product_with_positive_findings():
    """Wholesome product gets clean label bonus and positive findings."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Oats", "Almonds", "Water"],
            profile=None,
            provided_product_name="Wholesome Muesli",
            provided_product_category="Breakfast Cereal",
            nutrition_facts={"per_unit": "Per 100g", "total_sugars_g": 3.0, "sodium_mg": 20.0}
        )

        assert result["score"] == 100  # 100 + 5 bonus capped at 100
        assert result["overall_status"] == "GOOD"
        breakdown = result["score_breakdown"]
        assert breakdown is not None
        assert breakdown["base_score"] == 100
        assert breakdown["final_score"] == 100
        assert len(breakdown["deductions"]) == 0
        assert any("clean-label" in b["label"].lower() or "clean" in b["label"].lower() for b in breakdown["bonuses"])

        # Positive findings populated
        assert len(result["positive_findings"]) >= 1
        assert any("Oats" in pf or "Almonds" in pf or "Wholesome" in pf or "clean" in pf.lower() for pf in result["positive_findings"])
    finally:
        db.close()


def test_avoid_ingredient_score_deduction():
    """An AVOID ingredient deducts 25 points and sets overall status to AVOID."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Water", "High Fructose Corn Syrup"],
            profile=None,
            provided_product_name="Sweet Drink",
            provided_product_category="Soft Drink",
            nutrition_facts={}
        )

        assert result["overall_status"] == "AVOID"
        breakdown = result["score_breakdown"]
        assert breakdown is not None
        assert breakdown["avoid_count"] == 1
        assert any("avoid" in d["label"].lower() and d["points"] == -25 for d in breakdown["deductions"])
        assert result["score"] <= 75
    finally:
        db.close()


def test_nutrition_facts_deductions_integrated():
    """Trans fat, high sodium, high sugar, and caution ingredient deduct points."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Oats", "Refined Palm Oil"],
            profile=None,
            provided_product_name="Salty Snack",
            provided_product_category="Chips & Snacks",
            nutrition_facts={
                "per_unit": "Per 100g",
                "trans_fat_g": 0.5,
                "sodium_mg": 850.0,
                "added_sugars_g": 20.0,
                "saturated_fat_g": 12.0
            }
        )

        breakdown = result["score_breakdown"]
        assert breakdown is not None
        assert breakdown["nutrition_integrated"] is True

        labels = [d["label"].lower() for d in breakdown["deductions"]]
        # Verify trans fat deduction (-10)
        assert any("trans fat" in l for l in labels)
        # Verify high sodium deduction (-5)
        assert any("sodium" in l for l in labels)
        # Verify high added sugar deduction (-5)
        assert any("sugar" in l for l in labels)
        # Verify saturated fat deduction (-3)
        assert any("saturated fat" in l for l in labels)
        # Verify CAUTION ingredient deduction (-8)
        assert any("caution" in l for l in labels)
    finally:
        db.close()


def test_score_floor_enforcement():
    """Multiple severe penalties cannot lower score below 5."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=[
                "High Fructose Corn Syrup",
                "Partially Hydrogenated Soybean Oil",
                "Refined Palm Oil",
                "Ingredient Bad 1",
                "Ingredient Bad 2",
                "Ingredient Bad 3",
            ],
            profile=None,
            provided_product_name="Ultra Processed Snack",
            provided_product_category="Snacks",
            nutrition_facts={
                "trans_fat_g": 2.0,
                "sodium_mg": 1200.0,
                "added_sugars_g": 40.0,
                "saturated_fat_g": 25.0
            }
        )

        assert result["score"] >= 5
        assert result["overall_status"] == "AVOID"
        assert result["score_breakdown"]["final_score"] >= 5
    finally:
        db.close()


def test_scan_api_returns_score_breakdown_and_positive_findings():
    """POST /scan returns score_breakdown and positive_findings in schema."""
    res = client.post("/scan", json={
        "product_name": "Rolled Oats Bowl",
        "ocr_text": "INGREDIENTS: Whole Rolled Oats, Almonds, Sea Salt."
    })
    assert res.status_code == 200
    data = res.json()
    assert "score_breakdown" in data
    assert data["score_breakdown"] is not None
    assert "base_score" in data["score_breakdown"]
    assert "deductions" in data["score_breakdown"]
    assert "bonuses" in data["score_breakdown"]
    assert "final_score" in data["score_breakdown"]
    assert "positive_findings" in data
    assert isinstance(data["positive_findings"], list)
    # Check ingredient source
    for ing in data["ingredients"]:
        assert "source" in ing


# =========================================================================
# NEW SAFETY & NORMALIZATION TESTS
# =========================================================================

def test_bha_false_positive_prevention():
    """Ordinary Indian ingredients containing 'bha' are not flagged as BHA preservatives."""
    res = fallback_heuristic_analyzer(["Sambhar Masala", "Pav Bhaji Seasoning", "Bikaneri Bhujia"])
    for ing in res["ingredients"]:
        assert ing["category"] != "Preservative", f"False positive preservative on {ing['name']}"
        assert ing["status"] != "CAUTION", f"False positive CAUTION on {ing['name']}"


def test_coconut_meat_vegan_compatibility():
    """Coconut meat and plant-based items are not classified as non-veg animal by-products."""
    res = fallback_heuristic_analyzer(["Coconut Meat", "Soy Meat"], user_diet="VEGETARIAN")
    for ing in res["ingredients"]:
        assert ing["category"] != "Animal by-product"
        assert ing["status"] != "AVOID"
        assert ing["vegetarian_status"] == "YES"


def test_natural_colour_warning_exclusion():
    """Natural colours like Curcumin and Beetroot Red do not trigger synthetic colour warnings."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Water", "Curcumin", "Beetroot Red"],
            profile=None,
            provided_product_name="Natural Tonic",
            provided_product_category="Beverage"
        )
        # Should not warn about synthetic food colours
        assert not any("synthetic food colour" in w.lower() for w in result["warnings"])
    finally:
        db.close()


def test_per_serving_nutrition_normalization():
    """A 20g serving with 12g sugar (60% sugar) is scaled to 60g/100g and triggers sugar deduction."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Oats", "Water"],
            profile=None,
            provided_product_name="Mini Energy Bar",
            provided_product_category="Snacks",
            nutrition_facts={
                "per_unit": "Per Serving",
                "serving_size": "20g",
                "total_sugars_g": 12.0  # 12g in 20g = 60g/100g
            }
        )
        breakdown = result["score_breakdown"]
        assert breakdown is not None
        # High sugar penalty should trigger due to 60g/100g equivalent
        assert any("sugar" in d["label"].lower() for d in breakdown["deductions"])
    finally:
        db.close()


def test_cache_insertion_transaction_isolation():
    """Calling analyze_ingredients_list does not commit or drop an outer active transaction."""
    db = TestingSessionLocal()
    try:
        # Create a temporary user record inside an uncommitted transaction
        test_email = "tx_isolation@insideapp.in"
        existing = db.query(User).filter(User.email == test_email).first()
        if not existing:
            u = User(email=test_email, hashed_password="dummy", is_active=True, free_scans_used=1)
            db.add(u)
            db.flush()

        # Call analyze_ingredients_list with an unknown ingredient
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Novel Herbal Component 999"],
            profile=None,
        )
        assert result is not None

        # Outer transaction is still active — rollback cleanly
        db.rollback()
        # Ensure rollback succeeded and uncommitted user was not committed
        re_check = db.query(User).filter(User.email == test_email).first()
        assert re_check is None, "analyze_ingredients_list prematurely committed outer transaction!"
    finally:
        db.close()



def test_cocoa_butter_and_plant_milks_vegan_safe():
    """Cocoa butter, coconut milk, and peanut butter are plant-derived and must NOT trigger dairy non-vegan avoid."""
    res = fallback_heuristic_analyzer(["Cocoa Butter", "Coconut Milk", "Peanut Butter"], user_diet="VEGAN")
    for ing in res["ingredients"]:
        assert ing["vegan_status"] == "YES"
        assert ing["status"] != "AVOID"


def test_parenthetical_avoid_list_matching():
    """User avoiding Palm Oil is protected when product lists 'Vegetable Oil (Palm Oil)'."""
    from backend.app.models.entities import UserProfile
    db = TestingSessionLocal()
    try:
        profile = UserProfile(diet_preference="NONE", avoid_ingredients='["Palm Oil"]', allergens="[]")
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Vegetable Oil (Palm Oil)", "Wheat Flour", "Sugar"],
            profile=profile
        )
        avoid_items = [i for i in result["ingredients"] if i["status"] == "AVOID"]
        assert len(avoid_items) >= 1
        assert any("palm oil" in i["reason"].lower() for i in avoid_items)
    finally:
        db.close()


def test_ai_omitted_ingredient_fallback_heuristic():
    """If an unknown ingredient is not mapped by AI, local heuristic evaluator is invoked cleanly."""
    from unittest.mock import patch
    db = TestingSessionLocal()
    try:
        # Simulate AI omitting the item from returned map
        with patch("backend.app.services.analysis_engine.analyze_unknown_ingredients_with_ai", return_value={"ingredients": []}):
            result = analyze_ingredients_list(
                db=db,
                raw_ingredients=["Partially Hydrogenated Rice Bran Oil"],
                profile=None
            )
            # Heuristic should identify it as trans-fat / AVOID
            ing = result["ingredients"][0]
            assert ing["status"] == "AVOID"
            assert "trans" in ing["reason"].lower()
    finally:
        db.close()


def test_packaging_text_and_address_exclusion_in_ocr():
    """OCR processor excludes manufacturer addresses, PIN codes, and directions for use."""
    from backend.app.ocr.processor import process_food_label

    ocr_sample = """
    INGREDIENTS: Whole Wheat Flour, Edible Vegetable Oil, Sugar, Iodised Salt.
    Mfd. By: Sunrise Foods Pvt. Ltd., Plot No. 42, Sector 18, Industrial Area, Gurugram 122015, Haryana.
    CIN: U15400HR2015PTC056789.
    Storage Instructions: Store in a cool, dry and hygienic place away from direct sunlight.
    Customer Care: Call 1800-111-222 or email feedback@sunrisepack.com
    Net Wt: 200g.
    """
    ingredients, nf, cleaned = process_food_label(ocr_sample)

    assert "Whole Wheat Flour" in ingredients or any("Wheat" in i for i in ingredients)
    assert "Iodised Salt" in ingredients or any("Salt" in i for i in ingredients)

    # Packaging noise should NEVER appear as ingredients
    for noisy_word in ["Plot No", "Industrial Area", "122015", "Gurugram", "Pvt. Ltd.", "CIN:", "Store in", "Direct sunlight", "1800-111-222"]:
        assert not any(noisy_word.lower() in ing.lower() for ing in ingredients), f"Leaked noise into ingredients: {noisy_word}"


def test_medicine_rejection_as_incompatible():
    """Medicines and pharmaceutical drugs are rejected with clear incompatibility message."""
    from backend.app.services.product_compatibility import evaluate_product_compatibility, CompatibilityStatus

    medicine_ocr = "Rx Paracetamol Tablets IP 500 mg. Schedule H Prescription Drug. Dosage: As directed by physician."
    check = evaluate_product_compatibility(medicine_ocr, product_name="Pain Relief Tablets")
    assert check.status == CompatibilityStatus.INCOMPATIBLE
    assert check.is_food is False
    assert "Medicine" in check.title or "Medicine" in check.message


def test_cosmetic_rejection_as_incompatible():
    """Cosmetic and personal care products are rejected with clear incompatibility message."""
    from backend.app.services.product_compatibility import evaluate_product_compatibility, CompatibilityStatus

    cosmetic_ocr = "Herbal Nourishing Shampoo. For external use only. Ingredients: Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine."
    check = evaluate_product_compatibility(cosmetic_ocr, product_name="Hair Shampoo")
    assert check.status == CompatibilityStatus.INCOMPATIBLE
    assert check.is_food is False
    assert "Cosmetic" in check.title or "Cosmetic" in check.message


def test_sparse_scan_score_capped_at_85():
    """Scans with fewer than 3 ingredients cannot receive 100/100; capped at 85."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Iodised Salt", "Water"],
            profile=None,
            provided_product_name="Saline Water",
            provided_product_category="Beverage"
        )
        assert result["score"] <= 85
        assert any("sparse" in w.lower() for w in result["warnings"])
    finally:
        db.close()


def test_unverified_ingredient_gets_caution_and_caps_score():
    """Unrecognized non-staple ingredients receive CAUTION / Unverified and cap score at 85."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Wheat Flour", "Sugar", "UnrecognizedChemicalPolyester99"],
            profile=None,
            provided_product_name="Test Product",
            provided_product_category="Food Product"
        )
        unverified_items = [i for i in result["ingredients"] if i["category"] == "Unverified"]
        assert len(unverified_items) >= 1
        assert unverified_items[0]["status"] == "CAUTION"
        assert result["score"] <= 85
        assert any("unverified" in w.lower() for w in result["warnings"])
    finally:
        db.close()


def test_dietary_supplement_advisory_warning():
    """Dietary supplements trigger mandatory advisory warning and RDA recommendation."""
    db = TestingSessionLocal()
    try:
        result = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Whey Protein Isolate", "Cocoa Powder", "Stevia"],
            profile=None,
            provided_product_name="Ultra Whey",
            provided_product_category="Dietary Supplement"
        )
        assert any("dietary supplement" in w.lower() for w in result["warnings"])
        assert any("serving size" in r.lower() or "balanced diet" in r.lower() for r in result["recommendations"])
    finally:
        db.close()


def test_assessment_type_distinction():
    """Distinguishes between ingredient-only and full nutritional assessments."""
    db = TestingSessionLocal()
    try:
        # Without nutrition facts
        res_ing_only = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Oats", "Almonds", "Water"],
            profile=None,
            nutrition_facts={}
        )
        assert res_ing_only["assessment_type"] == "INGREDIENT_ONLY"
        assert res_ing_only["score_breakdown"]["assessment_type"] == "INGREDIENT_ONLY"
        assert any("ingredient-based assessment" in w.lower() for w in res_ing_only["warnings"])

        # With nutrition facts
        res_full = analyze_ingredients_list(
            db=db,
            raw_ingredients=["Oats", "Almonds", "Water"],
            profile=None,
            nutrition_facts={"energy_kcal": 380, "protein_g": 12.0, "total_sugars_g": 4.0}
        )
        assert res_full["assessment_type"] == "FULL_NUTRITIONAL_AND_INGREDIENT"
        assert res_full["score_breakdown"]["assessment_type"] == "FULL_NUTRITIONAL_AND_INGREDIENT"
    finally:
        db.close()

