import re
from typing import List, Tuple, Optional, Dict, Any

CONSUMER_CATEGORIES = [
    "Biscuits",
    "Chips & Snacks",
    "Chocolate",
    "Candy",
    "Soft Drink",
    "Juice",
    "Dairy",
    "Milk Product",
    "Breakfast Cereal",
    "Instant Food",
    "Noodles",
    "Sauces & Condiments",
    "Bakery",
    "Frozen Food",
    "Protein Product",
    "Beverage",
    "Tea & Coffee",
    "Ready-to-Eat",
    "Baby Food",
    "Other Food",
    "Food Product"
]

GENERIC_NAMES = {
    "food product",
    "scanned product",
    "scanned food product",
    "unknown product",
    "product",
    "unknown",
    ""
}

# Known common brands to assist high-accuracy OCR brand detection
COMMON_BRANDS = [
    "Britannia", "Parle", "Parle-G", "Amul", "Nestle", "Maggi", "Cadbury", "Dairy Milk",
    "Coca-Cola", "Coke", "Pepsi", "Lay's", "Lays", "Haldiram's", "Haldiram", "Kurkure",
    "Tropicana", "Real", "Kissan", "Kellogg's", "Kelloggs", "Quaker", "Doritos", "Oreo",
    "Sunfeast", "Dark Fantasy", "Hershey's", "Hersheys", "Epigamia", "Bournvita", "Horlicks",
    "Mother Dairy", "Dabur", "Marico", "Tata", "Saffola", "MTR", "Bikaji", "Balaji",
    "Lipton", "Nescafe", "Red Label", "Taj Mahal", "Bru", "Boost", "Complan", "Yakult",
    "NutriChoice", "Good Day", "Marie Gold", "Monaco", "Krackjack", "Hide & Seek", "5 Star",
    "KitKat", "Snickers", "Sprite", "Fanta", "Thums Up", "Limca", "Maaza", "Frooti", "Slice",
    "Appy Fizz", "Paper Boat", "Bingo", "Pringles", "Too Yumm", "Chocos", "Koko Krunch",
    "Corn Flakes", "Chings", "Knorr", "Maggi Cuppa", "Ching's Secret", "Top Ramen",
    "Nutella", "Nutrela", "Amul Butter", "Amul Taaza", "Amul Gold", "Amul Kool", "Activia"
]

CATEGORY_KEYWORD_MAP: List[Tuple[List[str], str]] = [
    (["biscuit", "biscuits", "cookie", "cookies", "cracker", "crackers", "wafer", "wafers", "rusk", "shortbread", "digestive"], "Biscuits"),
    (["chip", "chips", "crisp", "crisps", "nacho", "nachos", "popcorn", "namkeen", "bhujia", "sev", "peanut", "peanuts", "snack", "snacks", "pretzel", "puffs", "makhana"], "Chips & Snacks"),
    (["chocolate", "chocolates", "cocoa", "truffle", "praline", "cacao"], "Chocolate"),
    (["candy", "candies", "gummy", "gummies", "toffee", "toffees", "lollipop", "marshmallow", "jelly", "chewing gum", "mint"], "Candy"),
    (["soft drink", "soda", "sodas", "carbonated", "cola", "colas", "fizzy", "lemonade", "tonic"], "Soft Drink"),
    (["juice", "juices", "nectar", "smoothie", "squash", "fruit drink", "pulpy"], "Juice"),
    (["curd", "paneer", "cheese", "cheeses", "butter", "ghee", "yogurt", "yoghurt", "dahi", "dairy"], "Dairy"),
    (["milk", "milkshake", "condensed milk", "dairy drink", "flavoured milk", "milk powder", "toned milk"], "Milk Product"),
    (["breakfast cereal", "cereal", "cereals", "oat", "oats", "muesli", "granola", "flakes", "cornflakes", "corn flakes"], "Breakfast Cereal"),
    (["noodle", "noodles", "ramen", "vermicelli", "pasta", "macaroni", "spaghetti"], "Noodles"),
    (["instant", "ready meal", "meal kit", "instant mix", "instant soup", "pre-cooked"], "Instant Food"),
    (["sauce", "sauces", "ketchup", "mayonnaise", "mayo", "condiment", "condiments", "chutney", "pickle", "dressing", "mustard", "dip"], "Sauces & Condiments"),
    (["bread", "breads", "cake", "cakes", "pastry", "pastries", "muffin", "muffins", "bun", "buns", "croissant", "croissants", "toast", "bakery"], "Bakery"),
    (["ice cream", "ice-cream", "frozen", "kulfi", "gelato", "popsicle", "sorbet"], "Frozen Food"),
    (["protein bar", "protein powder", "whey", "isolate", "bcaa", "protein shake", "protein supplement"], "Protein Product"),
    (["tea", "coffee", "espresso", "cappuccino", "latte", "chai", "green tea", "black tea", "brew"], "Tea & Coffee"),
    (["energy drink", "beverage", "beverages", "isotonic", "sports drink", "drink"], "Beverage"),
    (["baby food", "infant formula", "cerelac", "infant"], "Baby Food"),
    (["ready-to-eat", "ready to eat"], "Ready-to-Eat"),
]


def normalize_category(raw_category: Optional[str]) -> str:
    """
    Normalizes Open Food Facts category tags or raw strings into a clean consumer-friendly category.
    """
    if not raw_category or not str(raw_category).strip():
        return "Food Product"

    cleaned = str(raw_category).lower()
    # Remove open food facts tag prefixes like 'en:', 'fr:'
    cleaned = re.sub(r"\b[a-z]{2}:", " ", cleaned)
    cleaned = re.sub(r"[\-_,;]+", " ", cleaned)

    for keywords, category in CATEGORY_KEYWORD_MAP:
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", cleaned):
                return category

    # Check direct substring matching if word boundary didn't catch it
    for keywords, category in CATEGORY_KEYWORD_MAP:
        for kw in keywords:
            if kw in cleaned:
                return category

    return "Food Product"


def extract_product_name_from_ocr(ocr_text: str) -> Optional[str]:
    """
    Priority 2: Extracts recognizable brand or product title from the raw OCR text.
    """
    if not ocr_text or len(ocr_text.strip()) < 3:
        return None

    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    if not lines:
        return None

    # Step A: Look for known brands in lines before 'INGREDIENTS:'
    before_ingredients_lines = []
    for line in lines:
        if re.search(r"(?i)\b(?:ingredients|composition|contents)\b", line):
            break
        before_ingredients_lines.append(line)

    search_lines = before_ingredients_lines if before_ingredients_lines else lines[:5]

    for line in search_lines:
        # Ignore noisy lines with barcodes, dates, licenses
        if re.search(r"(?i)\b(?:mfg|exp|batch|mrp|fssai|lic|net\s*wt|nutrition|per\s*100)\b", line):
            continue

        for brand in COMMON_BRANDS:
            pattern = rf"(?i)\b{re.escape(brand)}\b"
            if re.search(pattern, line):
                # Clean up the line: remove punctuation noise, keep letters, numbers, hyphens
                cleaned_line = re.sub(r"[^\w\s\-\'\&]", " ", line)
                cleaned_line = re.sub(r"\s+", " ", cleaned_line).strip()
                if len(cleaned_line) >= len(brand) and len(cleaned_line) <= 60:
                    return cleaned_line

    # Step B: If no known brand was matched, look for an obvious clean header title line before ingredients
    for line in before_ingredients_lines:
        if re.search(r"(?i)\b(?:mfg|exp|batch|mrp|fssai|lic|net\s*wt|nutrition|per\s*100|weight|store\s+in)\b", line):
            continue
        cleaned = re.sub(r"[^\w\s\-\'\&]", " ", line)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Must be title-case or uppercase words and between 4 and 45 chars
        if 4 <= len(cleaned) <= 45 and not re.match(r"^[\d\s\.\,\-]+$", cleaned):
            # Verify it has at least one alphabetical word
            if re.search(r"[a-zA-Z]{3,}", cleaned):
                return cleaned

    return None


def infer_product_and_category_from_ingredients(
    ingredients: List[str],
    ocr_text: Optional[str] = None
) -> Tuple[str, str]:
    """
    Priority 3 Heuristic: Analyzes ingredient composition to infer product descriptor and category.
    """
    combined = " ".join(ingredients).lower()
    if ocr_text:
        combined += " " + ocr_text.lower()

    # Rule 1: Biscuits & Cookies
    if any(k in combined for k in ["biscuit", "cookie", "digestive", "wafer", "rusk"]) or (
        any(k in combined for k in ["refined wheat flour", "wheat flour", "atta", "maida"]) and
        any(k in combined for k in ["palm oil", "edible vegetable oil", "butter", "fat"]) and
        any(k in combined for k in ["sugar", "invert sugar", "liquid glucose"]) and
        any(k in combined for k in ["leavening", "raising agent", "500", "503", "ins 500", "ins 503", "baking powder"])
    ):
        return "Biscuits / Cookies", "Biscuits"

    # Rule 2: Soft Drinks / Carbonated Beverages
    if any(k in combined for k in ["carbonated water", "carbonated beverage", "cola", "fizz"]) or (
        "carbonated" in combined and any(k in combined for k in ["sugar", "acidity regulator", "caffeine", "caramel colour", "flavouring"])
    ):
        return "Carbonated Soft Drink", "Soft Drink"

    # Rule 3: Chips & Savory Snacks
    if any(k in combined for k in ["potato", "potato flakes", "corn meal", "rice flour", "besan", "gram flour"]) and (
        any(k in combined for k in ["edible vegetable oil", "palmolein", "sunflower oil"]) and
        any(k in combined for k in ["salt", "spices", "seasoning", "chilli powder", "onion powder", "masala"])
    ):
        return "Savory Chips & Snacks", "Chips & Snacks"

    # Rule 4: Chocolate
    if (any(k in combined for k in ["cocoa solids", "cocoa butter", "cocoa mass", "cocoa powder", "chocolate"]) and
        any(k in combined for k in ["sugar", "milk solids", "lecithin", "emulsifier 322", "ins 322"])):
        return "Chocolate Confectionery", "Chocolate"

    # Rule 5: Noodles & Pasta
    if any(k in combined for k in ["noodle", "noodles", "tastemaker", "seasoning mix", "hydrolysed peanut protein", "wheat gluten"]) or (
        any(k in combined for k in ["wheat flour", "semolina", "durum"]) and "noodle" in combined
    ):
        return "Instant Noodles", "Noodles"

    # Rule 6: Juices & Fruit Drinks
    if any(k in combined for k in ["fruit juice", "fruit pulp", "fruit concentrate", "mango pulp", "apple juice", "orange juice"]) or (
        "water" in combined and "sugar" in combined and any(k in combined for k in ["acidity regulator 330", "citric acid", "fruit", "juice"])
    ):
        return "Fruit Juice Drink", "Juice"

    # Rule 7: Milk / Dairy
    if any(k in combined for k in ["pasteurized milk", "standardized milk", "toned milk", "cow milk", "milk solids", "paneer", "curd", "yogurt", "cheese"]):
        if any(k in combined for k in ["culture", "lactobacillus", "starter"]):
            return "Cultured Dairy / Yogurt", "Dairy"
        return "Milk Product", "Milk Product"

    # Rule 8: Breakfast Cereals
    if any(k in combined for k in ["rolled oats", "oat flakes", "corn flakes", "wheat flakes", "muesli", "granola"]):
        return "Breakfast Cereal", "Breakfast Cereal"

    # Rule 9: Sauces & Condiments
    if any(k in combined for k in ["tomato paste", "tomato puree", "vinegar", "acetic acid", "tamarind", "mayonnaise", "mustard"]):
        return "Sauce / Condiment", "Sauces & Condiments"

    # Rule 10: Candy & Confectionery
    if any(k in combined for k in ["liquid glucose", "glucose syrup", "pectin", "gelatin", "gum base"]) and (
        any(k in combined for k in ["sugar", "citric acid", "artificial colour", "flavour"])
    ):
        return "Candy / Confectionery", "Candy"

    # Rule 11: Protein Products
    if any(k in combined for k in ["whey protein", "soy protein isolate", "milk protein isolate", "bcaa", "casein"]):
        return "Protein Supplement", "Protein Product"

    # Rule 12: Tea & Coffee
    if any(k in combined for k in ["tea leaves", "tea extract", "instant tea", "coffee beans", "instant coffee", "chicory"]):
        return "Tea / Coffee Beverage", "Tea & Coffee"

    # Rule 13: Bakery Products
    if any(k in combined for k in ["yeast", "bread improver", "wheat flour", "maida"]) and any(k in combined for k in ["sugar", "salt", "gluten"]):
        return "Bakery Product", "Bakery"

    # Priority 4 Fallback
    return "Unknown Product", "Food Product"


def resolve_product_name_and_category(
    provided_name: Optional[str],
    provided_category: Optional[str],
    ocr_text: Optional[str],
    parsed_ingredients: List[str],
    ai_detected_name: Optional[str] = None,
    ai_detected_category: Optional[str] = None
) -> Tuple[str, str]:
    """
    Main resolution pipeline adhering to the specified priority order:
    1. Valid Barcode / provided lookup name
    2. OCR recognizable product/brand name
    3. AI / Heuristic inference
    4. Safe fallback: 'Unknown Product' / 'Food Product'
    """
    final_name: Optional[str] = None
    final_category: Optional[str] = None

    # Priority 1: Check provided name / category from barcode / client
    if provided_name and provided_name.strip():
        cleaned_prov = provided_name.strip()
        if cleaned_prov.lower() not in GENERIC_NAMES:
            final_name = cleaned_prov

    if provided_category and provided_category.strip():
        norm_cat = normalize_category(provided_category)
        if norm_cat != "Food Product":
            final_category = norm_cat

    # Priority 2: Extract recognizable product/brand from OCR text
    if not final_name and ocr_text:
        ocr_name = extract_product_name_from_ocr(ocr_text)
        if ocr_name:
            final_name = ocr_name
            # If we found a recognizable name like "Britannia NutriChoice Digestive", try category matching
            if not final_category:
                matched_cat = normalize_category(ocr_name)
                if matched_cat != "Food Product":
                    final_category = matched_cat

    # Priority 3: AI detection or Heuristic Inference
    if not final_name and ai_detected_name:
        cleaned_ai = ai_detected_name.strip()
        if cleaned_ai.lower() not in GENERIC_NAMES:
            final_name = cleaned_ai

    if not final_category and ai_detected_category:
        norm_ai_cat = normalize_category(ai_detected_category)
        if norm_ai_cat != "Food Product":
            final_category = norm_ai_cat

    # Priority 3 Fallback Heuristic: Infer from ingredients
    if not final_name or not final_category:
        inferred_name, inferred_cat = infer_product_and_category_from_ingredients(
            parsed_ingredients,
            ocr_text
        )
        if not final_name:
            final_name = inferred_name
        if not final_category:
            final_category = inferred_cat

    # Priority 4: Safe Fallbacks
    if not final_name or final_name.strip().lower() in GENERIC_NAMES:
        final_name = "Unknown Product"

    if not final_category or final_category.strip() == "":
        final_category = "Food Product"

    return final_name, final_category
