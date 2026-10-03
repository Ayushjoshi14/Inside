import json
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
                temperature=0.2
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

        # Check explicit avoid list match
        if any(av in lower for av in avoid_set if av):
            status = "AVOID"
            reason = "Matches your personal list of ingredients to avoid."

        elif any(k in lower for k in ["hydrogenated", "trans fat", "partially hydrogenated"]):
            status = "AVOID"
            category = "Fat/oil"
            reason = "Industrial trans fat linked to cardiovascular disease risk."
        elif any(k in lower for k in ["artificial colour", "red 40", "yellow 5", "yellow 6", "blue 1", "caramel iv"]):
            status = "CAUTION"
            category = "Artificial colour"
            reason = "Synthetic colorant; some individuals and children may be sensitive."
        elif any(k in lower for k in ["syrup", "dextrose", "maltose", "fructose", "sucrose", "glucose", "corn syrup"]):
            status = "CAUTION"
            category = "Sugar"
            reason = "Caloric added sugar or refined sweetener."
        elif any(k in lower for k in ["gelatin", "lard", "tallow", "bone", "meat", "poultry", "rennet", "carmine"]):
            category = "Animal by-product"
            veg = "NO"
            vegan = "NO"
            if user_diet in ["VEGETARIAN", "VEGAN"]:
                status = "AVOID"
                reason = "Animal-derived ingredient not suitable for your dietary preference."
            else:
                status = "CAUTION"
                reason = "Animal-derived source; check dietary compatibility."
        elif any(k in lower for k in ["preservative", "benzoate", "sorbate", "metabisulphite", "propionate", "bha", "bht"]):
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
        elif any(k in lower for k in ["milk", "dairy", "whey", "casein", "butter", "cheese"]):
            category = "Dairy"
            vegan = "NO"
            reason = "Dairy ingredient; contains lactose and milk proteins."
            if user_diet == "VEGAN":
                status = "AVOID"
                reason = "Dairy ingredient not suitable for a vegan diet."
        else:
            reason = "Common whole or processed food component."

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
