"""
Recommendation Service

Handles meal recommendation logic including:
- Menu filtering based on dietary restrictions
- Nutritional scoring and matching
- Detection boost calculations
"""

from datetime import timedelta, date
from typing import Dict, List, Set, Tuple, Any, Optional
from flask import request

from app.models.ingredient import FoodIngredient
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient
from app.models.preference import UserPreference
from app.services.food_helpers import serialize_nutrition
from app.services.food_constants import (
    MEAL_TYPES,
    DEFAULT_OPTIONS_PER_MEAL,
    DEFAULT_BOOST_PER_HIT,
    DEFAULT_BOOST_PER_100G,
    DEFAULT_MIN_HITS
)
from app.utils.http import arg_int
from app.utils.enums import UserRole, TargetRole


def is_menu_allowed(
    menu: FoodMenu,
    allergens: Set[str],
    restrictions: Set[str],
    ingredient_map: Dict[int, FoodIngredient],
    composition_by_menu: Dict[int, List]
) -> bool:
    """
    Check if menu is allowed based on allergens and dietary restrictions.
    
    Args:
        menu: Menu to check
        allergens: Set of allergens to avoid
        restrictions: Set of dietary restrictions
        ingredient_map: Map of ingredient IDs to ingredients
        composition_by_menu: Map of menu IDs to their ingredients
        
    Returns:
        True if menu is allowed, False otherwise
    """
    # Check menu tags
    menu_tags = set((menu.tags or "").lower().split(","))
    
    if any(allergen.lower() in menu_tags for allergen in allergens):
        return False
    
    if any(restriction.lower() in menu_tags for restriction in restrictions):
        return False
    
    # Check ingredient names and alt_names
    for composition in composition_by_menu.get(menu.id, []):
        ingredient = ingredient_map.get(composition.ingredient_id)
        if not ingredient:
            continue
        
        name_lower = (ingredient.name or "").lower()
        alt_lower = (getattr(ingredient, "alt_names", None) or "").lower()
        
        # Check allergens
        if any(allergen.lower() in name_lower or allergen.lower() in alt_lower 
               for allergen in allergens):
            return False
        
        # Check restrictions
        if any(restriction.lower() in name_lower or restriction.lower() in alt_lower 
               for restriction in restrictions):
            return False
    
    return True


def calculate_menu_nutrition(
    menu: FoodMenu,
    ingredient_map: Dict[int, FoodIngredient],
    composition_by_menu: Dict[int, List]
) -> Tuple[Dict[str, float], List[Dict]]:
    """
    Calculate total nutrition for a menu and return ingredient details.
    
    Returns:
        Tuple of (total nutrition dict, list of ingredient details)
    """
    # GOLDEN OVERRIDE LOGIC
    if menu.nutrition_is_manual and menu.manual_calories is not None:
        total = {
            "calories": int(menu.manual_calories),
            "protein_g": float(menu.manual_protein_g or 0),
            "carbs_g": float(menu.manual_carbs_g or 0),
            "fat_g": float(menu.manual_fat_g or 0),
        }
    else:
        total = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    
    ingredients = []
    
    for composition in composition_by_menu.get(menu.id, []):
        ingredient = ingredient_map.get(composition.ingredient_id)
        
        # Build ingredient details for the response regardless of calculation method
        qty = float(composition.quantity_g) if composition.quantity_g is not None else 0
        
        ing_data = {
            "ingredient_id": composition.ingredient_id,
            "name": ingredient.name if ingredient else "",
            "quantity_g": qty,
            "display_text": composition.display_quantity
        }
        ingredients.append(ing_data)

        # Only add to total if NOT using manual override and ingredient/quantity exists
        if not menu.nutrition_is_manual or menu.manual_calories is None:
            if ingredient and composition.quantity_g is not None:
                nutrition = serialize_nutrition(ingredient, qty)
                total["calories"] += int(nutrition["calories"]) # Ensure int
                total["protein_g"] += nutrition["protein_g"]
                total["carbs_g"] += nutrition["carbs_g"]
                total["fat_g"] += nutrition["fat_g"]
    
    return total, ingredients


def calculate_menu_score(
    nutrition: Dict[str, float], 
    targets: Dict[str, float],
    portions_per_day: float = 3.0
) -> float:
    """
    Calculate how well a menu matches nutritional targets.
    
    Lower score is better (represents deviation from target).
    """
    target_per_portion = {
        key: (targets[key] / portions_per_day) 
        for key in ["calories", "protein_g", "carbs_g", "fat_g"]
    }
    
    score = sum(
        abs(float(nutrition[key]) - float(target_per_portion[key])) 
        for key in target_per_portion
    )
    
    return score


def apply_detection_boost(
    base_score: float,
    ingredients: List[Dict],
    detected_ids: Set[int],
    boost_per_hit: int,
    boost_by_quantity: bool,
    boost_per_100g: int
) -> float:
    """
    Apply boost to menu score if it contains detected ingredients.
    
    Returns:
        Adjusted score (lower is better)
    """
    hits = 0
    total_quantity = 0.0
    
    for ingredient in ingredients:
        try:
            ingredient_id = int(ingredient.get("ingredient_id"))
            if ingredient_id in detected_ids:
                hits += 1
                quantity = float(ingredient.get("quantity_g") or 0)
                total_quantity += max(0.0, quantity)
        except (ValueError, TypeError):
            pass
    
    if hits == 0:
        return base_score
    
    # Calculate boost amount
    boost_amount = 0
    
    if boost_per_hit > 0:
        boost_amount += hits * boost_per_hit
    
    if boost_by_quantity and total_quantity > 0 and boost_per_100g > 0:
        boost_amount += (total_quantity / 100.0) * boost_per_100g
    
    # Reduce score by boost amount (lower score is better)
    return max(0, base_score - boost_amount)


def generate_meal_recommendations(
    user_id: int,
    preference: UserPreference,
    targets: Dict[str, Any],
    menus: List[FoodMenu],
    ingredient_map: Dict[int, FoodIngredient],
    composition_by_menu: Dict[int, List],
    detected_ids: Set[int],
    boost_per_hit: int = DEFAULT_BOOST_PER_HIT,
    boost_per_100g: int = DEFAULT_BOOST_PER_100G,
    min_hits: int = DEFAULT_MIN_HITS,
    options_per_meal: int = DEFAULT_OPTIONS_PER_MEAL,
    require_detected: Optional[bool] = None,
    boost_by_quantity: bool = True,
    meal_type_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate meal recommendations for immediate selection.
    
    Args:
        user_id: User ID
        preference: User preferences 
        targets: Nutritional targets
        menus: List of available menus
        ingredient_map: Map of ingredient IDs to ingredients
        composition_by_menu: Map of menu IDs to their ingredients
        detected_ids: Set of detected ingredient IDs
        boost_per_hit: Score reduction per detected ingredient hit
        boost_per_100g: Score reduction per 100g of detected ingredient
        min_hits: Minimum detected ingredients required (if require_detected is True)
        options_per_meal: Number of recommendations to return per meal type
        require_detected: If True, only return menus with detected ingredients
        boost_by_quantity: If True, scale boost by ingredient quantity
        meal_type_filter: specific meal type to filter (e.g. BREAKFAST)
        
    Returns:
        Dictionary with recommendation options
    """
    # Get dietary restrictions
    restrictions = set(preference.food_prohibitions or [])
    allergens = set(preference.allergens or [])
    
    # Resolve require_detected
    if require_detected is None:
        require_detected = bool(detected_ids)
        
    # Filter meal types
    meal_type_clean = (meal_type_filter or "").upper().strip()
    meal_types = (
        [meal_type_clean] if meal_type_clean in MEAL_TYPES 
        else MEAL_TYPES
    )
    
    # Generate recommendations
    recommendations = []
    
    for meal_type in meal_types:
        # Filter menus by type
        candidates = [
            menu for menu in menus 
            if menu.meal_type.upper() == meal_type
        ]
        
        # Score and filter menus
        scored_pool = []
        
        for menu in candidates:
            # Check dietary restrictions
            if not is_menu_allowed(menu, allergens, restrictions, 
                                   ingredient_map, composition_by_menu):
                continue
            
            # Filter by target_role
            user_role_cat = TargetRole.IBU
            if preference.role == UserRole.ANAK_BATITA:
                total_months = (preference.age_year or 0) * 12 + (preference.age_month or 0)
                if 6 <= total_months <= 8:
                    user_role_cat = TargetRole.ANAK_6_8
                elif 9 <= total_months <= 11:
                    user_role_cat = TargetRole.ANAK_9_11
                elif 12 <= total_months: # Covers 12-23m and older toddlers (2-3y)
                    user_role_cat = TargetRole.ANAK_12_23
                else:
                    user_role_cat = TargetRole.ANAK # Fallback

            menu_target = (menu.target_role or TargetRole.ALL).upper()
            
            # Match Logic:
            # 1. "ALL" matches everyone
            # 2. "ANAK" matches any child age
            # 3. Specific "ANAK_X_Y" matches only that age range
            # 4. "IBU" matches non-children
            
            if menu_target == TargetRole.ALL:
                pass # Always allow
            elif preference.role == UserRole.ANAK_BATITA:
                if menu_target == TargetRole.IBU:
                    continue # Child can't eat adult food
                if menu_target.startswith("ANAK_") and menu_target != user_role_cat:
                    continue # Wrong age range
            else:
                # User is IBU
                if menu_target.startswith("ANAK"):
                    continue # Ibu doesn't usually get recommended baby food
                if menu_target != TargetRole.IBU:
                    # This covers specific ANAK tags if any leaked
                    continue
            
            
            # Calculate nutrition
            nutrition, ingredients = calculate_menu_nutrition(
                menu, ingredient_map, composition_by_menu
            )
            
            # Calculate base score
            score = calculate_menu_score(nutrition, targets)
            
            # Apply detection boost
            if detected_ids:
                # Count hits
                hits = sum(
                    1 for ing in ingredients 
                    if ing.get("ingredient_id") is not None and int(ing.get("ingredient_id")) in detected_ids
                )
                
                # Skip if doesn't meet minimum hits
                if require_detected and hits < min_hits:
                    continue

                # Apply boost
                score = apply_detection_boost(
                    score, ingredients, detected_ids,
                    boost_per_hit, boost_by_quantity, boost_per_100g
                )
            
            scored_pool.append((score, menu, nutrition, ingredients))
        
        # Sort by score (lower is better)
        scored_pool.sort(key=lambda x: (x[0], x[1].name.lower()))
        
        # Build options
        options = []
        for score, menu, nutrition, ingredient_list in scored_pool[:options_per_meal]:
            options.append({
                "menu_id": menu.id,
                "menu_name": menu.name,
                "image_url": menu.image_url,
                "nutrition": nutrition,
                "ingredients": ingredient_list,
                "score": score,
                "food_log_payload": {
                    "items": [
                        {
                            "ingredient_id": ing["ingredient_id"],
                            "quantity_g": ing["quantity_g"]
                        }
                        for ing in ingredient_list
                    ]
                }
            })
        
        if options:
            recommendations.append({
                "meal_type": meal_type,
                "options": options
            })
    
    return {
        "user_id": user_id,
        "targets": targets,
        "recommendations": recommendations
    }
