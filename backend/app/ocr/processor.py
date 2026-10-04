import re
from typing import List, Tuple

PACKAGING_NOISE_PATTERNS = [
    r"(?i)mfg\.?\s*(?:date|dt)?[:\s\d\/\.\-]+",
    r"(?i)exp\.?\s*(?:date|dt)?[:\s\d\/\.\-]+",
    r"(?i)best\s+before[\w\s\:\.\-\d]+",
    r"(?i)use\s+by[\w\s\:\.\-\d]+",
    r"(?i)batch\s*(?:no|num)?[:\s\w\d\-]+",
    r"(?i)lot\s*(?:no|num)?[:\s\w\d\-]+",
    r"(?i)net\s*wt\.?[:\s\d\.\w]+",
    r"(?i)net\s*weight[:\s\d\.\w]+",
    r"(?i)net\s*qty[:\s\d\.\w]+",
    r"(?i)m\.?r\.?p\.?[\s\:\₹\$\d\.\-]+",
    r"(?i)incl\.?\s*of\s*all\s*taxes",
    r"(?i)fssai[\s\:\d\-]+",
    r"(?i)lic\.?\s*(?:no)?[\s\:\d\-]+",
    r"(?i)marketed\s*by[\w\s\.\,\-]+",
    r"(?i)manufactured\s*by[\w\s\.\,\-]+",
    r"(?i)store\s+in\s+a\s+cool[\w\s\,\.]+",
    r"(?i)customer\s*care[\w\s\:\.\-\d\@]+",
    r"(?i)for\s*feedback[\w\s\:\.\-\d\@]+",
    r"(?i)barcode[\s\:\d]+",
    r"(?i)nutrition(?:al)?\s*information[\w\s\:\.\,\-\%\d]+",
    r"(?i)per\s*100\s*g[\w\s\:\.\,\-\%\d]+",
]

INGREDIENT_SECTION_HEADERS = [
    r"(?i)(?:ingredients|ingredients\s*used|ingredients\s*list|composition)\s*[:\-\s]",
    r"(?i)contents\s*[:\-\s]",
]

def clean_raw_ocr(raw_text: str) -> str:
    """Removes non-ascii garbage, normalizes spaces and linebreaks."""
    if not raw_text:
        return ""
    # Standardize quotes and brackets
    cleaned = raw_text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    cleaned = cleaned.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    # Remove obvious non-printable noise while keeping standard punctuation
    cleaned = re.sub(r"[^\x20-\x7E\n\r]", " ", cleaned)
    cleaned = re.sub(r"\r\n", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()

def extract_ingredient_section(text: str) -> Tuple[str, str]:
    """
    Extracts the ingredient list substring from label OCR,
    discarding preceding or trailing packaging boilerplate.
    Returns (ingredient_section_text, extracted_header_or_empty).
    """
    cleaned = clean_raw_ocr(text)
    
    # Try finding an explicit 'INGREDIENTS:' marker
    start_pos = 0
    header_found = ""
    for pattern in INGREDIENT_SECTION_HEADERS:
        match = re.search(pattern, cleaned)
        if match:
            start_pos = match.end()
            header_found = match.group(0).strip()
            break
            
    extracted = cleaned[start_pos:]
    
    # Trim at allergen/warning or manufacture boundary if present
    cutoff_markers = [
        r"(?i)\n\s*(?:allergen\s+advice|allergen\s+declaration|contains|may\s+contain)\s*:",
        r"(?i)\n\s*(?:manufactured|marketed|mfd|pkd|mfg|storage|fssai|nutrition)",
    ]
    
    # Also strip common packaging noise patterns
    for pat in PACKAGING_NOISE_PATTERNS:
        extracted = re.sub(pat, " ", extracted)

    # Clean whitespace
    extracted = re.sub(r"\s+", " ", extracted).strip()
    return extracted, header_found

def split_into_ingredients(section_text: str) -> List[str]:
    """
    Splits ingredient text cleanly by commas, semicolons, and bullets,
    taking care not to break inside nested parentheses:
    e.g., 'Flour, Edible Vegetable Oil (Palm Oil, Antioxidant (INS 319)), Salt'
    -> ['Flour', 'Edible Vegetable Oil (Palm Oil, Antioxidant (INS 319))', 'Salt']
    """
    if not section_text:
        return []
    
    # Split with nested parenthesis balancing
    tokens = []
    current_token = []
    paren_depth = 0
    
    for char in section_text:
        if char == "(":
            paren_depth += 1
            current_token.append(char)
        elif char == ")":
            if paren_depth > 0:
                paren_depth -= 1
            current_token.append(char)
        elif char in [",", ";", "•", "\n", "|"] and paren_depth == 0:
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
    results = []
    for t in tokens:
        # Strip trailing dots or dashes
        t_cleaned = re.sub(r"^[\s\-\*\.\:]+|[\s\-\*\.\:]+$", "", t).strip()
        # If ends with period like "Salt." remove it
        if t_cleaned.endswith("."):
            t_cleaned = t_cleaned[:-1].strip()
        # Ignore empty, pure symbols, or ultra-short junk
        if len(t_cleaned) > 1 and not re.match(r"^[\d\.\s\%]+$", t_cleaned) and re.search(r"[a-zA-Z]", t_cleaned):
            results.append(t_cleaned)
            
    return results

def process_raw_label(raw_text: str) -> Tuple[List[str], str]:
    """
    Full OCR processing pipeline:
    Returns (list_of_parsed_ingredients, cleaned_section_text)
    """
    section_text, _ = extract_ingredient_section(raw_text)
    if not section_text:
        section_text = clean_raw_ocr(raw_text)
    ingredients = split_into_ingredients(section_text)
    return ingredients, section_text
