import re
from typing import List, Tuple, Dict, Any, Optional

# =========================================================================
# PACKAGING & REGULATORY CUTOFF PATTERNS
# Marks the end of an ingredient list on food packaging.
# =========================================================================
SECTION_CUTOFF_PATTERNS = [
    # Allergens & Cross-Contamination
    r"(?i)\b(?:allergen\s+(?:advice|declaration|information|warning)|contains\s+allergens?|may\s+contain|allergen\s*info)\s*[:\-\s]",
    # Manufacturing, Packing, Distribution & Corporate Entities
    r"(?i)\b(?:manufactured\s*(?:by|at|for|in)?|mfd(?:\.|\s*(?:by|at|for))?|marketed\s*(?:by|for)?|packed\s*(?:by|at)?|pkd(?:\.|\s*(?:by|at))?|distributed\s*by|imported\s*by|produced\s*by|made\s*in|product\s*of|repacked\s*by)\b",
    r"(?i)\b(?:factory|plant|unit\s*[0-9]|plot\s*(?:no\.?)?|khasra|survey\s*no|industrial\s*(?:area|estate)|regd?\.\s*office|registered\s*office|corp(?:orate)?\s*office|head\s*office)\b",
    r"(?i)\b(?:cin\s*[:\-\s]|cin\s*no|gstin|pan\s*no)\b",
    # Postal addresses & PIN codes
    r"(?i)\b(?:p\.?o\.?\s*box|road|street|marg|nagar|sector|phase|taluk|taluka|district|post\s*office)\b",
    r"(?i)\bpin\s*(?:code)?\s*[:\-\s]*\d{6}\b",
    # Licensing & Regulatory
    r"(?i)\b(?:fssai|lic\.?\s*(?:no\.?)?|license\s*no|regd?\.\s*(?:no|tm)|trademark|issuing\s+authority|agmark|isi\s*mark)\b",
    # Dates, Batches & Shelf Life
    r"(?i)\b(?:best\s+before|use\s+by|expiry\s+date|exp\.?\s*(?:date|dt)?|mfg\.?\s*(?:date|dt)?|batch\s*(?:no|num)?|lot\s*(?:no|num)?|date\s*of\s*mfg)\b",
    # Quantities, Weights & Pricing
    r"(?i)\b(?:net\s*(?:wt\.?|weight|qty|quantity)|m\.?r\.?p\.?|incl\.?\s*of\s*all\s*taxes|gross\s*weight|unit\s*sale\s*price)\b",
    # Storage Conditions & Instructions
    r"(?i)\b(?:store\s+in\s+a\s+(?:cool|dry)|keep\s+(?:refrigerated|in\s+a\s+cool|away\s+from)|do\s+not\s+(?:freeze|accept|buy)|once\s+opened|transfer\s+to\s+an\s+airtight)\b",
    # Usage & Preparation Instructions
    r"(?i)\b(?:how\s+to\s+use|directions\s*(?:for\s*use)?|preparation\s*(?:instructions?)?|serving\s*suggestion|serve\s*chilled|shake\s*well\s*before|consume\s*within)\b",
    # Medical Disclaimers, Warnings & Dietary Supplements
    r"(?i)\b(?:not\s+for\s+medicinal\s+use|dietary\s+supplement|health\s+supplement|consult\s+(?:your\s+)?(?:doctor|physician)|keep\s+out\s+of\s+reach\s+of\s+children|statutory\s*warning|caution\s*:)\b",
    # Customer Contact, Feedback & URLs
    r"(?i)\b(?:customer\s*(?:care|support)|consumer\s*(?:care|cell|affairs)|for\s*feedback|toll\s*free|write\s*to\s*us|feedback\@|contact\s*us|website\s*:|www\.[\w\.\-]+|\b[\w\.\-]+@[a-zA-Z_]+?\.[a-zA-Z]{2,3}\b)\b",
    # Nutrition panel start
    r"(?i)\b(?:nutrition(?:al)?\s*(?:information|facts|values?|declaration)|typical\s*values?)\b",
    r"(?i)\bper\s*100\s*(?:g|ml)\b",
]

# Common food brand names to prevent them from becoming ingredients
KNOWN_BRAND_NAMES = [
    "britannia", "parle", "nestle", "cadbury", "mondelez", "lays", "lay's",
    "haldiram", "haldirams", "bikaji", "itc", "sunfeast", "oreo", "kurkure",
    "doritos", "pringles", "kellogg's", "kelloggs", "quaker", "dabur", "tata",
    "kissan", "maggi", "hershey's", "hersheys", "ferrero", "nutella", "mars",
    "snickers", "kitkat", "thums up", "sprite", "fanta", "coca-cola", "coca cola",
    "pepsi", "7up", "mountain dew", "limca", "maaza", "frooti", "slice",
    "tropicana", "red bull", "amul", "mother dairy", "nandini", "epigamia",
    "good day", "marie gold", "bourbon", "dark fantasy", "hide & seek", "monaco",
    "krackjack", "little hearts", "jim jam", "milkybar", "perk", "munch", "silk",
    "nutrichoice", "bingo", "crax", "act ii", "safal", "chocos", "real", "del monte",
    "dr. oetker", "veeba", "cremica", "heinz", "hellmann's", "mccain"
]

# Product category/heading terms to discard
PRODUCT_HEADINGS = [
    "biscuits", "cookies", "crackers", "wafers", "chips", "crisps", "potato chips",
    "namkeen", "bhujia", "chocolate", "milk chocolate", "dark chocolate", "confectionery",
    "soft drink", "carbonated beverage", "energy drink", "fruit juice",
    "breakfast cereal", "corn flakes", "tomato ketchup", "ketchup", "sauce",
    "mayonnaise", "instant noodles", "noodles", "pasta", "spread", "peanut butter",
    "jam", "pickle", "ready to eat", "snack food"
]

# Marketing claims to discard
MARKETING_CLAIMS = [
    r"(?i)^100\%\s*(?:veg|vegetarian|real|natural|pure)$",
    r"(?i)^no\s*(?:added\s*preservatives|artificial\s*colours?|preservatives|trans\s*fat)$",
    r"(?i)^zero\s*(?:trans\s*fat|cholesterol|sugar|calories)$",
    r"(?i)^(?:high|rich\s*in)\s*(?:protein|fiber|fibre|iron|calcium)$",
    r"(?i)^serving\s*suggestion$",
    r"(?i)^original\s*(?:taste|recipe|formula)$",
    r"(?i)^crunchy\s*(?:&|and)\s*delicious$",
    r"(?i)^freshly\s*packed$",
    r"(?i)^baked\s*not\s*fried$",
]

# Section headers for ingredients
INGREDIENT_SECTION_HEADERS = [
    r"(?i)\b(?:ingredients|ingredients\s*used|ingredients\s*list|ingredient\s*declaration|ingredient\s*statement|composition|contents)\s*[:\-\s]",
    r"(?i)\b(?:ingrédients|ingredientes|zutaten|samagri)\s*[:\-\s]",
]

def clean_raw_ocr(raw_text: str) -> str:
    """Removes non-ascii noise, standardizes quotes, brackets, and spaces."""
    if not raw_text:
        return ""
    cleaned = raw_text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    cleaned = cleaned.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    cleaned = re.sub(r"[^\x20-\x7E\n\r]", " ", cleaned)
    cleaned = re.sub(r"\r\n", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()

# =========================================================================
# NUTRITION FACTS EXTRACTION
# =========================================================================
def extract_nutrition_facts(text: str) -> Tuple[Dict[str, Any], str]:
    """
    Extracts nutrition facts into a structured dictionary and removes
    the nutrition panel region from the text so nutrition facts never
    contaminate the ingredient list.
    
    Returns (nutrition_facts_dict, text_without_nutrition_panel).
    """
    cleaned = clean_raw_ocr(text)
    nutrition: Dict[str, Any] = {}

    # Check for serving size or basis (per 100g, per serving)
    per_unit_match = re.search(r"(?i)\b(per\s*100\s*(?:g|ml)|per\s*serving|per\s*pack(?:et)?|per\s*portion)\b", cleaned)
    if per_unit_match:
        nutrition["per_unit"] = per_unit_match.group(1).title()

    serving_size_match = re.search(r"(?i)\bserving\s*size\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?\s*(?:g|ml|oz|tbsp|piece|pack)?)\b", cleaned)
    if serving_size_match:
        nutrition["serving_size"] = serving_size_match.group(1).strip()

    # Nutrient regex extractors
    nutrients = [
        ("energy_kcal", [
            r"(?i)\benergy(?:\s*value)?\s*(?:\(kcal\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*(?:kcal)?\b",
            r"(?i)\b([0-9]+(?:\.[0-9]+)?)\s*kcal\b",
            r"(?i)\bcalories\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)\b",
        ]),
        ("protein_g", [
            r"(?i)\bprotein\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b",
        ]),
        ("carbohydrates_g", [
            r"(?i)\b(?:carbohydrates?|total\s*carbohydrates?|carbs?)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b",
        ]),
        ("total_sugars_g", [
            r"(?i)\b(?:total\s*sugars?|sugars?)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b",
        ]),
        ("added_sugars_g", [
            r"(?i)\badded\s*sugars?\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b",
        ]),
        ("dietary_fiber_g", [
            r"(?i)\b(?:dietary\s*fiber|dietary\s*fibre|fiber|fibre)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b",
        ]),
        ("total_fat_g", [
            r"(?i)\b(?:total\s*fat|fat)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b",
        ]),
        ("saturated_fat_g", [
            r"(?i)\bsaturated\s*(?:fat|fatty\s*acids?)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b",
        ]),
        ("trans_fat_g", [
            r"(?i)\btrans\s*(?:fat|fatty\s*acids?)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b",
        ]),
        ("cholesterol_mg", [
            r"(?i)\bcholesterol\s*(?:\(mg\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*mg?\b",
        ]),
        ("sodium_mg", [
            r"(?i)\bsodium\s*(?:\(mg\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*mg?\b",
        ]),
    ]

    for key, patterns in nutrients:
        for pat in patterns:
            match = re.search(pat, cleaned)
            if match:
                try:
                    val = float(match.group(1))
                    nutrition[key] = val
                    break
                except (ValueError, IndexError):
                    pass

    # Locate and excise nutrition panel from the text
    panel_start_patterns = [
        r"(?i)\b(?:nutrition(?:al)?\s*(?:information|facts|values?|declaration)|typical\s*values?)\b",
        r"(?i)\bper\s*100\s*(?:g|ml)\s*(?:\(approx\.\))?\b",
    ]

    text_without_nutrition = cleaned
    for p_pat in panel_start_patterns:
        match = re.search(p_pat, text_without_nutrition)
        if match:
            start_idx = match.start()
            # Find end of nutrition block: look for next section header like 'INGREDIENTS:'
            ing_header_match = None
            for h in INGREDIENT_SECTION_HEADERS:
                hm = re.search(h, text_without_nutrition[start_idx:])
                if hm and hm.start() > 0:
                    ing_header_match = start_idx + hm.start()
                    break

            if ing_header_match:
                # Nutrition was before ingredients
                text_without_nutrition = (
                    text_without_nutrition[:start_idx] + " " + text_without_nutrition[ing_header_match:]
                )
            else:
                # Nutrition was after ingredients or at end
                text_without_nutrition = text_without_nutrition[:start_idx]
            break

    # Also clean explicit single nutrient lines that might linger
    clean_lines = []
    for line in text_without_nutrition.split("\n"):
        line_strip = line.strip()
        if re.search(r"(?i)^(?:energy|protein|carbohydrate|fat|sugars?|sodium|cholesterol)\s*[:\-\s]*[0-9]+", line_strip):
            continue
        clean_lines.append(line)

    text_without_nutrition = "\n".join(clean_lines).strip()
    return nutrition, text_without_nutrition

# =========================================================================
# INGREDIENT SECTION EXTRACTION
# =========================================================================
def extract_ingredient_section(text: str) -> Tuple[str, bool]:
    """
    Extracts the substring representing the ingredient declaration.
    Returns (ingredient_section_text, header_found_boolean).
    """
    cleaned = clean_raw_ocr(text)

    # 1. Search for explicit ingredient header
    start_pos = -1
    for pattern in INGREDIENT_SECTION_HEADERS:
        match = re.search(pattern, cleaned)
        if match:
            start_pos = match.end()
            break

    header_found = start_pos != -1

    if header_found:
        raw_section = cleaned[start_pos:]
    else:
        # Check if text contains high density of ingredients or additives
        additive_match = re.search(r"(?i)\b(?:ins|e)\s*\d{3,4}\b", cleaned)
        comma_count = cleaned.count(",")
        if additive_match or comma_count >= 3:
            raw_section = cleaned
        else:
            # No credible ingredient list found
            return "", False

    # 2. Find cutoff boundary (earliest occurrence of packaging noise / allergen block)
    cutoff_pos = len(raw_section)
    for pat in SECTION_CUTOFF_PATTERNS:
        match = re.search(pat, raw_section)
        if match and match.start() > 0:
            if match.start() < cutoff_pos:
                cutoff_pos = match.start()

    isolated_section = raw_section[:cutoff_pos].strip()
    return isolated_section, header_found

# =========================================================================
# INGREDIENT TOKEN CLEANING & FILTRATION
# =========================================================================
def clean_ingredient_token(raw_token: str) -> Optional[str]:
    """
    Cleans, normalizes and validates an ingredient candidate.
    Discards brands, categories, marketing slogans, nutrition remnants,
    manufacturer addresses, storage and usage instructions, medical disclaimers,
    and arbitrary OCR noise.
    Returns the cleaned ingredient name or None if rejected.
    """
    if not raw_token:
        return None

    token = raw_token.strip()

    # Strip leading bullet points, numbers, punctuation
    token = re.sub(r"^[\s\d\.\-\*\•\:\,\;\|\~\(\)]+", "", token).strip()
    # Strip trailing punctuation
    token = re.sub(r"[\s\.\,\;\:\-\*\|\~\(\)]+$", "", token).strip()

    # If starts with 'Contains added' or 'Nature identical', clean prefix
    token = re.sub(r"(?i)^contains\s+(?:added\s+)?", "", token).strip()

    lower = token.lower()

    # 1. Reject if too short or lacking alphabetical characters
    alphabetic_chars = re.findall(r"[a-zA-Z]", token)
    if len(alphabetic_chars) < 3:
        return None

    # 2. Reject pure numbers, dates, or percentages
    if re.match(r"^[\d\.\s\%\/\-]+$", token):
        return None

    # 3. Reject known brand names
    for brand in KNOWN_BRAND_NAMES:
        if lower == brand or lower.startswith(f"{brand} ") or lower.endswith(f" {brand}"):
            return None

    # 4. Reject product headings / categories
    for heading in PRODUCT_HEADINGS:
        if lower == heading or lower == f"rich {heading}" or lower == f"crispy {heading}":
            return None

    # 5. Reject marketing claims
    for claim in MARKETING_CLAIMS:
        if re.search(claim, token):
            return None

    # 6. Reject nutrition table remnants
    if re.search(r"(?i)\b(?:energy|calories|kcal|protein|carbohydrates?|total\s*sugars?|added\s*sugars?|total\s*fat|saturated\s*fat|trans\s*fat|cholesterol|sodium|dietary\s*fiber|typical\s*values?|per\s*100\s*(?:g|ml)|per\s*serving|approx\s*values?)\b", lower):
        return None

    # 7. Reject packaging, manufacturing, legal & regulatory keywords
    if re.search(r"(?i)\b(?:fssai|lic\.?\s*no|batch|lot|mfg|exp|expiry|net\s*wt|gross\s*wt|mrp|customer\s*care|consumer\s*cell|best\s*before|use\s*by|package|marketed|manufactured|packed|distributor|producer|importer|cin\s*no|trademark|registered\s*office|corp\s*office)\b", lower):
        return None

    # 8. Reject addresses, locations, industrial zones, PIN codes
    if re.search(r"(?i)\b(?:plot\s*(?:no\.?)?|sector|phase|nagar|road|street|marg|industrial\s*(?:area|estate)|taluk|taluka|district|building|village|pin\s*code|floor|complex|estate|highway)\b", lower) or re.search(r"\b\d{6}\b", lower):
        return None

    # 9. Reject storage & usage instructions
    if re.search(r"(?i)\b(?:store\s+in|cool\s+(?:and|&)\s+dry|keep\s+away|away\s+from|direct\s+sunlight|hygienic\s+place|refrigerate|room\s+temperature|do\s+not\s+freeze|shake\s+well|serving\s*suggestion|directions\s*for\s*use|how\s*to\s*use|preparation)\b", lower):
        return None

    # 10. Reject medical warnings and disclaimers
    if re.search(r"(?i)\b(?:not\s+for\s+medicinal|medicinal\s*use|dietary\s*supplement|consult\s+physician|consult\s+doctor|pregnant|lactating|keep\s+out\s+of\s+reach|children|swallow\s+whole|do\s+not\s+chew)\b", lower):
        return None

    # 11. Reject arbitrary company/unit words or gibberish fragments
    if re.match(r"^(?:approx|pvt|ltd|inc|co|corp|g|kg|ml|l|oz|nos|qty|wt|rs|inr|taxes|email|website|www)$", lower):
        return None

    # Standardize spaces
    token = re.sub(r"\s+", " ", token).strip()
    return token

# =========================================================================
# PARENTHESIS-AWARE TOKENIZER
# =========================================================================
def split_into_ingredients(section_text: str) -> List[str]:
    """
    Splits ingredient text by delimiters (comma, semicolon, bullet, newline)
    while strictly preserving nested parentheses:
    e.g. 'Wheat Flour (Maida) (58%), Edible Vegetable Oil (Palmolein, Antioxidant (INS 319)), Salt'
    -> ['Wheat Flour (Maida) (58%)', 'Edible Vegetable Oil (Palmolein, Antioxidant (INS 319))', 'Salt']
    """
    if not section_text:
        return []

    tokens: List[str] = []
    current_token: List[str] = []
    paren_depth = 0

    for char in section_text:
        if char == "(":
            paren_depth += 1
            current_token.append(char)
        elif char == ")":
            if paren_depth > 0:
                paren_depth -= 1
            current_token.append(char)
        elif char in [",", ";", "•", "\n", "|", "*", "\t"] and paren_depth == 0:
            token_str = "".join(current_token).strip()
            if token_str:
                tokens.append(token_str)
            current_token = []
        else:
            current_token.append(char)

    if current_token:
        token_str = "".join(current_token).strip()
        if token_str:
            tokens.append(token_str)

    # Clean and filter tokens
    valid_ingredients: List[str] = []
    seen: set = set()

    for raw in tokens:
        cleaned = clean_ingredient_token(raw)
        if cleaned:
            # Deduplicate case-insensitively while preserving original order
            key = cleaned.lower()
            if key not in seen:
                seen.add(key)
                valid_ingredients.append(cleaned)

    return valid_ingredients

# =========================================================================
# UNIVERSAL ANALYSIS PIPELINE ENTRY POINTS
# =========================================================================
def process_food_label(raw_text: str) -> Tuple[List[str], Dict[str, Any], str]:
    """
    Universal label processing for every food product:
    1. Extracts nutrition facts into structured dictionary.
    2. Excises nutrition block from text to prevent cross-contamination.
    3. Locates and isolates ingredient declaration boundaries.
    4. Tokenizes with nested parenthesis protection.
    5. Cleans and validates true ingredients (discarding brand names,
       headings, manufacturer details, addresses, storage/usage instructions,
       medical disclaimers, serving sizes, marketing phrases, and packaging noise).
    6. Verifies extraction reliability so unreadable or non-ingredient scans are rejected.
    
    Returns: (parsed_ingredients, nutrition_facts, cleaned_section_text)
    """
    cleaned_ocr = clean_raw_ocr(raw_text)
    nutrition_facts, text_no_nutrition = extract_nutrition_facts(cleaned_ocr)
    ingredient_section, header_found = extract_ingredient_section(text_no_nutrition)

    if not ingredient_section:
        return [], nutrition_facts, cleaned_ocr

    ingredients = split_into_ingredients(ingredient_section)

    # Extraction Quality & Reliability Check:
    # If no explicit header was found and extracted items are fewer than 2,
    # or total combined letters across ingredients is too sparse (< 8 chars),
    # reject as unreliable rather than assigning a false assessment.
    total_letters = sum(len(re.findall(r"[a-zA-Z]", ing)) for ing in ingredients)
    if not header_found and (len(ingredients) < 2 or total_letters < 8):
        return [], nutrition_facts, cleaned_ocr

    return ingredients, nutrition_facts, ingredient_section

def process_raw_label(raw_text: str, extract_nutrition: bool = False):
    """
    Backwards-compatible API wrapper:
    If extract_nutrition=True: returns (ingredients, nutrition_facts, section_text)
    If extract_nutrition=False (default): returns (ingredients, section_text)
    """
    ingredients, nutrition_facts, section_text = process_food_label(raw_text)
    if extract_nutrition:
        return ingredients, nutrition_facts, section_text
    return ingredients, section_text
