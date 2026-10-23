import json
import re
import logging
from typing import List, Dict, Any, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an objective food science expert assisting the 'Inside' ingredient scanner app.
Your task is to analyze unknown or complex food ingredients and classify them into exactly three statuses:
1. 'GOOD': Safe, natural, wholesome, or harmless standard food ingredients.
2. 'CAUTION': Contains added sugars, high saturated fats, potential irritants, artificial sweeteners, or ingredients whose source may vary (e.g. animal vs vegetable mono-diglycerides).
3. 'AVOID': Trans fats, banned/restricted artificial dyes, harmful preservatives (BHA, excessive nitrites), or proven endocrine disruptors.

Output ONLY valid, parseable JSON conforming to this schema without markdown code blocks:
{
  "ingredients": [
    {
      "name": "Ingredient Name",
      "status": "GOOD" | "CAUTION" | "AVOID",
      "category": "Preservative" | "Sweetener" | "Emulsifier" | "Fat/oil" | "Sugar" | "Allergen" | "Flavour" | "Colour" | "General",
      "reason": "Clear 1-sentence consumer-friendly explanation",
      "vegetarian_status": "YES" | "NO" | "MAYBE",
      "vegan_status": "YES" | "NO" | "MAYBE"
    }
  ],
  "summary_insight": "A brief 1-2 sentence overall note on these ingredients."
}
"""

def analyze_unknown_ingredients_with_ai(
    unknown_ingredients: List[str],
    user_diet_preference: str = "NONE",
    user_avoid_list: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Sends only unknown/ambiguous ingredients to Gemini AI to minimize API calls and latency.
    """
    if not unknown_ingredients:
        return {"ingredients": [], "summary_insight": ""}

    if not settings.GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not set. Using local food science heuristic engine.")
        return fallback_heuristic_analyzer(unknown_ingredients, user_diet_preference, user_avoid_list)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        user_prompt = f"""Analyze the following list of food ingredients:
{json.dumps(unknown_ingredients, indent=2)}

User diet preference: {user_diet_preference}
User avoid list: {json.dumps(user_avoid_list or [])}

Respond with strictly valid JSON."""

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[user_prompt],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.0  # Zero temperature for deterministic evaluations
            )
        )

        response_text = response.text.strip()
        # Clean any accidental markdown code fences
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        parsed = json.loads(response_text.strip())
        return parsed
    except Exception as e:
        logger.error(f"Error calling Gemini AI: {e}. Falling back to local heuristic analyzer.")
        return fallback_heuristic_analyzer(unknown_ingredients, user_diet_preference, user_avoid_list)


def fallback_heuristic_analyzer(
    ingredients: List[str],
    user_diet: str = "NONE",
    avoid_list: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Robust local food science heuristic rule engine.
    Used when offline, in development without API key, or as high-availability fallback.
    """
    results = []
    avoid_set = {a.lower().strip() for a in (avoid_list or [])}

    for item in ingredients:
        lower = item.lower().strip()
        status = "GOOD"
        category = "General"
        reason = "Standard dietary ingredient."
        veg = "YES"
        vegan = "YES"

        # Check explicit user avoid list match
        if any(av in lower for av in avoid_set if av):
            status = "AVOID"
            reason = "Matches your personal list of ingredients to avoid."

        elif any(k in lower for k in ["partially hydrogenated", "trans fat"]):
            status = "AVOID"
            category = "Fat/oil"
            reason = "Industrial trans fat linked to cardiovascular disease risk."
        elif re.search(r"\b(?:hydrogenated(?:\s+\w+)?\s+oil|hydrogenated\s+fat)\b", lower):
            status = "AVOID"
            category = "Fat/oil"
            reason = "Hydrogenated fat; may contain trans or high saturated fatty acids."
        elif any(k in lower for k in ["artificial colour", "red 40", "yellow 5", "yellow 6", "blue 1", "caramel iv", "caramel iii"]):
            status = "CAUTION"
            category = "Artificial colour"
            reason = "Synthetic colorant; some individuals and children may be sensitive."
        elif any(k in lower for k in ["syrup", "dextrose", "maltose", "fructose", "sucrose", "glucose", "corn syrup", "cane sugar"]):
            status = "CAUTION"
            category = "Sugar"
            reason = "Caloric added sugar or refined sweetener."
        # Animal by-products check: Avoid false positives like "coconut meat", "soy meat", "sweetmeat", "jackfruit meat"
        elif any(k in lower for k in ["gelatin", "lard", "tallow", "poultry", "rennet", "carmine"]) or \
             (re.search(r"\bmeat\b", lower) and not any(p in lower for p in ["coconut", "soy", "sweet", "plant", "mock", "veggie", "jackfruit"])) or \
             (re.search(r"\bbone\b", lower) and not any(p in lower for p in ["bone-in", "wishbone"])):
            category = "Animal by-product"
            veg = "NO"
            vegan = "NO"
            if user_diet in ["VEGETARIAN", "VEGAN"]:
                status = "AVOID"
                reason = "Animal-derived ingredient not suitable for your dietary preference."
            else:
                status = "CAUTION"
                reason = "Animal-derived source; check dietary compatibility."
        # Preservatives: require word boundary for short abbreviations like BHA, BHT, TBHQ to avoid matching "sambhar", "bhaji", "bhujia"
        elif any(k in lower for k in ["preservative", "benzoate", "sorbate", "metabisulphite", "propionate"]) or \
             bool(re.search(r"\b(?:bha|bht|tbhq)\b", lower)):
            status = "CAUTION"
            category = "Preservative"
            reason = "Food preservative added to prolong commercial shelf-life."
        elif any(k in lower for k in ["aspartame", "sucralose", "acesulfame", "saccharin", "neotame"]):
            status = "CAUTION"
            category = "Sweetener"
            reason = "Intense artificial low-calorie sweetener."
        elif any(k in lower for k in ["wheat", "gluten", "barley", "rye"]):
            category = "Flour"
            reason = "Cereal grain containing gluten."
        elif any(k in lower for k in ["soy", "soya"]):
            category = "Legume"
            reason = "Soy-derived ingredient; allergen for sensitive persons."
        # Dairy check: strictly distinguish dairy milk/butter from plant butters (cocoa butter, peanut butter) and plant milks (coconut milk, soy milk, almond milk, oat milk)
        elif (any(k in lower for k in ["dairy", "whey", "casein", "cheese", "ghee", "lactose", "buttermilk"]) or
              (re.search(r"\bmilk\b", lower) and not any(p in lower for p in ["coconut", "soy", "almond", "oat", "rice", "hemp", "cashew", "plant", "pea"])) or
              (re.search(r"\bbutter\b", lower) and not any(p in lower for p in ["cocoa", "peanut", "almond", "shea", "apple", "nut", "seed", "plant", "cookie"]))):
            category = "Dairy"
            vegan = "NO"
            reason = "Dairy ingredient; contains lactose and milk proteins."
            if user_diet == "VEGAN":
                status = "AVOID"
                reason = "Dairy ingredient not suitable for a vegan diet."
        elif any(re.search(p, lower) for p in [
            r"\bwater\b", r"\baqua\b", r"\bsalt\b", r"\biodised\s+salt\b", r"\brock\s+salt\b", r"\bsea\s+salt\b",
            r"\bwheat\b", r"\brice\b", r"\boats?\b", r"\bcorn\b", r"\bmaize\b", r"\bbarley\b", r"\bmillets?\b",
            r"\bragi\b", r"\bjowar\b", r"\bbajra\b", r"\bflour\b", r"\batta\b", r"\bmaida\b", r"\bsuji\b", r"\brava\b",
            r"\bsemolina\b", r"\bbesan\b", r"\blentils?\b", r"\bdal\b", r"\bchana\b", r"\burad\b", r"\bmoong\b",
            r"\bpeas?\b", r"\bbeans?\b", r"\bchickpeas?\b", r"\bsoybeans?\b",
            r"\bturmeric\b", r"\bchili\b", r"\bchilli\b", r"\bpepper\b", r"\bcumin\b", r"\bcoriander\b",
            r"\bginger\b", r"\bgarlic\b", r"\bcinnamon\b", r"\bcardamom\b", r"\bclove\b", r"\bnutmeg\b",
            r"\bmustard\b", r"\bfenugreek\b", r"\bfennel\b", r"\boregano\b", r"\bbasil\b", r"\bthyme\b",
            r"\brosemary\b", r"\bpudina\b", r"\bmint\b", r"\bspices?\b", r"\bmasala\b", r"\bseasoning\b",
            r"\bbhujia\b", r"\bpotato(?:es)?\b", r"\bonions?\b", r"\btomato(?:es)?\b", r"\bcarrots?\b",
            r"\bbeetroot\b", r"\bspinach\b", r"\blemon\b", r"\blime\b", r"\bmango\b", r"\bapple\b",
            r"\bbanana\b", r"\borange\b", r"\bgrapes?\b", r"\bcoconut\b", r"\balmonds?\b", r"\bcashews?\b",
            r"\bwalnuts?\b", r"\bpistachio\b", r"\bpeanuts?\b", r"\bsesame\b", r"\bsunflower\s+seeds?\b",
            r"\bpumpkin\s+seeds?\b", r"\bchia\s+seeds?\b", r"\bflaxseeds?\b", r"\bdates?\b", r"\braisins?\b",
            r"\bvegetable\s+oil\b", r"\bolive\s+oil\b", r"\bsunflower\s+oil\b", r"\bmustard\s+oil\b",
            r"\bcoconut\s+oil\b", r"\bgroundnut\s+oil\b", r"\bsoybean\s+oil\b", r"\bcanola\s+oil\b",
            r"\bcocoa\b", r"\bcacao\b", r"\bcoffee\b", r"\btea\b", r"\byeast\b", r"\bvinegar\b",
            r"\bbaking\s+powder\b", r"\bbaking\s+soda\b", r"\bsodium\s+bicarbonate\b", r"\bcitric\s+acid\b",
            r"\bpectin\b", r"\bstarch\b", r"\btapioca\b"
        ]):
            status = "GOOD"
            category = "Whole food / Staple"
            reason = "Common whole food or standard dietary staple."
        else:
            # Unverified ingredient not recognized as standard food component or staple
            status = "CAUTION"
            category = "Unverified"
            reason = "Unverified ingredient not found in reference database; verify on product packaging."
            veg = "MAYBE"
            vegan = "MAYBE"

        results.append({
            "name": item,
            "status": status,
            "category": category,
            "reason": reason,
            "vegetarian_status": veg,
            "vegan_status": vegan
        })

    return {
        "ingredients": results,
        "summary_insight": "Evaluated through Inside's food safety analysis database."
    }
