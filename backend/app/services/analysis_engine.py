import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Ingredient, CachedIngredientAnalysis, UserProfile
from backend.app.services.normalization import normalize_ingredient_name
from backend.app.ai.gemini_service import analyze_unknown_ingredients_with_ai

logger = logging.getLogger(__name__)

def evaluate_personalized_status(
    base_status: str,
    base_reason: str,
    veg_status: str,
    vegan_status: str,
    allergen_info: Optional[str],
    ingredient_name: str,
    profile: Optional[UserProfile]
) -> Tuple[str, str]:
    """
    Applies user personalization rules:
    - Diet preference (VEGETARIAN, VEGAN)
    - Custom Avoid list
    - Allergens list
    """
    if not profile:
        return base_status, base_reason

    lower_name = ingredient_name.lower()
    final_status = base_status
    reason_notes = [base_reason] if base_reason else []

    # 1. Check custom avoid list
    for avoid_term in profile.avoid_list:
        if avoid_term and avoid_term.lower() in lower_name:
            final_status = "AVOID"
            reason_notes.insert(0, f"Matches your custom avoid list ('{avoid_term}')")
            break

    # 2. Check allergens
    for allergen in profile.allergens_list:
        if allergen and (allergen.lower() in lower_name or (allergen_info and allergen.lower() in allergen_info.lower())):
            final_status = "AVOID"
            reason_notes.insert(0, f"Contains allergen: {allergen}")
            break

    # 3. Check dietary preference
    diet = (profile.diet_preference or "NONE").upper()
    if diet == "VEGETARIAN":
        if veg_status == "NO":
            final_status = "AVOID"
            reason_notes.insert(0, "Non-vegetarian ingredient (derived from animal source)")
        elif veg_status == "MAYBE" and final_status != "AVOID":
            final_status = "CAUTION"
            reason_notes.insert(0, "Source may vary (may be plant or animal derived; check manufacturer)")
    elif diet == "VEGAN":
        if vegan_status == "NO" or veg_status == "NO":
            final_status = "AVOID"
            reason_notes.insert(0, "Non-vegan ingredient (animal or dairy origin)")
        elif (vegan_status == "MAYBE" or veg_status == "MAYBE") and final_status != "AVOID":
            final_status = "CAUTION"
            reason_notes.insert(0, "Source may vary (verify with manufacturer for vegan compliance)")

    # Combine unique reason notes cleanly
    unique_reasons = []
    for r in reason_notes:
        if r not in unique_reasons:
            unique_reasons.append(r)

    combined_reason = ". ".join(unique_reasons).strip()
    if not combined_reason.endswith("."):
        combined_reason += "."
    return final_status, combined_reason


def analyze_ingredients_list(
    db: Session,
    raw_ingredients: List[str],
    profile: Optional[UserProfile] = None
) -> Dict[str, Any]:
    """
    Core hybrid analysis pipeline:
    1. Normalize names & extract INS/E codes
    2. Check local structured DB
    3. Check local cache
    4. Call AI only for remaining unknown items
    5. Cache new AI evaluations
    6. Apply user personalization
    7. Compute score, status, warnings, and summary
    """
    parsed_items = []
    unknown_for_ai = []

    # Step 1-3: Normalize and check local DB / Cache
    for raw_item in raw_ingredients:
        display_name, normalized_name, conf = normalize_ingredient_name(raw_item)
        if not normalized_name:
            continue

        # Look in structured DB
        db_match = db.query(Ingredient).filter(
            (Ingredient.normalized_name.ilike(normalized_name)) |
            (Ingredient.name.ilike(normalized_name)) |
            (Ingredient.aliases.ilike(f"%{normalized_name}%"))
        ).first()

        if db_match:
            parsed_items.append({
                "name": display_name,
                "normalized_name": db_match.normalized_name,
                "status": db_match.caution_level,
                "reason": db_match.explanation or db_match.description or "Standard food additive.",
                "category": db_match.category,
                "vegetarian_status": db_match.vegetarian_status,
                "vegan_status": db_match.vegan_status,
                "allergen_info": db_match.allergen_info,
                "source": "local_db"
            })
            continue

        # Look in Cache
        cached_match = db.query(CachedIngredientAnalysis).filter(
            CachedIngredientAnalysis.normalized_name.ilike(normalized_name)
        ).first()

        if cached_match:
            parsed_items.append({
                "name": display_name,
                "normalized_name": cached_match.normalized_name,
                "status": cached_match.status,
                "reason": cached_match.reason,
                "category": cached_match.category,
                "vegetarian_status": "YES",
                "vegan_status": "YES",
                "allergen_info": None,
                "source": "cache"
            })
            continue

        # Item is genuinely unknown locally: queue for AI
        unknown_for_ai.append({
            "raw_item": raw_item,
            "display_name": display_name,
            "normalized_name": normalized_name
        })

    # Step 4: Call AI only for unknown items
    if unknown_for_ai:
        names_to_query = [u["normalized_name"] for u in unknown_for_ai]
        diet = profile.diet_preference if profile else "NONE"
        avoids = profile.avoid_list if profile else []
        
        ai_response = analyze_unknown_ingredients_with_ai(names_to_query, diet, avoids)
        ai_map = {item.get("name", "").lower(): item for item in ai_response.get("ingredients", [])}

        for u in unknown_for_ai:
            norm_key = u["normalized_name"].lower()
            ai_item = ai_map.get(norm_key, {})

            status = ai_item.get("status", "GOOD")
            if status not in ["GOOD", "CAUTION", "AVOID"]:
                status = "GOOD"
                
            reason = ai_item.get("reason", "Common dietary component.")
            category = ai_item.get("category", "General")
            veg_status = ai_item.get("vegetarian_status", "YES")
            vegan_status = ai_item.get("vegan_status", "YES")

            # Cache the result for future users to save AI cost
            try:
                new_cache = CachedIngredientAnalysis(
                    normalized_name=u["normalized_name"],
                    status=status,
                    reason=reason,
                    category=category
                )
                db.add(new_cache)
                db.commit()
            except Exception as e:
                db.rollback()

            parsed_items.append({
                "name": u["display_name"],
                "normalized_name": u["normalized_name"],
                "status": status,
                "reason": reason,
                "category": category,
                "vegetarian_status": veg_status,
                "vegan_status": vegan_status,
                "allergen_info": None,
                "source": "ai"
            })

    # Step 5: Apply personalization to every item
    final_ingredients = []
    avoid_count = 0
    caution_count = 0
    good_count = 0

    warnings = []
    has_preservatives = False
    has_artificial_colours = False
    has_high_sugar = False
    has_trans_fats = False
    has_allergens = False

    for item in parsed_items:
        p_status, p_reason = evaluate_personalized_status(
            base_status=item["status"],
            base_reason=item["reason"],
            veg_status=item["vegetarian_status"],
            vegan_status=item["vegan_status"],
            allergen_info=item["allergen_info"],
            ingredient_name=item["normalized_name"],
            profile=profile
        )

        item["status"] = p_status
        item["reason"] = p_reason
        final_ingredients.append(item)

        if p_status == "AVOID":
            avoid_count += 1
        elif p_status == "CAUTION":
            caution_count += 1
        else:
            good_count += 1

        cat = (item["category"] or "").lower()
        if "preservative" in cat:
            has_preservatives = True
        if "colour" in cat or "color" in cat:
            has_artificial_colours = True
        if "sugar" in cat or "sweetener" in cat:
            has_high_sugar = True
        if "trans fat" in item["reason"].lower():
            has_trans_fats = True
        if item["allergen_info"]:
            has_allergens = True

    # Step 6: Compute overall score (0-100) and overall status
    # Base: 100 points
    score = 100 - (avoid_count * 28) - (caution_count * 10)
    score = max(10, min(100, score))

    if avoid_count > 0:
        overall_status = "AVOID"
    elif caution_count >= 2 or score < 75:
        overall_status = "CAUTION"
    else:
        overall_status = "GOOD"

    # Step 7: Construct Key Highlights & Warnings
    if avoid_count == 0 and caution_count == 0:
        warnings.append("✓ Clean formulation with no major additives of concern")
    else:
        if has_trans_fats:
            warnings.append("⚠ Contains hydrogenated trans-fats")
        if has_artificial_colours:
            warnings.append("⚠ Contains synthetic food colours")
        if has_preservatives:
            warnings.append("⚠ Contains artificial preservatives")
        if has_high_sugar:
            warnings.append("⚠ Contains added sugars or refined sweeteners")
        if has_allergens:
            warnings.append("⚠ Contains potential allergens")

    # Step 8: Concise consumer summary
    if overall_status == "GOOD":
        summary = "Safe and clean ingredient profile with no critical additives detected."
    elif overall_status == "CAUTION":
        summary = f"Contains {caution_count} ingredient(s) worth checking before regular consumption."
    else:
        summary = f"Contains {avoid_count} ingredient(s) recommended to avoid based on health impact or your dietary preferences."

    recommendations = [
        "Store in a cool, dry place.",
        "Check manufacturer label for latest formulation updates."
    ]

    return {
        "overall_status": overall_status,
        "score": score,
        "summary": summary,
        "ingredients": final_ingredients,
        "warnings": warnings,
        "recommendations": recommendations
    }
