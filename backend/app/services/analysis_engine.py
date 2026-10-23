import json
import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import Ingredient, CachedIngredientAnalysis, UserProfile
from backend.app.services.normalization import normalize_ingredient_name
from backend.app.services.product_detector import resolve_product_name_and_category
from backend.app.ai.gemini_service import analyze_unknown_ingredients_with_ai, fallback_heuristic_analyzer

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
        if avoid_term:
            term_clean = avoid_term.strip().lower()
            if re.search(rf"\b{re.escape(term_clean)}\b", lower_name) or term_clean in lower_name:
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
    profile: Optional[UserProfile] = None,
    provided_product_name: Optional[str] = None,
    provided_product_category: Optional[str] = None,
    raw_ocr_text: Optional[str] = None,
    nutrition_facts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Core hybrid analysis pipeline:
    1. Normalize names & extract INS/E codes
    2. Check local structured DB
    3. Check local cache
    4. Call AI only for remaining unknown items
    5. Cache new AI evaluations atomically via nested savepoint
    6. Apply user personalization
    7. Compute transparent score with breakdown & nutrition normalization
    8. Build positive findings, warnings, and smart summary
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
        
        # Build maps with non-empty keys
        ai_map = {
            item.get("name", "").strip().lower(): item 
            for item in ai_response.get("ingredients", [])
            if item.get("name", "").strip()
        }
        ai_norm_map = {
            re.sub(r"[^a-z0-9]", "", item.get("name", "").lower()): item
            for item in ai_response.get("ingredients", [])
            if item.get("name", "").strip()
        }

        for u in unknown_for_ai:
            norm_key = u["normalized_name"].strip().lower()
            disp_key = u["display_name"].strip().lower()
            clean_norm_key = re.sub(r"[^a-z0-9]", "", norm_key)
            clean_disp_key = re.sub(r"[^a-z0-9]", "", disp_key)

            ai_item = ai_map.get(norm_key) or ai_map.get(disp_key)
            if not ai_item and clean_norm_key:
                ai_item = ai_norm_map.get(clean_norm_key)
            if not ai_item and clean_disp_key:
                ai_item = ai_norm_map.get(clean_disp_key)

            # Substring fallback with minimum token length guard to avoid accidental short matches
            if not ai_item:
                for k, v in ai_map.items():
                    if len(k) >= 4 and len(norm_key) >= 4:
                        if k in norm_key or norm_key in k:
                            ai_item = v
                            break

            # If AI omitted this ingredient, fallback directly to local heuristic analysis
            if not ai_item:
                fallback_res = fallback_heuristic_analyzer([u["normalized_name"]], diet, avoids)
                if fallback_res.get("ingredients"):
                    ai_item = fallback_res["ingredients"][0]
                else:
                    ai_item = {}

            category = ai_item.get("category", "General")
            status = ai_item.get("status", "GOOD")
            if category == "Unverified":
                status = "CAUTION"
            elif status not in ["GOOD", "CAUTION", "AVOID"]:
                status = "GOOD"

            reason = ai_item.get("reason", "Common dietary component.")
            veg_status = ai_item.get("vegetarian_status", "YES")
            vegan_status = ai_item.get("vegan_status", "YES")

            # Cache using a nested transaction savepoint so the caller's outer transaction
            # and row locks on User remain intact and uncommitted.
            if ai_item:
                try:
                    with db.begin_nested():
                        new_cache = CachedIngredientAnalysis(
                            normalized_name=u["normalized_name"],
                            status=status,
                            reason=reason,
                            category=category
                        )
                        db.add(new_cache)
                except Exception:
                    pass

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
        # Pass composite display + normalized name to verify parenthetical ingredients (e.g. "Vegetable Oil (Palm Oil)")
        full_ingredient_name = f"{item['name']} {item['normalized_name']}"
        p_status, p_reason = evaluate_personalized_status(
            base_status=item["status"],
            base_reason=item["reason"],
            veg_status=item["vegetarian_status"],
            vegan_status=item["vegan_status"],
            allergen_info=item["allergen_info"],
            ingredient_name=full_ingredient_name,
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
        name_lower = (item["name"] or "").lower()
        reason_lower = (item["reason"] or "").lower()

        if "preservative" in cat:
            has_preservatives = True

        # Accurately distinguish synthetic food dyes from natural pigments (e.g. Curcumin, Beetroot Red)
        is_natural_pigment = any(np in name_lower or np in reason_lower for np in [
            "natural colour", "natural color", "curcumin", "beetroot red", "paprika",
            "beta-carotene", "chlorophyll", "anthocyanin", "annatto", "caramel i", "caramel ii",
            "natural pigment", "plant extract", "turmeric"
        ])
        is_synthetic_dye = (
            not is_natural_pigment and
            ("colour" in cat or "color" in cat) and
            any(k in name_lower or k in reason_lower for k in [
                "synthetic", "artificial", "tartrazine", "sunset yellow", "allura red",
                "brilliant blue", "ponceau", "azorubine", "erythrosine", "indigotine",
                "fast green", "caramel iv", "caramel iii", "titanium dioxide", "food dye"
            ])
        )
        if is_synthetic_dye:
            has_artificial_colours = True

        # Caloric added sugars vs natural non-caloric sweeteners (e.g. Stevia, Monk Fruit)
        is_caloric_sugar = (
            ("sugar" in cat or "sweetener" in cat) and
            not any(k in name_lower for k in ["stevia", "steviol", "monk fruit", "erythritol"])
        )
        if is_caloric_sugar:
            has_high_sugar = True

        if "trans fat" in reason_lower:
            has_trans_fats = True
        if item["allergen_info"]:
            has_allergens = True

    # -------------------------------------------------------------------------
    # Step 6: Transparent score computation (0–100) with nutrition normalization
    # -------------------------------------------------------------------------
    score_deductions: List[Dict[str, Any]] = []
    score_bonuses: List[Dict[str, Any]] = []
    nutrition_deduction = 0
    nf = nutrition_facts or {}

    ingredient_deduction = (avoid_count * 25) + (caution_count * 8)
    if avoid_count > 0:
        score_deductions.append({
            "label": f"{avoid_count} ingredient(s) to avoid",
            "points": -(avoid_count * 25)
        })
    if caution_count > 0:
        score_deductions.append({
            "label": f"{caution_count} ingredient(s) requiring caution",
            "points": -(caution_count * 8)
        })

    # Nutrition-driven deductions with per-serving & beverage normalization
    unit_label = "per 100g"
    raw_sugar = 0.0
    normalized_sugar = 0.0
    sugar_threshold = 15.0
    raw_sodium = 0.0
    normalized_sodium = 0.0

    if nf:
        per_unit_raw = str(nf.get("per_unit") or "").lower()
        serving_size_str = str(nf.get("serving_size") or "").lower()

        is_per_serving = "serving" in per_unit_raw or "pack" in per_unit_raw or "portion" in per_unit_raw
        is_per_100ml = "100 ml" in per_unit_raw or "100ml" in per_unit_raw or "liquid" in per_unit_raw

        category_lower = (provided_product_category or "").lower()
        is_beverage = is_per_100ml or any(b in category_lower for b in ["soft drink", "beverage", "juice", "drink", "tea", "coffee"])

        scale_to_100 = 1.0
        if is_per_serving and serving_size_str:
            match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:g|ml)?", serving_size_str)
            if match:
                try:
                    serving_weight = float(match.group(1))
                    if serving_weight > 0:
                        scale_to_100 = 100.0 / serving_weight
                except (ValueError, ZeroDivisionError):
                    scale_to_100 = 1.0

        if is_per_100ml or is_beverage:
            unit_label = "per 100ml"
        elif is_per_serving:
            unit_label = "per serving"
        else:
            unit_label = "per 100g"

        trans_fat = nf.get("trans_fat_g") or 0
        if trans_fat > 0:
            nutrition_deduction += 10
            score_deductions.append({"label": f"Trans fat detected ({trans_fat}g {unit_label})", "points": -10})

        raw_sugar = nf.get("added_sugars_g") or nf.get("total_sugars_g") or 0
        normalized_sugar = raw_sugar * scale_to_100 if is_per_serving else raw_sugar
        sugar_threshold = 6.0 if is_beverage else 15.0
        if normalized_sugar >= sugar_threshold and raw_sugar > 0:
            nutrition_deduction += 5
            score_deductions.append({
                "label": f"High added sugar ({raw_sugar}g {unit_label})",
                "points": -5
            })

        raw_sodium = nf.get("sodium_mg") or 0
        normalized_sodium = raw_sodium * scale_to_100 if is_per_serving else raw_sodium
        if normalized_sodium >= 600 and raw_sodium > 0:
            nutrition_deduction += 5
            score_deductions.append({
                "label": f"High sodium ({raw_sodium}mg {unit_label})",
                "points": -5
            })

        raw_sat_fat = nf.get("saturated_fat_g") or 0
        normalized_sat_fat = raw_sat_fat * scale_to_100 if is_per_serving else raw_sat_fat
        if normalized_sat_fat >= 10 and raw_sat_fat > 0:
            nutrition_deduction += 3
            score_deductions.append({
                "label": f"High saturated fat ({raw_sat_fat}g {unit_label})",
                "points": -3
            })

    # Assessment type: distinguish full nutritional + ingredient from ingredient-only assessment
    has_substantive_nutrition = bool(
        nf and any(
            nf.get(k) is not None and float(nf.get(k) or 0) > 0
            for k in ["energy_kcal", "total_fat_g", "carbohydrates_g", "total_sugars_g", "protein_g", "sodium_mg"]
        )
    )
    if has_substantive_nutrition:
        assessment_type = "FULL_NUTRITIONAL_AND_INGREDIENT"
        assessment_label = "Verified Ingredients & Nutrition Facts"
    else:
        assessment_type = "INGREDIENT_ONLY"
        assessment_label = "Ingredient-Based Assessment"

    raw_score = 100 - ingredient_deduction - nutrition_deduction

    has_unverified = any(item.get("category") == "Unverified" for item in final_ingredients)
    is_sparse = len(final_ingredients) < 3

    # Clean-label bonus: Only awarded for complete formulations (>= 3 ingredients) with zero concerns and zero unverified items
    if avoid_count == 0 and caution_count == 0 and nutrition_deduction == 0 and not is_sparse and not has_unverified:
        raw_score += 5
        score_bonuses.append({
            "label": "Clean label — no major concerns detected",
            "points": 5
        })

    score = max(5, min(100, raw_score))

    # Reliability Cap: If scan is sparse (< 3 ingredients) or contains unverified items, cap score at 85
    if (is_sparse or has_unverified) and score > 85:
        score = 85

    # Overall status thresholds
    if avoid_count > 0:
        overall_status = "AVOID"
    elif caution_count >= 2 or score < 70:
        overall_status = "CAUTION"
    else:
        overall_status = "GOOD"

    # -------------------------------------------------------------------------
    # Step 7: Positive findings — notable GOOD ingredients worth highlighting
    # -------------------------------------------------------------------------
    positive_findings: List[str] = []
    BENEFICIAL_KEYWORDS = [
        "oat", "whole wheat", "whole grain", "flaxseed", "chia", "almond", "walnut",
        "turmeric", "curcumin", "ginger", "cinnamon", "green tea", "honey", "olive oil", "sunflower",
        "vitamin", "calcium", "iron", "zinc", "magnesium", "protein", "fibre", "fiber",
        "quinoa", "millet", "amaranth", "probiotic", "prebiotic", "antioxidant",
        "beetroot", "beta-carotene"
    ]
    for item in final_ingredients:
        if item["status"] == "GOOD":
            name_lower = item["name"].lower()
            if any(k in name_lower for k in BENEFICIAL_KEYWORDS):
                positive_findings.append(f"{item['name']}: {item['reason']}")
    positive_findings = positive_findings[:4]

    # -------------------------------------------------------------------------
    # Step 8: Key findings / warnings
    # -------------------------------------------------------------------------
    trans_in_nf = nf.get("trans_fat_g", 0) or 0
    if avoid_count == 0 and caution_count == 0 and trans_in_nf == 0:
        warnings.append("✓ Clean formulation with no major additives of concern")
    else:
        if has_trans_fats or trans_in_nf > 0:
            warnings.append("⚠ Contains hydrogenated trans-fats — linked to cardiovascular risk")
        if has_artificial_colours:
            warnings.append("⚠ Contains synthetic food colours")
        if has_preservatives:
            warnings.append("⚠ Contains artificial preservatives")
        if has_high_sugar:
            warnings.append("⚠ Contains added sugars or refined sweeteners")
        if has_allergens:
            warnings.append("⚠ Contains potential allergens — check label carefully")

    if nf:
        if raw_sugar > 0 and normalized_sugar >= sugar_threshold:
            if "⚠ Contains added sugars or refined sweeteners" not in warnings and not any("sugar" in w.lower() for w in warnings):
                warnings.append(f"⚠ High sugar content ({raw_sugar}g {unit_label})")
        if raw_sodium > 0 and normalized_sodium >= 600:
            if not any("sodium" in w.lower() for w in warnings):
                warnings.append(f"⚠ High sodium ({raw_sodium}mg {unit_label})")

    # Informational transparency notices
    if is_sparse:
        warnings.append("ℹ Sparse ingredient list (< 3 items detected): Score is capped as an estimate pending full label scan.")
    if has_unverified:
        warnings.append("ℹ Contains unverified ingredient(s) not in our database — review packaging for details.")
    if not has_substantive_nutrition:
        warnings.append("ℹ Ingredient-based assessment: Nutrition Facts were not scanned or available.")

    # Product category resolution & Dietary supplement checks
    detected_name, detected_category = resolve_product_name_and_category(
        provided_name=provided_product_name,
        provided_category=provided_product_category,
        ocr_text=raw_ocr_text,
        parsed_ingredients=raw_ingredients
    )

    is_supplement = (
        detected_category == "Dietary Supplement" or
        "supplement" in (provided_product_category or "").lower() or
        "supplement" in detected_category.lower() or
        "nutraceutical" in (raw_ocr_text or "").lower()
    )
    if is_supplement:
        warnings.append("⚠ Dietary Supplement / Nutraceutical: Formulated for supplemental use. Consult packaging for recommended daily allowance (RDA) and dosage.")

    # -------------------------------------------------------------------------
    # Step 9: Smart, context-aware summary
    # -------------------------------------------------------------------------
    if overall_status == "GOOD":
        if score >= 95:
            summary = "Excellent ingredient profile — clean and minimally processed."
        elif score >= 80:
            summary = "Good overall — mostly wholesome ingredients with minor points to note."
        else:
            summary = "Generally acceptable, though some ingredients are worth monitoring."
    elif overall_status == "CAUTION":
        summary = (
            f"Contains {caution_count} ingredient(s) worth checking before regular consumption. "
            "Occasional use is typically fine for most people."
        )
    else:
        avoid_names = [i["name"] for i in final_ingredients if i["status"] == "AVOID"][:2]
        concern_str = " and ".join(avoid_names) if avoid_names else "certain ingredients"
        summary = (
            f"Contains {concern_str} which may not be suitable based on health guidelines "
            "or your dietary preferences. Review before purchasing."
        )

    # -------------------------------------------------------------------------
    # Step 10: Actionable recommendations
    # -------------------------------------------------------------------------
    recommendations = []
    if is_supplement:
        recommendations.append("Follow the manufacturer's suggested serving size. Dietary supplements should not replace a balanced diet.")
    if avoid_count > 0:
        recommendations.append("Consider alternatives with cleaner ingredient lists.")
    if has_allergens:
        recommendations.append("Check allergen declarations on the physical label — formulations may change.")
    if not recommendations:
        recommendations.append("Check the manufacturer label for the latest ingredient formulation.")

    # Score breakdown for transparent display in the UI
    score_breakdown = {
        "base_score": 100,
        "assessment_type": assessment_type,
        "assessment_label": assessment_label,
        "deductions": score_deductions,
        "bonuses": score_bonuses,
        "final_score": score,
        "good_count": good_count,
        "caution_count": caution_count,
        "avoid_count": avoid_count,
        "nutrition_integrated": bool(has_substantive_nutrition and nutrition_deduction > 0),
        "disclaimer": (
            "Score is an informational estimate based on ingredient safety classifications "
            "and available nutrition data. It is not a medical or clinical assessment."
        )
    }

    return {
        "product_name": detected_name,
        "product_category": detected_category,
        "assessment_type": assessment_type,
        "assessment_label": assessment_label,
        "overall_status": overall_status,
        "score": score,
        "score_breakdown": score_breakdown,
        "positive_findings": positive_findings,
        "summary": summary,
        "ingredients": final_ingredients,
        "warnings": warnings,
        "recommendations": recommendations,
        "nutrition_facts": nf
    }
