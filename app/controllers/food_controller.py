"""
Food Controller Module

Handles food-related endpoints including:
- Food scanning and ingredient detection
- Meal recommendations based on user preferences
- Meal logging and history
- Menu CRUD operations
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Set, Tuple, Optional, Any
from flask import request
from sqlalchemy import desc

from app.extensions import db
from app.utils.ai import recognize
from app.models.ingredient import FoodIngredient
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient
from app.models.preference import UserPreference
from app.utils.http import ok, error, json_body, arg_int, parse_iso_datetime
from app.models.meal_log import FoodMealLog, FoodMealLogItem

# ============================================================================
# Constants
# ============================================================================

RAW_KEYWORDS = ["dada", "paha", "fillet", "kulit", "hati", "ati", "telur", "mentah", "raw"]
MEAL_TYPES = ["BREAKFAST", "LUNCH", "DINNER"]

# Nutrition calculation constants
CALORIES_PER_GRAM_CARBS = 4.0
CALORIES_PER_GRAM_FAT = 9.0

# Default nutritional targets
DEFAULT_CALORIE_TARGET = 2000
DEFAULT_MIN_PROTEIN_G = 50.0
DEFAULT_CARBS_PERCENTAGE = 0.5
DEFAULT_FAT_PERCENTAGE = 0.3

# Scoring and boost defaults
DEFAULT_TOP_CANDIDATES = 3
DEFAULT_OPTIONS_PER_MEAL = 3
DEFAULT_BOOST_PER_HIT = 400
DEFAULT_BOOST_PER_100G = 5
DEFAULT_MIN_HITS = 1

# Gestational age thresholds (weeks)
FIRST_TRIMESTER_WEEKS = 13
SECOND_TRIMESTER_WEEKS = 28

# ============================================================================
# Helper Functions - General
# ============================================================================

def _normalize_name(ingredient: FoodIngredient) -> str:
    """Normalize ingredient name and alt_names to lowercase for matching."""
    name = (ingredient.name or '').lower()
    alt = (ingredient.alt_names or '').lower()
    return f"{name} {alt}"


def serialize_nutrition(ingredient: FoodIngredient, quantity_g: float) -> Dict[str, float]:
    """
    Calculate nutritional values for a given quantity of an ingredient.
    
    Args:
        ingredient: The ingredient to calculate nutrition for
        quantity_g: Quantity in grams
        
    Returns:
        Dictionary with calories, protein_g, carbs_g, fat_g
    """
    factor = (quantity_g or 100) / 100.0
    return {
        "calories": int(ingredient.calories * factor),
        "protein_g": float(ingredient.protein_g) * factor,
        "carbs_g": float(ingredient.carbs_g) * factor,
        "fat_g": float(ingredient.fat_g) * factor,
    }


def _has_raw_hint(ingredient: FoodIngredient) -> bool:
    """Check if ingredient name suggests it's a raw ingredient."""
    normalized = _normalize_name(ingredient)
    return any(keyword in normalized for keyword in RAW_KEYWORDS)


def _parse_detected_ids_from_query() -> Set[int]:
    """Extract detected ingredient IDs from query string."""
    detected_ids = set()
    detected_ids_param = (request.args.get("detected_ids") or "").strip()
    
    if detected_ids_param:
        for token in detected_ids_param.replace(",", " ").split():
            try:
                detected_ids.add(int(token))
            except ValueError:
                pass
    
    return detected_ids


def _parse_detected_ids_from_body(body: Dict) -> Set[int]:
    """
    Extract detected ingredient IDs from JSON body.
    
    Supports multiple formats:
    - { detected_ids: [1,2,3] }
    - { detected: [1,2,3] }
    - { candidates: [{ingredient_id: 1}, ...] }
    - { items: [{ingredient_id: 1}, ...] }
    """
    detected_ids = set()
    
    def add_from_iterable(value):
        if isinstance(value, (list, tuple, set)):
            for item in value:
                try:
                    if isinstance(item, dict) and "ingredient_id" in item:
                        detected_ids.add(int(item.get("ingredient_id")))
                    else:
                        detected_ids.add(int(item))
                except (ValueError, TypeError):
                    pass
    
    if not isinstance(body, dict):
        return detected_ids
    
    for key in ["detected_ids", "detected", "candidates", "items"]:
        if key in body:
            add_from_iterable(body.get(key))
    
    return detected_ids


# ============================================================================
# Helper Functions - Scan Food
# ============================================================================

def _score_ingredient_match(
    label: str,
    ingredient: FoodIngredient,
    confidence: float
) -> float:
    """
    Calculate match score between detected label and ingredient.
    
    Args:
        label: Detected label from AI recognition
        ingredient: Ingredient to match against
        confidence: AI confidence score
        
    Returns:
        Match score (higher is better)
    """
    label_lower = label.lower()
    name_lower = (ingredient.name or "").lower()
    alt_lower = (ingredient.alt_names or "").lower()
    
    # Tokenize for word-level matching
    label_tokens = set(label_lower.split())
    name_tokens = set(name_lower.split())
    alt_tokens = set(alt_lower.split())
    
    # Calculate score based on various matching criteria
    score = 0.0
    
    # Token overlap scoring
    name_overlap = len(label_tokens & name_tokens)
    alt_overlap = len(label_tokens & alt_tokens)
    score += 3 * name_overlap + 2 * alt_overlap
    
    # Substring matching
    if label_lower in name_lower:
        score += 2
    if label_lower in alt_lower:
        score += 1
    
    # Boost if it's a raw ingredient
    if _has_raw_hint(ingredient):
        score += 1
    
    # Apply confidence factor
    score = score * (0.5 + confidence)
    
    return score


def _build_candidate_from_ingredient(
    ingredient: FoodIngredient,
    confidence: float
) -> Dict[str, Any]:
    """Build candidate object from ingredient for scan food response."""
    return {
        "ingredient_id": ingredient.id,
        "name": ingredient.name,
        "confidence": float(confidence),
        "per_100g": {
            "calories": ingredient.calories,
            "protein_g": float(ingredient.protein_g),
            "carbs_g": float(ingredient.carbs_g),
            "fat_g": float(ingredient.fat_g),
        },
        "suggested_quantity_g": 100
    }


# ============================================================================
# Helper Functions - Recommendations
# ============================================================================

def _calculate_nutritional_targets(preference: UserPreference) -> Dict[str, Any]:
    """
    Calculate daily nutritional targets based on user role and preferences.
    
    Args:
        preference: User preference object
        
    Returns:
        Dictionary with calorie and macronutrient targets
    """
    role = (preference.role or "").upper()
    height_m = (float(preference.height_cm or 0) / 100.0) if preference.height_cm else 0.0
    weight = float(preference.weight_kg or 0)
    bmi = (weight / (height_m * height_m)) if height_m > 0 else None
    
    # Base defaults
    calorie_target = int(preference.calorie_target or DEFAULT_CALORIE_TARGET)
    protein_g = max(DEFAULT_MIN_PROTEIN_G, 0.9 * weight)
    carbs_percentage = DEFAULT_CARBS_PERCENTAGE
    fat_percentage = DEFAULT_FAT_PERCENTAGE
    
    # Role-specific adjustments
    if role == "IBU_HAMIL":
        calorie_target, protein_g = _calculate_pregnant_targets(preference, weight)
    elif role == "IBU_MENYUSUI":
        calorie_target, protein_g = _calculate_lactating_targets(preference, weight)
    elif role == "ANAK_BALITA":
        calorie_target, protein_g = _calculate_toddler_targets(weight)
        fat_percentage = 0.35
    
    return {
        "calories": calorie_target,
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carbs_percentage * calorie_target / CALORIES_PER_GRAM_CARBS, 1),
        "fat_g": round(fat_percentage * calorie_target / CALORIES_PER_GRAM_FAT, 1),
        "bmi": round(bmi, 1) if bmi else None,
    }


def _calculate_pregnant_targets(
    preference: UserPreference,
    weight: float
) -> Tuple[int, float]:
    """Calculate calorie and protein targets for pregnant women."""
    gestational_age = preference.gestational_age_week or 0
    
    # Calorie adjustment based on trimester
    if gestational_age < FIRST_TRIMESTER_WEEKS:
        additional_calories = 0
    elif gestational_age < SECOND_TRIMESTER_WEEKS:
        additional_calories = 340
    else:
        additional_calories = 452
    
    calorie_target = int(preference.calorie_target or (DEFAULT_CALORIE_TARGET + additional_calories))
    protein_g = max(70.0, 1.1 * weight)
    
    # LILA (mid-upper arm circumference) adjustment for undernutrition
    try:
        lila_cm = float(preference.lila_cm or 0)
        if lila_cm and lila_cm < 23.5:
            calorie_target += 200
            protein_g = round(protein_g * 1.1, 1)
    except (ValueError, TypeError):
        pass
    
    return calorie_target, protein_g


def _calculate_lactating_targets(
    preference: UserPreference,
    weight: float
) -> Tuple[int, float]:
    """Calculate calorie and protein targets for lactating women."""
    # Try to get lactation volume from query param first, then preference
    lactation_ml = None
    query_param = request.args.get("lactation_ml")
    
    if query_param is not None and query_param != "":
        try:
            lactation_ml = float(query_param)
        except (ValueError, TypeError):
            pass
    
    if lactation_ml is None:
        try:
            lactation_ml = float(preference.lactation_ml or 0)
        except (ValueError, TypeError):
            lactation_ml = None
    
    # Calculate additional calories based on lactation volume
    if lactation_ml and lactation_ml > 0:
        additional_calories = int(0.67 * lactation_ml)
    else:
        additional_calories = 500
    
    calorie_target = int(preference.calorie_target or (2200 + additional_calories))
    protein_g = max(75.0, 1.1 * weight)
    
    return calorie_target, protein_g


def _calculate_toddler_targets(weight: float) -> Tuple[int, float]:
    """Calculate calorie and protein targets for toddlers."""
    default_weight = weight or 12
    calorie_target = int(max(900, min(1400, 90 * default_weight)))
    protein_g = max(20.0, 1.1 * default_weight)
    
    return calorie_target, protein_g


def _is_menu_allowed(
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


def _calculate_menu_nutrition(
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


def _calculate_menu_score(
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


def _apply_detection_boost(
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


# ============================================================================
# Request Handlers
# ============================================================================

def scan_food_handler():
    """
    Scan food image and return ingredient candidates.
    
    Uses AI to recognize food items in the image and matches them
    against the ingredient database.
    """
    image = request.files.get("image")
    if not image:
        return error("IMAGE_REQUIRED", "image file is required", 400)
    
    # Get AI recognition results
    labels = recognize(image)
    label_names = [
        str(label.get("label", "")).strip().lower() 
        for label in labels 
        if label.get("label")
    ]
    
    if not label_names:
        return ok({"candidates": []})
    
    # Query ingredients that might match
    like_patterns = [f"%{name}%" for name in label_names]
    or_clauses = [
        clause 
        for pattern in like_patterns 
        for clause in (
            FoodIngredient.name.ilike(pattern),
            FoodIngredient.alt_names.ilike(pattern)
        )
    ]
    
    ingredients = FoodIngredient.query.filter(db.or_(*or_clauses)).limit(20).all()
    
    # Score and rank candidates for each detected label
    candidates = []
    
    for label in labels:
        label_text = label["label"].lower()
        confidence = float(label.get("confidence", 0) or 0)
        
        # Score all ingredients for this label
        scored = [
            (_score_ingredient_match(label_text, ing, confidence), ing)
            for ing in ingredients
        ]
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Take top N candidates
        for _, ingredient in scored[:DEFAULT_TOP_CANDIDATES]:
            candidates.append(_build_candidate_from_ingredient(ingredient, confidence))
    
    # Deduplicate - keep highest confidence for each ingredient
    deduped = {}
    for candidate in candidates:
        ingredient_id = candidate["ingredient_id"]
        if (ingredient_id not in deduped or 
            candidate["confidence"] > deduped[ingredient_id]["confidence"]):
            deduped[ingredient_id] = candidate
    
    return ok({
        "candidates": list(deduped.values()),
        "detected_ids": [c["ingredient_id"] for c in deduped.values()],
    })


def recommendation_handler():
    """
    Generate meal recommendations based on user preferences and optional detected ingredients.
    
    Query Parameters:
        - days: Number of days to generate (1-31)
        - date: Start date (ISO format)
        - meal_type: Filter by specific meal type (BREAKFAST/LUNCH/DINNER)
        - detected_ids: Comma-separated ingredient IDs
        - boost_per_hit: Boost amount per detected ingredient hit
        - boost_per_100g: Boost amount per 100g of detected ingredients
        - boost_by_quantity: Whether to boost by ingredient quantity
        - require_detected: Require menus to contain detected ingredients
        - min_hits: Minimum number of detected ingredient hits required
        - options_per_meal: Number of menu options to return per meal
        - hide_options: Hide alternative menu options
    """
    user_id = request.user_id
    days = arg_int("days", 1, min_value=1, max_value=31)
    
    # Get user preferences
    preference = UserPreference.query.get(user_id)
    if not preference:
        return error("PREFERENCE_REQUIRED", "Please complete preferences", 409)
    
    # Calculate nutritional targets
    targets = _calculate_nutritional_targets(preference)
    
    # Load menus and ingredients
    menus = FoodMenu.query.filter_by(is_active=True).order_by(
        FoodMenu.meal_type, FoodMenu.name
    ).all()
    menu_ids = [menu.id for menu in menus]
    
    ingredient_map = {ing.id: ing for ing in FoodIngredient.query.all()}
    
    compositions = FoodMenuIngredient.query.filter(
        FoodMenuIngredient.menu_id.in_(menu_ids)
    ).all()
    composition_by_menu = {}
    for comp in compositions:
        composition_by_menu.setdefault(comp.menu_id, []).append(comp)
    
    # Get dietary restrictions
    restrictions = set(preference.food_prohibitions or [])
    allergens = set(preference.allergens or [])
    
    # Parse detected ingredients
    detected_ids = _parse_detected_ids_from_query()
    detected_ids.update(_parse_detected_ids_from_body(json_body() or {}))
    
    # Get boost parameters
    boost_per_hit = arg_int("boost_per_hit", DEFAULT_BOOST_PER_HIT, min_value=0, max_value=1000)
    boost_per_100g = arg_int("boost_per_100g", DEFAULT_BOOST_PER_100G, min_value=0, max_value=10000)
    min_hits = arg_int("min_hits", DEFAULT_MIN_HITS, min_value=1, max_value=10)
    options_per_meal = arg_int("options_per_meal", DEFAULT_OPTIONS_PER_MEAL, min_value=1, max_value=5)
    
    # Parse boolean parameters
    require_detected_param = request.args.get("require_detected")
    require_detected = (
        bool(detected_ids) if require_detected_param is None 
        else (require_detected_param.lower() == "true")
    )
    
    boost_by_quantity = (
        request.args.get("boost_by_quantity", "true").lower() == "true"
    )
    
    hide_options_param = request.args.get("hide_options")
    hide_options = (
        bool(detected_ids) if hide_options_param is None 
        else (hide_options_param.lower() == "true")
    )
    
    # Parse date parameters
    date_str = request.args.get("date")
    try:
        base_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        base_date = date.today()
    
    # Filter meal types
    meal_type_filter = (request.args.get("meal_type") or "").upper().strip()
    meal_types = (
        [meal_type_filter] if meal_type_filter in MEAL_TYPES 
        else MEAL_TYPES
    )
    
    # Generate recommendations
    plan = []
    
    for day_offset in range(days):
        day_date = base_date + timedelta(days=day_offset)
        meals_payload = []
        
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
                if not _is_menu_allowed(menu, allergens, restrictions, 
                                       ingredient_map, composition_by_menu):
                    continue
                
                # Calculate nutrition
                nutrition, ingredients = _calculate_menu_nutrition(
                    menu, ingredient_map, composition_by_menu
                )
                
                # Calculate base score
                score = _calculate_menu_score(nutrition, targets)
                
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
                    score = _apply_detection_boost(
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
            
            # Add best option as recommendation
            if options:
                best_option = options[0]
                meals_payload.append({
                    "meal_type": meal_type,
                    **{
                        key: best_option[key] 
                        for key in ["menu_id", "menu_name", "nutrition", "ingredients"]
                    },
                    "food_log_payload": best_option["food_log_payload"],
                })
            
            # Add all options if not hidden
            if not hide_options:
                meals_payload.append({
                    "meal_type": meal_type,
                    "options": options
                })
        
        # Calculate daily summary
        summary = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for meal in meals_payload:
            if "nutrition" in meal:
                nutrition = meal["nutrition"]
                for key in ("calories", "protein_g", "carbs_g", "fat_g"):
                    summary[key] += nutrition[key]
        
        plan.append({
            "date": day_date.isoformat(),
            "daily_target": targets,
            "meals": meals_payload,
            "summary": summary
        })
    
    return ok({
        "user_id": user_id,
        "start_date": date.today().isoformat(),
        "days": plan
    })


def create_meal_log_handler():
    """
    Create a meal log entry from a menu.
    
    Body Parameters:
        - menu_id (required): ID of the menu to log
        - servings (optional): Number of servings (default: 1.0)
        - logged_at (optional): Timestamp of the meal (ISO format)
    """
    user_id = request.user_id
    data = json_body()
    
    # Validate menu_id
    try:
        menu_id = int(data.get("menu_id"))
    except (ValueError, TypeError):
        return error("VALIDATION_ERROR", "menu_id required", 400)
    
    # Parse servings
    try:
        servings = float(data.get("servings")) if data.get("servings") is not None else 1.0
    except (ValueError, TypeError):
        servings = 1.0
    
    if servings <= 0:
        servings = 1.0
    
    # Validate menu exists
    menu = FoodMenu.query.get(menu_id)
    if not menu:
        return error("MENU_NOT_FOUND", "menu_id does not exist", 400)
    
    # Get menu ingredients
    compositions = FoodMenuIngredient.query.filter_by(menu_id=menu_id).all()
    if not compositions:
        return error("MENU_EMPTY", "No ingredients for the specified menu_id", 400)
    
    ingredient_map = {ing.id: ing for ing in FoodIngredient.query.all()}
    
    # Calculate totals
    total = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    items_payload = []
    
    for composition in compositions:
        ingredient = ingredient_map.get(composition.ingredient_id)
        if not ingredient:
            continue
        
        quantity = float(composition.quantity_g) * float(servings)
        nutrition = serialize_nutrition(ingredient, quantity)
        
        total["calories"] += nutrition["calories"]
        total["protein_g"] += nutrition["protein_g"]
        total["carbs_g"] += nutrition["carbs_g"]
        total["fat_g"] += nutrition["fat_g"]
        
        items_payload.append((ingredient.id, quantity, nutrition))
    
    # Create meal log
    try:
        logged_at = parse_iso_datetime(data.get("logged_at")) or datetime.utcnow()
        
        meal_log = FoodMealLog(
            user_id=user_id,
            menu_id=menu_id,
            total_calories=int(total["calories"]),
            total_protein_g=float(total["protein_g"]),
            total_carbs_g=float(total["carbs_g"]),
            total_fat_g=float(total["fat_g"]),
            servings=float(servings),
            logged_at=logged_at,
        )
        db.session.add(meal_log)
        db.session.flush()
        
        # Create meal log items
        for ingredient_id, quantity, nutrition in items_payload:
            db.session.add(FoodMealLogItem(
                meal_log_id=meal_log.id,
                ingredient_id=ingredient_id,
                quantity_g=float(quantity),
                calories=int(nutrition["calories"]),
                protein_g=float(nutrition["protein_g"]),
                carbs_g=float(nutrition["carbs_g"]),
                fat_g=float(nutrition["fat_g"]),
            ))
        
        db.session.commit()
        
        return ok({
            "meal_log_id": meal_log.id,
            "menu_id": menu_id,
            "menu_name": menu.name,
            "servings": float(servings),
            "logged_at": meal_log.logged_at.isoformat() if meal_log.logged_at else None,
            "total": total,
            "items": [
                {"ingredient_id": iid, "quantity_g": float(qty), **nutr} 
                for iid, qty, nutr in items_payload
            ]
        }, 201)
    
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def list_meal_log_handler():
    """
    List meal logs for the current user.
    
    Query Parameters:
        - limit: Maximum number of logs to return (default: 10)
    """
    user_id = request.user_id
    limit = arg_int("limit", 10)
    
    # Get meal logs
    logs = (
        FoodMealLog.query
        .filter_by(user_id=user_id)
        .order_by(desc(FoodMealLog.logged_at))
        .limit(limit)
        .all()
    )
    
    # Load related data
    menu_map = {menu.id: menu for menu in FoodMenu.query.all()}
    log_ids = [log.id for log in logs]
    
    items = FoodMealLogItem.query.filter(
        FoodMealLogItem.meal_log_id.in_(log_ids or [0])
    ).all()
    
    items_by_log = {}
    for item in items:
        items_by_log.setdefault(item.meal_log_id, []).append(item)
    
    # Build response
    payload = []
    for log in logs:
        menu = menu_map.get(log.menu_id)
        payload.append({
            "meal_log_id": log.id,
            "menu_id": log.menu_id,
            "menu_name": menu.name if menu else None,
            "servings": float(log.servings),
            "logged_at": log.logged_at.isoformat() if log.logged_at else None,
            "total": {
                "calories": int(log.total_calories),
                "protein_g": float(log.total_protein_g),
                "carbs_g": float(log.total_carbs_g),
                "fat_g": float(log.total_fat_g),
            },
            "items": [
                {
                    "ingredient_id": item.ingredient_id,
                    "quantity_g": float(item.quantity_g),
                    "calories": int(item.calories),
                    "protein_g": float(item.protein_g),
                    "carbs_g": float(item.carbs_g),
                    "fat_g": float(item.fat_g),
                }
                for item in items_by_log.get(log.id, [])
            ]
        })
    
    return ok({"items": payload})


def list_menus_handler():
    """List all menus with their ingredients."""
    menus = FoodMenu.query.order_by(FoodMenu.meal_type, FoodMenu.name).all()
    menu_ids = [menu.id for menu in menus]
    
    # Get all menu ingredients
    menu_ingredients = FoodMenuIngredient.query.filter(
        FoodMenuIngredient.menu_id.in_(menu_ids or [0])
    ).all()
    
    # Get all ingredients
    ingredient_ids = [mi.ingredient_id for mi in menu_ingredients]
    ingredients = FoodIngredient.query.filter(
        FoodIngredient.id.in_(ingredient_ids or [0])
    ).all()
    ingredient_map = {ing.id: ing for ing in ingredients}
    
    # Group ingredients by menu
    ingredients_by_menu = {}
    for menu_ingredient in menu_ingredients:
        if menu_ingredient.menu_id not in ingredients_by_menu:
            ingredients_by_menu[menu_ingredient.menu_id] = []
        
        ingredient = ingredient_map.get(menu_ingredient.ingredient_id)
        if ingredient:
            ingredients_by_menu[menu_ingredient.menu_id].append({
                "ingredient_id": ingredient.id,
                "name": ingredient.name,
                "quantity_g": float(menu_ingredient.quantity_g)
            })
    
    # Build response
    data = []
    for menu in menus:
        data.append({
            "id": menu.id,
            "name": menu.name,
            "meal_type": menu.meal_type,
            "tags": menu.tags,
            "is_active": menu.is_active,
            "ingredients": ingredients_by_menu.get(menu.id, [])
        })
    
    return ok(data)


def create_menu_handler():
    """
    Create a new menu with ingredients.
    
    Body Parameters:
        - name (required): Menu name
        - meal_type (required): BREAKFAST/LUNCH/DINNER
        - tags (optional): Comma-separated tags
        - is_active (optional): Whether menu is active (default: True)
        - ingredients (optional): List of {ingredient_id, quantity_g}
    """
    data = json_body()
    
    # Validate required fields
    name = (data.get("name") or "").strip()
    meal_type = (data.get("meal_type") or "").strip().upper()
    
    if not name or not meal_type:
        return error("VALIDATION_ERROR", "Name and meal_type are required", 400)
    
    try:
        # Create menu
        menu = FoodMenu(
            name=name,
            meal_type=meal_type,
            tags=data.get("tags", ""),
            is_active=data.get("is_active", True)
        )
        db.session.add(menu)
        db.session.flush()
        
        # Add ingredients
        ingredients = data.get("ingredients", [])
        for item in ingredients:
            ingredient_id = item.get("ingredient_id")
            quantity_g = item.get("quantity_g")
            
            if ingredient_id and quantity_g:
                db.session.add(FoodMenuIngredient(
                    menu_id=menu.id,
                    ingredient_id=ingredient_id,
                    quantity_g=quantity_g
                ))
        
        db.session.commit()
        return ok({"id": menu.id, "message": "Menu created successfully"}, 201)
    
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def update_menu_handler(menu_id: int):
    """
    Update an existing menu.
    
    Body Parameters (all optional):
        - name: Menu name
        - meal_type: BREAKFAST/LUNCH/DINNER
        - tags: Comma-separated tags
        - is_active: Whether menu is active
        - ingredients: List of {ingredient_id, quantity_g} (replaces all)
    """
    menu = FoodMenu.query.get(menu_id)
    if not menu:
        return error("NOT_FOUND", "Menu not found", 404)
    
    data = json_body()
    
    # Update fields if provided
    if "name" in data:
        menu.name = data["name"]
    if "meal_type" in data:
        menu.meal_type = data["meal_type"].upper()
    if "tags" in data:
        menu.tags = data["tags"]
    if "is_active" in data:
        menu.is_active = data["is_active"]
    
    try:
        # Update ingredients if provided
        if "ingredients" in data:
            # Delete existing ingredients
            FoodMenuIngredient.query.filter_by(menu_id=menu_id).delete()
            
            # Add new ingredients
            for item in data["ingredients"]:
                ingredient_id = item.get("ingredient_id")
                quantity_g = item.get("quantity_g")
                
                if ingredient_id and quantity_g:
                    db.session.add(FoodMenuIngredient(
                        menu_id=menu.id,
                        ingredient_id=ingredient_id,
                        quantity_g=quantity_g
                    ))
        
        db.session.commit()
        return ok({"id": menu.id, "message": "Menu updated successfully"})
    
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def delete_menu_handler(menu_id: int):
    """Delete a menu and its associated ingredients."""
    menu = FoodMenu.query.get(menu_id)
    if not menu:
        return error("NOT_FOUND", "Menu not found", 404)
    
    try:
        # Delete menu ingredients first
        FoodMenuIngredient.query.filter_by(menu_id=menu_id).delete()
        
        # Delete menu
        db.session.delete(menu)
        db.session.commit()
        
        return ok({"message": "Menu deleted successfully"})
    
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def get_menu_detail_handler(menu_id: int):
    """Get detailed information about a menu including its ingredients."""
    menu = FoodMenu.query.get(menu_id)
    if not menu:
        return error("NOT_FOUND", "Menu not found", 404)
    
    # Get menu ingredients
    ingredients = []
    menu_ingredients = FoodMenuIngredient.query.filter_by(menu_id=menu_id).all()
    
    for menu_ingredient in menu_ingredients:
        ingredient = FoodIngredient.query.get(menu_ingredient.ingredient_id)
        if ingredient:
            ingredients.append({
                "ingredient_id": ingredient.id,
                "name": ingredient.name,
                "quantity_g": float(menu_ingredient.quantity_g)
            })
    
    return ok({
        "id": menu.id,
        "name": menu.name,
        "meal_type": menu.meal_type,
        "tags": menu.tags,
        "is_active": menu.is_active,
        "ingredients": ingredients
    })
