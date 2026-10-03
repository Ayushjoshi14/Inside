import re
from typing import Tuple, Optional, Dict

# INS / E-number lookup table
CODE_TO_INGREDIENT = {
    # Colours
    "100": "Curcumin",
    "101": "Riboflavin",
    "102": "Tartrazine",
    "110": "Sunset Yellow FCF",
    "120": "Carmine",
    "122": "Azorubine",
    "124": "Ponceau 4R",
    "127": "Erythrosine",
    "129": "Allura Red",
    "132": "Indigotine",
    "133": "Brilliant Blue FCF",
    "140": "Chlorophylls",
    "150a": "Caramel I (Plain)",
    "150b": "Caramel II (Caustic Sulphite)",
    "150c": "Caramel III (Ammonia)",
    "150d": "Caramel IV (Sulphite Ammonia)",
    "160a": "Beta-Carotene",
    "160b": "Annatto",
    "160c": "Paprika Extract",
    "162": "Beetroot Red",
    "171": "Titanium Dioxide",
    
    # Preservatives
    "200": "Sorbic Acid",
    "202": "Potassium Sorbate",
    "211": "Sodium Benzoate",
    "220": "Sulphur Dioxide",
    "223": "Sodium Metabisulphite",
    "224": "Potassium Metabisulphite",
    "234": "Nisin",
    "282": "Calcium Propionate",
    
    # Antioxidants
    "300": "Ascorbic Acid",
    "301": "Sodium Ascorbate",
    "307": "Tocopherols (Vitamin E)",
    "319": "TBHQ (Tert-Butylhydroquinone)",
    "320": "BHA (Butylated Hydroxyanisole)",
    "321": "BHT (Butylated Hydroxytoluene)",
    "322": "Lecithin",
    "322i": "Soy Lecithin",
    "330": "Citric Acid",
    "334": "Tartaric Acid",
    "338": "Phosphoric Acid",
    
    # Emulsifiers, Stabilizers & Thickeners
    "407": "Carrageenan",
    "412": "Guar Gum",
    "414": "Acacia Gum (Gum Arabic)",
    "415": "Xanthan Gum",
    "420": "Sorbitol",
    "422": "Glycerol",
    "428": "Gelatin",
    "440": "Pectin",
    "450": "Diphosphates",
    "452": "Polyphosphates",
    "471": "Mono- and Diglycerides of Fatty Acids",
    "472e": "DATEM",
    "476": "Polyglycerol Polyricinoleate (PGPR)",
    
    # Acidity Regulators & Raising Agents
    "500": "Sodium Carbonate",
    "500i": "Sodium Carbonate",
    "500ii": "Sodium Bicarbonate",
    "503": "Ammonium Carbonate",
    "503ii": "Ammonium Bicarbonate",
    "551": "Silicon Dioxide",
    
    # Flavour Enhancers
    "621": "Monosodium Glutamate",
    "627": "Disodium Guanylate",
    "631": "Disodium Inosinate",
    "635": "Disodium 5'-ribonucleotides",
    
    # Sweeteners
    "950": "Acesulfame Potassium",
    "951": "Aspartame",
    "955": "Sucralose",
    "960": "Steviol Glycosides",
    "965": "Maltitol",
    "968": "Erythritol",
}

# Common OCR typo substitutions
SPELLING_CORRECTIONS = {
    "citric acd": "citric acid",
    "citric acld": "citric acid",
    "artifical flavour": "artificial flavour",
    "artficial flavour": "artificial flavour",
    "artificial flvr": "artificial flavour",
    "artificial flavor": "artificial flavour",
    "palm ol": "palm oil",
    "pam oil": "palm oil",
    "palmolein": "palmolein oil",
    "whcat flour": "wheat flour",
    "weat flour": "wheat flour",
    "refned wheat flour": "refined wheat flour",
    "preservatve": "preservative",
    "preservatves": "preservatives",
    "monosodum glutamate": "monosodium glutamate",
    "ascorbc acid": "ascorbic acid",
    "soya lecithn": "soy lecithin",
    "soy lecithn": "soy lecithin",
    "lecitin": "lecithin",
    "cocoa solid": "cocoa solids",
    "milk solid": "milk solids",
    "hydrgenated": "hydrogenated",
}

def clean_token(token: str) -> str:
    """Removes percentage numbers like '(52%)', brackets with only numbers, etc."""
    cleaned = re.sub(r"\(\s*\d+(?:\.\d+)?\s*%\s*\)", "", token)
    cleaned = re.sub(r"\s+\d+(?:\.\d+)?\s*%", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def extract_ins_or_e_code(text: str) -> Optional[Tuple[str, str]]:
    """
    Finds INS or E codes in strings like:
    'Emulsifier (INS 322i)', 'INS 330', 'E102', 'Preservative (211)', 'Raising Agent 500(ii)'
    Returns (code_key, matched_canonical_name) or None
    """
    # INS pattern: e.g. INS 322, INS 500(ii), INS 500ii, INS-322i
    ins_match = re.search(r"\b(?:INS|E)\s*[-:]?\s*(\d{3,4}(?:\([a-z0-9]+\)|[a-z0-9]*))\b", text, re.IGNORECASE)
    if ins_match:
        raw_code = ins_match.group(1).lower().replace("(", "").replace(")", "").strip()
        # Look up directly or stripped
        for key in [raw_code, raw_code.rstrip("i").rstrip("a").rstrip("b").rstrip("c").rstrip("d")]:
            if key in CODE_TO_INGREDIENT:
                return (raw_code, CODE_TO_INGREDIENT[key])
                
    # Direct code like (322) or (500(ii)) within functional additive prefix
    additive_context = re.search(r"(?:antioxidant|preservative|emulsifier|stabilizer|acidity regulator|colour|color|raising agent|flavour enhancer|sweetener)\s*\(\s*([0-9]{3,4}(?:\([a-z0-9]+\)|[a-z0-9]*))\s*\)", text, re.IGNORECASE)
    if additive_context:
        raw_code = additive_context.group(1).lower().replace("(", "").replace(")", "").strip()
        for key in [raw_code, raw_code.rstrip("i").rstrip("a").rstrip("b").rstrip("c").rstrip("d")]:
            if key in CODE_TO_INGREDIENT:
                return (raw_code, CODE_TO_INGREDIENT[key])

    return None

def normalize_ingredient_name(raw_name: str) -> Tuple[str, str, str]:
    """
    Normalizes a single ingredient token.
    Returns:
    (display_name, normalized_name, confidence)
    where confidence is 'HIGH', 'MEDIUM', or 'LOW'
    """
    cleaned = clean_token(raw_name)
    if not cleaned:
        return ("", "", "LOW")

    lower = cleaned.lower()

    # Check for INS/E-number first
    code_match = extract_ins_or_e_code(cleaned)
    if code_match:
        code_str, canonical_name = code_match
        return (f"{canonical_name} (INS {code_str.upper()})", canonical_name, "HIGH")

    # Check spelling corrections
    for typo, correction in SPELLING_CORRECTIONS.items():
        if typo in lower:
            fixed = re.sub(re.escape(typo), correction, lower, flags=re.IGNORECASE)
            return (fixed.title(), fixed.title(), "MEDIUM")

    # If it has parenthetical sub-ingredients, e.g. "Vegetable Oil (Palm Oil)"
    paren_match = re.search(r"^(.*?)\s*\((.*?)\)$", cleaned)
    if paren_match:
        outer = paren_match.group(1).strip()
        inner = paren_match.group(2).strip()
        # If inner contains a known ingredient, use both
        return (f"{outer.title()} ({inner})", outer.title(), "HIGH")

    # Standard clean name
    normalized = cleaned.strip()
    return (normalized.title(), normalized.title(), "HIGH")
