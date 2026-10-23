import pytest
from backend.tests.test_backend import client, TestingSessionLocal
from backend.app.models.entities import User, ScanHistory
from backend.app.services.product_compatibility import (
    evaluate_product_compatibility,
    CompatibilityStatus,
    INCOMPATIBLE_TITLE,
    INCOMPATIBLE_MESSAGE,
    UNREADABLE_TITLE,
    UNREADABLE_MESSAGE,
)


def _create_authenticated_user(email="compat_user@insideapp.in", password="password123"):
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    user_id = reg.json()["user_id"]
    return {"Authorization": f"Bearer {token}"}, user_id


# =========================================================================
# Scenario 1: Packaged biscuit with readable ingredient label
# =========================================================================
def test_scenario_1_packaged_biscuit_with_readable_ingredients():
    headers, user_id = _create_authenticated_user("biscuit_user@insideapp.in")

    biscuit_ocr = (
        "Britannia Good Day Butter Cookies. "
        "INGREDIENTS: Refined Wheat Flour (Maida), Butter, Sugar, Palm Oil, "
        "Invert Sugar, Iodised Salt, Milk Solids, Raising Agents (INS 503(ii), INS 500(ii)), "
        "Emulsifier (INS 322). FSSAI Lic. No. 10015043001129. Net Wt: 120g. "
        "Best before 6 months from packaging."
    )

    # Unit check
    compat = evaluate_product_compatibility(biscuit_ocr)
    assert compat.status == CompatibilityStatus.COMPATIBLE
    assert compat.is_food is True

    # API scan check
    res = client.post("/scan", headers=headers, json={"ocr_text": biscuit_ocr})
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["is_compatible"] is True
    assert data["compatibility_status"] == "COMPATIBLE"
    assert data["score"] > 0
    assert data["scan_id"] is not None
    assert len(data["ingredients"]) > 0

    # Verify quota decremented by 1 and history saved
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 1
    assert u.scans_count == 1
    histories = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).all()
    assert len(histories) == 1
    assert histories[0].overall_score == data["score"]
    db.close()


# =========================================================================
# Scenario 2: Packaged snack with nutrition label
# =========================================================================
def test_scenario_2_packaged_snack_with_nutrition_label():
    headers, user_id = _create_authenticated_user("snack_user@insideapp.in")

    snack_ocr = (
        "Lays Classic Salted Potato Chips. "
        "NUTRITION FACTS Per 100g: Energy: 540 kcal, Protein: 7g, "
        "Carbohydrate: 53g, Total Sugars: 1.5g, Total Fat: 34g, Saturated Fat: 15g, Sodium: 520mg. "
        "Ingredients: Potato, Edible Vegetable Oil (Palmolein), Iodised Salt. "
        "FSSAI Lic No 10014064000435. Net Quantity: 52g. Store in a cool and dry place."
    )

    # Unit check
    compat = evaluate_product_compatibility(snack_ocr)
    assert compat.status == CompatibilityStatus.COMPATIBLE
    assert compat.is_food is True

    # API scan check
    res = client.post("/scan", headers=headers, json={"ocr_text": snack_ocr})
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["is_compatible"] is True
    assert data["compatibility_status"] == "COMPATIBLE"
    assert data["score"] > 0
    assert data["scan_id"] is not None

    # Verify quota decremented and history saved
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 1
    assert u.scans_count == 1
    histories = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).all()
    assert len(histories) == 1
    db.close()


# =========================================================================
# Scenario 3: Book containing words like "sugar" and "protein"
# =========================================================================
def test_scenario_3_book_containing_sugar_and_protein():
    headers, user_id = _create_authenticated_user("book_user@insideapp.in")

    book_ocr = (
        "Chapter 4: The Biochemistry of Cellular Nutrition. "
        "In this chapter, the author examines sugar and protein transport across cellular membranes. "
        "Published by Oxford University Press. ISBN 978-0-19-850000-0. "
        "Copyright 2021. All rights reserved. Page 142."
    )

    # Unit check
    compat = evaluate_product_compatibility(book_ocr)
    assert compat.status == CompatibilityStatus.INCOMPATIBLE
    assert compat.title == INCOMPATIBLE_TITLE
    assert compat.message == INCOMPATIBLE_MESSAGE
    assert compat.is_food is False

    # API scan check
    res = client.post("/scan", headers=headers, json={"ocr_text": book_ocr})
    assert res.status_code == 422, f"Expected 422 for book scan, got {res.status_code}"
    err_detail = res.json()["detail"]
    assert err_detail["error"] == "INCOMPATIBLE_PRODUCT"
    assert err_detail["title"] == INCOMPATIBLE_TITLE
    assert err_detail["message"] == INCOMPATIBLE_MESSAGE

    # Critical: Quota must NOT be decremented and NO history created
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 0, "Scan quota must NOT be decremented for incompatible products"
    assert u.scans_count == 0
    histories = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).all()
    assert len(histories) == 0, "Incompatible products must NOT be saved to scan history"
    db.close()


# =========================================================================
# Scenario 4: Mobile phone
# =========================================================================
def test_scenario_4_mobile_phone():
    headers, user_id = _create_authenticated_user("phone_user@insideapp.in")

    phone_ocr = (
        "Samsung Galaxy Smartphone 5G. "
        "8GB RAM, 128GB ROM, 6.5 inch 120Hz AMOLED display, 64MP camera, "
        "5000mAh battery, Qualcomm Snapdragon 778G processor, Model SM-A526B. "
        "IMEI: 356987123456789."
    )

    # Unit check
    compat = evaluate_product_compatibility(phone_ocr)
    assert compat.status == CompatibilityStatus.INCOMPATIBLE
    assert compat.title == INCOMPATIBLE_TITLE
    assert compat.message == INCOMPATIBLE_MESSAGE
    assert compat.is_food is False

    # API scan check
    res = client.post("/scan", headers=headers, json={"ocr_text": phone_ocr})
    assert res.status_code == 422, f"Expected 422 for phone scan, got {res.status_code}"
    err_detail = res.json()["detail"]
    assert err_detail["error"] == "INCOMPATIBLE_PRODUCT"
    assert err_detail["title"] == INCOMPATIBLE_TITLE
    assert err_detail["message"] == INCOMPATIBLE_MESSAGE

    # Critical: Quota must NOT be decremented and NO history created
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 0
    assert u.scans_count == 0
    histories = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).all()
    assert len(histories) == 0
    db.close()


# =========================================================================
# Scenario 5: Blank or blurry image
# =========================================================================
def test_scenario_5_blank_or_blurry_image():
    headers, user_id = _create_authenticated_user("blank_user@insideapp.in")

    for blank_text in ["", "   \n\t  ", "... --- ..."]:
        compat = evaluate_product_compatibility(blank_text)
        assert compat.status == CompatibilityStatus.UNREADABLE
        assert compat.title == UNREADABLE_TITLE
        assert compat.message == UNREADABLE_MESSAGE
        assert compat.is_food is False

        res = client.post("/scan", headers=headers, json={"ocr_text": blank_text})
        assert res.status_code == 422, f"Expected 422 for blank scan, got {res.status_code}"
        err_detail = res.json()["detail"]
        assert err_detail["error"] == "UNABLE_TO_IDENTIFY"
        assert err_detail["title"] == UNREADABLE_TITLE
        assert err_detail["message"] == UNREADABLE_MESSAGE

    # Critical: Quota must NOT be decremented and NO history created
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 0
    assert u.scans_count == 0
    histories = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).all()
    assert len(histories) == 0
    db.close()


# =========================================================================
# Scenario 6: Food package with unreadable label
# =========================================================================
def test_scenario_6_food_package_with_unreadable_label():
    headers, user_id = _create_authenticated_user("blurry_label_user@insideapp.in")

    unreadable_label_ocr = "qwjke rhkwe jhkr wjher kjhwe zzz mnp qrs 98234"

    # Unit check
    compat = evaluate_product_compatibility(unreadable_label_ocr)
    assert compat.status == CompatibilityStatus.UNREADABLE
    assert compat.title == UNREADABLE_TITLE
    assert compat.message == UNREADABLE_MESSAGE
    assert compat.is_food is False

    # API scan check
    res = client.post("/scan", headers=headers, json={"ocr_text": unreadable_label_ocr})
    assert res.status_code == 422, f"Expected 422 for unreadable label scan, got {res.status_code}"
    err_detail = res.json()["detail"]
    assert err_detail["error"] == "UNABLE_TO_IDENTIFY"
    assert err_detail["title"] == UNREADABLE_TITLE
    assert err_detail["message"] == UNREADABLE_MESSAGE

    # Critical: Quota must NOT be decremented and NO history created
    db = TestingSessionLocal()
    u = db.query(User).filter(User.id == user_id).first()
    assert u.free_scans_used == 0
    assert u.scans_count == 0
    histories = db.query(ScanHistory).filter(ScanHistory.user_id == user_id).all()
    assert len(histories) == 0
    db.close()
