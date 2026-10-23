import re
from enum import Enum
from typing import NamedTuple, Optional, List, Dict, Any
from backend.app.services.product_detector import COMMON_BRANDS, CATEGORY_KEYWORD_MAP

class CompatibilityStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNREADABLE = "UNREADABLE"

class ProductCompatibilityCheck(NamedTuple):
    status: CompatibilityStatus
    title: str
    message: str
    reasons: List[str]
    is_food: bool

INCOMPATIBLE_TITLE = "Incompatible Product"
INCOMPATIBLE_MESSAGE = (
    "This doesn't appear to be a food product. Inside can analyze food ingredients "
    "and nutrition labels only. Please scan a food package or ingredient label."
)

UNREADABLE_TITLE = "Unable to Identify Product"
UNREADABLE_MESSAGE = (
    "Please scan a clear image of the food package or ingredient label."
)

# 1. Non-food markers
BOOK_PATTERNS = [
    r"(?i)\bisbn(?:-1[03])?[:\s\d\-]+",
    r"(?i)\bcopyright\b",
    r"(?i)\ball\s+rights\s+reserved\b",
    r"(?i)\bpublished\s+by\b",
    r"(?i)\bpublisher\b",
    r"(?i)\bchapter\s+\d+\b",
    r"(?i)\bpage\s+\d+\b",
    r"(?i)\btable\s+of\s+contents\b",
    r"(?i)\bauthor\b",
    r"(?i)\bpreface\b",
    r"(?i)\bforeword\b",
    r"(?i)\bbibliography\b",
    r"(?i)\bedition\b",
    r"(?i)\buniversity\s+press\b",
    r"(?i)\bpaperback\b",
    r"(?i)\bhardcover\b",
    r"(?i)\bjournal\s+of\b",
    r"(?i)\bvolume\s+\d+\b",
    r"(?i)\bprinted\s+in\b",
    r"(?i)\breading\s+level\b",
    r"(?i)\blibrary\s+of\s+congress\b",
]

ELECTRONICS_PATTERNS = [
    r"(?i)\bsmartphone\b",
    r"(?i)\bmobile\s+phone\b",
    r"(?i)\bcell\s*phone\b",
    r"(?i)\bsamsung(?:\s+galaxy)?\b",
    r"(?i)\biphone\b",
    r"(?i)\bipad\b",
    r"(?i)\bqualcomm\b",
    r"(?i)\bsnapdragon\b",
    r"(?i)\b\d+\s*gb\s*ram\b",
    r"(?i)\b\d+\s*mp\s*camera\b",
    r"(?i)\bmegapixel\b",
    r"(?i)\bamoled\b",
    r"(?i)\boled\b",
    r"(?i)\blcd(?:\s+display)?\b",
    r"(?i)(?<![\d.])5g\s*(?:lte|nr|network|cellular|phone|smartphone|connectivity)\b",
    r"(?i)\b4g\s*lte\b",
    r"(?i)\b\d+\s*mah\b",
    r"(?i)\bimei\b",
    r"(?i)\bbluetooth\b",
    r"(?i)\bwi-?fi\b",
    r"(?i)\btype-c\b",
    r"(?i)\busb(?:-c)?\b",
    r"(?i)\brefresh\s*rate\b",
    r"(?i)\bprocessor\b",
    r"(?i)\bandroid\s*\d+\b",
    r"(?i)\bios\s*\d+\b",
    r"(?i)\bghz\b",
    r"(?i)\bintel\s*core\b",
    r"(?i)\bdisplay\s*resolution\b",
    r"(?i)\bsim\s*card\b",
    r"(?i)\bdual\s*sim\b",
    r"(?i)\bcharger\b",
    r"(?i)\bearphone\b",
    r"(?i)\bheadphone\b",
]

CLOTHING_PATTERNS = [
    r"(?i)\b\d{1,3}\%\s*(?:cotton|polyester|elastane|spandex|wool|linen|nylon|rayon|silk)\b",
    r"(?i)\bmachine\s*wash\b",
    r"(?i)\bdo\s*not\s*bleach\b",
    r"(?i)\bhand\s*wash\b",
    r"(?i)\btumble\s*dry\b",
    r"(?i)\biron\s*low\b",
    r"(?i)\bdry\s*clean\b",
    r"(?i)\bsize\s*:\s*(?:xs|s|m|l|xl|xxl|\d{2,3})\b",
    r"(?i)\bapparel\b",
    r"(?i)\bgarment\b",
    r"(?i)\bshirt\b",
    r"(?i)\bt-shirt\b",
    r"(?i)\btrousers?\b",
    r"(?i)\bjeans\b",
    r"(?i)\bshoes?\b",
    r"(?i)\bsneakers?\b",
]

FURNITURE_HARDWARE_PATTERNS = [
    r"(?i)\bassembly\s+instructions\b",
    r"(?i)\bchoking\s+hazard\b",
    r"(?i)\bnot\s+suitable\s+for\s+children\b",
    r"(?i)\bmodel\s*(?:no|number)?[:\s\w\d\-]+",
    r"(?i)\b220\s*-\s*240\s*v\b",
    r"(?i)\b50\s*hz\b",
    r"(?i)\bwattage\b",
    r"(?i)\bwarranty\b",
    r"(?i)\bserial\s*(?:no|number)\b",
    r"(?i)\bfurniture\b",
    r"(?i)\bsofa\b",
    r"(?i)\bwardrobe\b",
    r"(?i)\bbookshelf\b",
    r"(?i)\btoy\b",
]

# Medicine / Pharmaceutical markers
MEDICINE_PATTERNS = [
    r"(?i)\brx\s*(?:only)?\b",
    r"(?i)\bprescription\s*(?:drug|medicine|only)\b",
    r"(?i)\bschedule\s*[ghh1]\s*(?:drug|prescription)\b",
    r"(?i)\bdosage\s*:\s*(?:as\s*directed|1\s*tablet|2\s*tablets|\d+\s*mg)\b",
    r"(?i)\bindications?\s*[:\-\s]",
    r"(?i)\bcontraindications?\b",
    r"(?i)\bactive\s*pharmaceutical\s*ingredient\b",
    r"(?i)\btherapeutic\s*use\b",
    r"(?i)\bpharmacist\b",
    r"(?i)\bpharmaceuticals?\b",
    r"(?i)\b(?:tablets?|capsules?|syrup|injection|ointment)\s*i\.?p\.?\b",
    r"(?i)\bnot\s+for\s+human\s+consumption\b",
]

# Cosmetic / Personal Care markers
COSMETIC_PATTERNS = [
    r"(?i)\bfor\s*external\s*use\s*only\b",
    r"(?i)\bshampoo\b",
    r"(?i)\bconditioner\b",
    r"(?i)\bface\s*wash\b",
    r"(?i)\bbody\s*wash\b",
    r"(?i)\bsoap\s*bar\b",
    r"(?i)\bmoisturizer\b",
    r"(?i)\bsunscreen\b",
    r"(?i)\bbody\s*lotion\b",
    r"(?i)\btoothpaste\b",
    r"(?i)\bmouthwash\b",
    r"(?i)\bdeodorant\b",
    r"(?i)\bperfume\b",
    r"(?i)\bmascara\b",
    r"(?i)\blipstick\b",
]

# 2. Strong food markers
FOOD_HEADER_PATTERNS = [
    r"(?i)\b(?:ingredients|ingredients\s*used|ingredients\s*list|composition)\s*[:\-\s]",
    r"(?i)\bcontents\s*[:\-\s]",
    r"(?i)\bcontains\s+added\s+flavour",
    r"(?i)\bcontains\s+allergens?",
    r"(?i)\ballergen\s+(?:advice|declaration|information)\b",
    r"(?i)\bmay\s+contain\s*[:\-\s]",
]

NUTRITION_PANEL_PATTERNS = [
    r"(?i)\bnutrition(?:al)?\s*(?:information|facts|values?)\b",
    r"(?i)\bper\s*100\s*(?:g|ml)\b",
    r"(?i)\bper\s*serving\b",
    r"(?i)\benergy\s*[:\-\s]*\d+\s*(?:kcal|cal|kj)\b",
    r"(?i)\b(?:total\s*fat|saturated\s*fat|trans\s*fat|cholesterol|carbohydrate|total\s*sugars|added\s*sugars|dietary\s*fiber)\b",
]

FOOD_REGULATORY_PATTERNS = [
    r"(?i)\bfssai\b",
    r"(?i)\blic\.?\s*(?:no\.?)?\s*[:\s\d\-]+",
    r"(?i)\bbest\s+before\b",
    r"(?i)\buse\s+by\b",
    r"(?i)\bexp(?:iry)?\.?\s*(?:date)?\b",
    r"(?i)\bmfg\.?\s*(?:date)?\b",
    r"(?i)\bnet\s*(?:wt\.?|weight|qty|quantity)\b",
    r"(?i)\bstore\s+in\s+a\s+cool\b",
    r"(?i)\bkeep\s+refrigerated\b",
    r"(?i)\bveg(?:etarian)?\s+logo\b",
]

FOOD_ADDITIVE_PATTERNS = [
    r"(?i)\b(?:ins|e)\s*\d{3,4}[a-z]?\b",
    r"(?i)\b(?:emulsifier|stabilizer|acidity\s*regulator|raising\s*agent|preservative|antioxidant|flavour\s*enhancer|thickener|anti-caking\s*agent|leavening\s*agent)\b",
]

# Recognizable common food items (at least 2 should match if no header present)
FOOD_SPECIFIC_ITEMS = [
    "wheat flour", "refined wheat flour", "atta", "maida", "palm oil", "palmolein",
    "vegetable oil", "sunflower oil", "soybean oil", "mustard oil", "liquid glucose",
    "invert sugar", "cocoa solids", "cocoa butter", "cocoa powder", "milk solids",
    "skimmed milk", "whole milk", "toned milk", "iodised salt", "baking powder",
    "citric acid", "soy lecithin", "lecithin", "yeast", "semolina", "durum wheat",
    "potato flakes", "potato starch", "corn starch", "corn flour", "rice flour",
    "rolled oats", "oat flakes", "corn flakes", "mango pulp", "apple juice concentrate",
    "malt extract", "cardamom", "cinnamon", "turmeric", "cumin", "coriander powder"
]


def evaluate_product_compatibility(
    ocr_text: str,
    product_name: Optional[str] = None,
    product_category: Optional[str] = None
) -> ProductCompatibilityCheck:
    """
    Evaluates whether the scanned text belongs to a valid food product or label.
    Strictly prevents non-food objects (books, phones, clothes, furniture, medicines, cosmetics)
    or unreadable/blurry scans from being scored.
    """
    if not ocr_text or not ocr_text.strip():
        return ProductCompatibilityCheck(
            status=CompatibilityStatus.UNREADABLE,
            title=UNREADABLE_TITLE,
            message=UNREADABLE_MESSAGE,
            reasons=["Image or OCR text is blank."],
            is_food=False
        )

    clean_text = ocr_text.strip()
    alphanumeric_chars = re.findall(r"[a-zA-Z0-9]", clean_text)
    words = re.findall(r"[a-zA-Z]{2,}", clean_text)

    # 1. Unclear / Unreadable / Gibberish Check
    if len(alphanumeric_chars) < 12 or len(words) < 3:
        return ProductCompatibilityCheck(
            status=CompatibilityStatus.UNREADABLE,
            title=UNREADABLE_TITLE,
            message=UNREADABLE_MESSAGE,
            reasons=["Text is too short or lacks readable words."],
            is_food=False
        )

    lower_text = clean_text.lower()

    # 2. Check for explicit Incompatible Non-Food Objects
    non_food_matches: List[str] = []

    for p in MEDICINE_PATTERNS:
        if re.search(p, clean_text):
            non_food_matches.append("pharmaceutical / medicinal marker")

    for p in COSMETIC_PATTERNS:
        if re.search(p, clean_text):
            non_food_matches.append("cosmetic / personal care marker")

    for p in BOOK_PATTERNS:
        if re.search(p, clean_text):
            non_food_matches.append("book / print publication marker")

    for p in ELECTRONICS_PATTERNS:
        if re.search(p, clean_text):
            non_food_matches.append("electronics / mobile device marker")

    for p in CLOTHING_PATTERNS:
        if re.search(p, clean_text):
            non_food_matches.append("clothing / apparel marker")

    for p in FURNITURE_HARDWARE_PATTERNS:
        if re.search(p, clean_text):
            non_food_matches.append("furniture / hardware marker")

    # Prose sentence detection
    if re.search(r"(?i)\b(?:in this chapter|the author|we argue that|as discussed in|study shows that|furthermore,|moreover,)\b", clean_text):
        non_food_matches.append("literary / academic prose discourse")

    # If non-food markers are found:
    if non_food_matches:
        specific_title = INCOMPATIBLE_TITLE
        specific_msg = INCOMPATIBLE_MESSAGE
        if any("pharmaceutical" in m for m in non_food_matches):
            specific_title = "Incompatible Product: Medicine / Drug"
            specific_msg = (
                "This appears to be a medicine or pharmaceutical product. Inside is designed to analyze "
                "food and beverage products only. Please consult a doctor or pharmacist for medication details."
            )
        elif any("cosmetic" in m for m in non_food_matches):
            specific_title = "Incompatible Product: Cosmetic / Personal Care"
            specific_msg = (
                "This appears to be a cosmetic or personal care product. Inside is designed to analyze "
                "edible food and beverage products only."
            )

        return ProductCompatibilityCheck(
            status=CompatibilityStatus.INCOMPATIBLE,
            title=specific_title,
            message=specific_msg,
            reasons=[f"Detected non-food indicators: {', '.join(set(non_food_matches))}"],
            is_food=False
        )

    # 3. Check for Food Evidence
    food_evidence_score = 0
    food_evidences: List[str] = []

    # Evidence A: Ingredient header
    if any(re.search(p, clean_text) for p in FOOD_HEADER_PATTERNS):
        food_evidence_score += 3
        food_evidences.append("ingredient list header")

    # Evidence B: Nutrition panel
    if any(re.search(p, clean_text) for p in NUTRITION_PANEL_PATTERNS):
        food_evidence_score += 3
        food_evidences.append("nutrition information panel")

    # Evidence C: Food regulation / packaging info (FSSAI, Net Wt, Best Before, etc.)
    reg_matches = [p for p in FOOD_REGULATORY_PATTERNS if re.search(p, clean_text)]
    if reg_matches:
        food_evidence_score += min(len(reg_matches) * 2, 4)
        food_evidences.append("food packaging & regulatory markers")

    # Evidence D: Food additive codes (INS / E numbers or additive functional classes)
    add_matches = [p for p in FOOD_ADDITIVE_PATTERNS if re.search(p, clean_text)]
    if add_matches:
        food_evidence_score += min(len(add_matches) * 2, 3)
        food_evidences.append("food additive & INS codes")

    # Evidence E: Known Food Brands
    for brand in COMMON_BRANDS:
        if re.search(rf"(?i)\b{re.escape(brand)}\b", clean_text):
            food_evidence_score += 2
            food_evidences.append(f"recognized food brand ({brand})")
            break

    # Evidence F: Known Food Categories
    for keywords, category in CATEGORY_KEYWORD_MAP:
        if category != "Food Product":
            for kw in keywords:
                if re.search(rf"(?i)\b{re.escape(kw)}\b", clean_text):
                    food_evidence_score += 1
                    food_evidences.append(f"food category ({category})")
                    break
            if food_evidence_score >= 8:
                break

    # Evidence G: Specific food formulation ingredients
    matched_ingredients = [item for item in FOOD_SPECIFIC_ITEMS if item in lower_text]
    if len(matched_ingredients) >= 2:
        food_evidence_score += min(len(matched_ingredients), 3)
        food_evidences.append(f"recognized formulation ingredients ({len(matched_ingredients)} items)")

    # 4. Final Compatibility Decision
    # Threshold: Must have at least 3 points of food evidence to be compatible.
    if food_evidence_score >= 3:
        return ProductCompatibilityCheck(
            status=CompatibilityStatus.COMPATIBLE,
            title="Compatible Food Product",
            message="Food product label verified.",
            reasons=food_evidences,
            is_food=True
        )

    # If it didn't pass the food threshold:
    if non_food_matches or re.search(r"(?i)\b(?:phone|laptop|cable|shirt|t-shirt|pant|shoes|toy|plastic|screw|paper|book|novel)\b", clean_text):
        return ProductCompatibilityCheck(
            status=CompatibilityStatus.INCOMPATIBLE,
            title=INCOMPATIBLE_TITLE,
            message=INCOMPATIBLE_MESSAGE,
            reasons=["Not a food product."],
            is_food=False
        )

    # Otherwise, it is an ambiguous, unclear, or insufficient scan of a label
    return ProductCompatibilityCheck(
        status=CompatibilityStatus.UNREADABLE,
        title=UNREADABLE_TITLE,
        message=UNREADABLE_MESSAGE,
        reasons=["Insufficient evidence of a food product or ingredient label."],
        is_food=False
    )
