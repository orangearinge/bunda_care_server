"""
Recommendation Service

Handles meal recommendation logic including:
- Menu filtering based on dietary restrictions
- Nutritional scoring and matching
- Detection boost calculations
"""

from datetime import timedelta, date
from typing import Dict, List, Set, Tuple, Any
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
    total = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    ingredients = []
    
    for composition in composition_by_menu.get(menu.id, []):
        ingredient = ingredient_map.get(composition.ingredient_id)
        if not ingredient:
            continue
        
        quantity = float(composition.quantity_g)
        nutrition = serialize_nutrition(ingredient, quantity)
        
        for key in ("calories", "protein_g", "carbs_g", "fat_g"):
            total[key] += nutrition[key]
        
        ingredients.append({
            "ingredient_id": ingredient.id,
            "name": ingredient.name,
            "quantity_g": quantity
        })
    
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
    detected_ids: Set[int]
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
        
    Returns:
        Dictionary with recommendation options
    """
    # Get dietary restrictions
    restrictions = set(preference.food_prohibitions or [])
    allergens = set(preference.allergens or [])
    
    # Get recommendation parameters
    boost_per_hit = arg_int("boost_per_hit", DEFAULT_BOOST_PER_HIT, min_value=0, max_value=1000)
    boost_per_100g = arg_int("boost_per_100g", DEFAULT_BOOST_PER_100G, min_value=0, max_value=10000)
    min_hits = arg_int("min_hits", DEFAULT_MIN_HITS, min_value=1, max_value=10)
    options_per_meal = arg_int("options_per_meal", DEFAULT_OPTIONS_PER_MEAL, min_value=1, max_value=10)
    
    # Parse boolean parameters
    require_detected_param = request.args.get("require_detected")
    require_detected = (
        bool(detected_ids) if require_detected_param is None 
        else (require_detected_param.lower() == "true")
    )
    
    boost_by_quantity = (
        request.args.get("boost_by_quantity", "true").lower() == "true"
    )
    
    # Filter meal types
    meal_type_filter = (request.args.get("meal_type") or "").upper().strip()
    meal_types = (
        [meal_type_filter] if meal_type_filter in MEAL_TYPES 
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
                    if int(ing.get("ingredient_id")) in detected_ids
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
