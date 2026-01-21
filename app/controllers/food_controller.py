"""
Food Controller Module

Handles food-related endpoints including:
- Food scanning and ingredient detection
- Meal recommendations based on user preferences
- Meal logging and history
- Menu CRUD operations

This controller delegates business logic to specialized services.
"""

from datetime import datetime
from flask import request

from app.extensions import db
from app.models.ingredient import FoodIngredient
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient
from app.models.preference import UserPreference
from app.utils.http import ok, error, json_body, arg_int, validate_schema
from app.utils.enums import UserRole, TargetRole, MealType

# Import services
from app.services.food_scan_service import scan_food_image
from app.services.nutrition_service import calculate_nutritional_targets
from app.services.recommendation_service import generate_meal_recommendations
from app.services.meal_log_service import create_meal_log, list_meal_logs
from app.services.menu_service import (
    list_menus, 
    get_menu_detail, 
    create_menu, 
    update_menu, 
    delete_menu
)
from app.services.food_helpers import (
    parse_detected_ids_from_query,
    parse_detected_ids_from_body
)
from app.schemas.food_schema import (
    CreateMenuSchema,
    UpdateMenuSchema,
    CreateMealLogSchema,
    ListMenuQuerySchema
)


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
    
    try:
        result = scan_food_image(image)
        return ok(result)
    except Exception as e:
        return error("SCAN_ERROR", str(e), 500)


def recommendation_handler():
    """
    Generate meal recommendations based on user preferences and optional detected ingredients.
    
    Query Parameters:
        - meal_type: Filter by specific meal type (BREAKFAST/LUNCH/DINNER)
        - detected_ids: Comma-separated ingredient IDs
        - boost_per_hit: Boost amount per detected ingredient hit
        - boost_per_100g: Boost amount per 100g of detected ingredients
        - boost_by_quantity: Whether to boost by ingredient quantity
        - require_detected: Require menus to contain detected ingredients
        - min_hits: Minimum number of detected ingredient hits required
        - options_per_meal: Number of menu options to return per meal
    """
    user_id = request.user_id
    
    # Get user preferences
    preference = UserPreference.query.get(user_id)
    if not preference:
        return error("PREFERENCE_REQUIRED", "Please complete preferences", 409)
    
    # Calculate nutritional targets
    targets = calculate_nutritional_targets(preference)
    
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
    
    # Parse detected ingredients
    detected_ids = parse_detected_ids_from_query()
    detected_ids.update(parse_detected_ids_from_body(json_body() or {}))
    
    try:
        result = generate_meal_recommendations(
            user_id=user_id,
            preference=preference,
            targets=targets,
            menus=menus,
            ingredient_map=ingredient_map,
            composition_by_menu=composition_by_menu,
            detected_ids=detected_ids
        )
        return ok(result)
    except Exception as e:
        return error("RECOMMENDATION_ERROR", str(e), 500)


def create_meal_log_handler():
    """
    Create a meal log entry from a menu.
    
    Body Parameters:
        - menu_id (required): ID of the menu to log
        - servings (optional): Number of servings (default: 1.0)
        - is_consumed (optional): Whether the meal was actually eaten (default: False)
        - logged_at (optional): Timestamp of the meal (ISO format)
    """
    from app.utils.http import parse_iso_datetime
    
    user_id = request.user_id
    data, errors = validate_schema(CreateMealLogSchema, json_body())
    
    if errors:
        return error("VALIDATION_ERROR", "Invalid input data", 400, details=errors)
    
    menu_id = data["menu_id"]
    servings = data["servings"]
    is_consumed = data["is_consumed"]
    logged_at = data.get("logged_at") or datetime.utcnow()
    
    try:
        result = create_meal_log(
            user_id=user_id,
            menu_id=menu_id,
            servings=servings,
            logged_at=logged_at,
            is_consumed=is_consumed
        )
        return ok(result, 201)
    except ValueError as e:
        error_msg = str(e)
        if "MENU_NOT_FOUND" in error_msg:
            return error("MENU_NOT_FOUND", "menu_id does not exist", 400)
        elif "MENU_EMPTY" in error_msg:
            return error("MENU_EMPTY", "No ingredients for the specified menu_id", 400)
        return error("VALIDATION_ERROR", error_msg, 400)
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)



def confirm_meal_log_handler(log_id: int):
    """Mark a specific meal log as consumed/eaten."""
    user_id = request.user_id
    from app.services.meal_log_service import confirm_meal_consumed
    
    if confirm_meal_consumed(user_id, log_id):
        return ok({"message": "Meal marked as consumed", "meal_log_id": log_id})
    else:
        return error("NOT_FOUND", "Meal log not found or unauthorized", 404)


def list_meal_log_handler():
    """
    List meal logs for the current user.
    
    Query Parameters:
        - limit: Maximum number of logs to return (default: 10)
    """
    user_id = request.user_id
    limit = arg_int("limit", 10)
    
    try:
        payload = list_meal_logs(user_id, limit)
        return ok({"items": payload})
    except Exception as e:
        return error("UNKNOWN_ERROR", str(e), 500)


def list_menus_handler():
    """
    List menus with search, filter, and pagination.
    
    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 10)
        - search: Search term for name or tags
        - meal_type: Filter by meal type
        - is_active: Filter by active status (true/false)
    """
    # Validate query parameters
    query_data = {
        "page": request.args.get("page"),
        "limit": request.args.get("limit"),
        "search": request.args.get("search"),
        "meal_type": request.args.get("meal_type"),
        "is_active": request.args.get("is_active"),
        "target_role": request.args.get("target_role")
    }
    # Filter out None values to let schema defaults kick in
    query_data = {k: v for k, v in query_data.items() if v is not None}
    
    data, errors = validate_schema(ListMenuQuerySchema, query_data)
    if errors:
        return error("VALIDATION_ERROR", "Invalid query parameters", 400, details=errors)

    page = data["page"]
    limit = data["limit"]
    search = data.get("search")
    meal_type = data.get("meal_type")
    is_active = data.get("is_active")
    target_role = data.get("target_role")

    if not target_role:
        user_id = getattr(request, "user_id", None)
        if user_id:
            pref = UserPreference.query.get(user_id)
            if pref:
                if pref.role == UserRole.ANAK_BATITA:
                    total_months = (pref.age_year or 0) * 12 + (pref.age_month or 0)
                    if 6 <= total_months <= 8:
                        target_role = TargetRole.ANAK_6_8
                    elif 9 <= total_months <= 11:
                        target_role = TargetRole.ANAK_9_11
                    elif 12 <= total_months <= 23:
                        target_role = TargetRole.ANAK_12_23
                    else:
                        target_role = TargetRole.ANAK
                else:
                    target_role = TargetRole.IBU
    
    try:
        result = list_menus(
            page=page,
            limit=limit,
            search=search,
            meal_type=meal_type,
            target_role=target_role,
            is_active=is_active
        )
        return ok(result)
    except Exception as e:
        return error("UNKNOWN_ERROR", str(e), 500)

def create_menu_handler():
    """
    Create a new menu with ingredients.
    
    Body Parameters:
        - name (required): Menu name
        - meal_type (required): BREAKFAST/LUNCH/DINNER
        - tags (optional): Comma-separated tags
        - is_active (optional): Whether menu is active (default: True)
        - ingredients (optional): List of {ingredient_id, quantity_g, display_quantity}
        - nutrition_is_manual (optional): Use manual nutrition values
        - serving_unit (optional): Unit of serving (e.g., "Porsi")
        - manual_calories (optional): Manual calorie value
        - manual_protein_g (optional): Manual protein value
        - manual_carbs_g (optional): Manual carbs value
        - manual_fat_g (optional): Manual fat value
    """
    # Validate input
    data, errors = validate_schema(CreateMenuSchema, json_body())
    if errors:
        return error("VALIDATION_ERROR", "Invalid input data", 400, details=errors)
    
    # Debug logging
    print(f"[CREATE MENU] Received data: {data}")
    
    try:
        menu_id = create_menu(
            name=data["name"],
            meal_type=data["meal_type"],
            tags=data.get("tags", ""),
            image_url=data.get("image_url"),
            description=data.get("description"),
            cooking_instructions=data.get("cooking_instructions"),
            cooking_time_minutes=data.get("cooking_time_minutes"),
            target_role=data.get("target_role", TargetRole.ALL),
            is_active=data.get("is_active", True),
            ingredients=data.get("ingredients", []),
            nutrition_is_manual=data.get("nutrition_is_manual", False),
            serving_unit=data.get("serving_unit"),
            manual_calories=data.get("manual_calories"),
            manual_protein_g=data.get("manual_protein_g"),
            manual_carbs_g=data.get("manual_carbs_g"),
            manual_fat_g=data.get("manual_fat_g")
        )
        print(f"[CREATE MENU] Successfully created menu with ID: {menu_id}")
        return ok({"id": menu_id, "message": "Menu created successfully"}, 201)
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
        - image_url: URL to image
        - description: Menu description
        - cooking_instructions: How to cook
        - cooking_time_minutes: Time in minutes
        - target_role: IBU, ANAK, or ALL
        - is_active: Whether menu is active
        - ingredients: List of {ingredient_id, quantity_g, display_quantity} (replaces all)
        - nutrition_is_manual: Use manual nutrition values
        - serving_unit: Unit of serving
        - manual_calories: Manual calorie value
        - manual_protein_g: Manual protein value
        - manual_carbs_g: Manual carbs value
        - manual_fat_g: Manual fat value
    """
    # Validate input
    data, errors = validate_schema(UpdateMenuSchema, json_body(), partial=True)
    if errors:
        return error("VALIDATION_ERROR", "Invalid input data", 400, details=errors)
    
    # Debug logging
    print(f"[UPDATE MENU] Menu ID: {menu_id}")
    print(f"[UPDATE MENU] Received data: {data}")
    
    try:
        success = update_menu(
            menu_id=menu_id,
            name=data.get("name"),
            meal_type=data.get("meal_type"),
            tags=data.get("tags"),
            image_url=data.get("image_url"),
            description=data.get("description"),
            cooking_instructions=data.get("cooking_instructions"),
            cooking_time_minutes=data.get("cooking_time_minutes"),
            target_role=data.get("target_role"),
            is_active=data.get("is_active"),
            ingredients=data.get("ingredients"),
            nutrition_is_manual=data.get("nutrition_is_manual"),
            serving_unit=data.get("serving_unit"),
            manual_calories=data.get("manual_calories"),
            manual_protein_g=data.get("manual_protein_g"),
            manual_carbs_g=data.get("manual_carbs_g"),
            manual_fat_g=data.get("manual_fat_g")
        )
        
        if not success:
            return error("NOT_FOUND", "Menu not found", 404)
        
        print(f"[UPDATE MENU] Successfully updated menu ID: {menu_id}")
        return ok({"id": menu_id, "message": "Menu updated successfully"})
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)



def delete_menu_handler(menu_id: int):
    """Delete a menu and its associated ingredients."""
    try:
        success = delete_menu(menu_id)
        
        if not success:
            return error("NOT_FOUND", "Menu not found", 404)
        
        return ok({"message": "Menu deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def get_menu_detail_handler(menu_id: int):
    """Get detailed information about a menu including its ingredients."""
    try:
        menu_detail = get_menu_detail(menu_id)
        
        if not menu_detail:
            return error("NOT_FOUND", "Menu not found", 404)
        
        return ok(menu_detail)
    except Exception as e:
        return error("UNKNOWN_ERROR", str(e), 500)
