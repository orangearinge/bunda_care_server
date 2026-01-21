"""
Meal Log Service

Handles meal logging operations including creation and retrieval.
"""

from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import desc

from app.extensions import db
from app.models.ingredient import FoodIngredient
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient
from app.models.meal_log import FoodMealLog, FoodMealLogItem
from app.services.food_helpers import serialize_nutrition
from app.utils.http import parse_iso_datetime


def create_meal_log(
    user_id: int,
    menu_id: int,
    servings: float,
    logged_at: datetime = None,
    is_consumed: bool = False
) -> Dict[str, Any]:
    """
    Create a meal log entry from a menu.
    
    Args:
        user_id: User ID
        menu_id: Menu ID to log
        servings: Number of servings 
        logged_at: Timestamp of the meal
        
    Returns:
        Dictionary with meal log details
        
    Raises:
        ValueError: If menu not found or has no ingredients
        Exception: For database errors
    """
    # Validate menu exists
    menu = FoodMenu.query.get(menu_id)
    if not menu:
        raise ValueError("MENU_NOT_FOUND: menu_id does not exist")
    
    # Get menu ingredients
    compositions = FoodMenuIngredient.query.filter_by(menu_id=menu_id).all()
    if not compositions:
        raise ValueError("MENU_EMPTY: No ingredients for the specified menu_id")
    
    ingredient_map = {ing.id: ing for ing in FoodIngredient.query.all()}
    
    # Calculate totals
    total = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    items_payload = []
    
    for composition in compositions:
        ingredient = ingredient_map.get(composition.ingredient_id)
        if not ingredient:
            continue
        
        # Use 0 as fallback if quantity_g is null (e.g. for display-only ingredients)
        quantity = float(composition.quantity_g or 0) * float(servings)
        nutrition = serialize_nutrition(ingredient, quantity)
        
        total["calories"] += nutrition["calories"]
        total["protein_g"] += nutrition["protein_g"]
        total["carbs_g"] += nutrition["carbs_g"]
        total["fat_g"] += nutrition["fat_g"]
        
        items_payload.append((ingredient.id, quantity, nutrition))
    
    # Create meal log
    if logged_at is None:
        logged_at = datetime.utcnow()
    
    meal_log = FoodMealLog(
        user_id=user_id,
        menu_id=menu_id,
        total_calories=int(total["calories"]),
        total_protein_g=float(total["protein_g"]),
        total_carbs_g=float(total["carbs_g"]),
        total_fat_g=float(total["fat_g"]),
        servings=float(servings),
        is_consumed=is_consumed,
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
    
    return {
        "meal_log_id": meal_log.id,
        "menu_id": menu_id,
        "menu_name": menu.name,
        "image_url": menu.image_url,
        "servings": float(servings),
        "is_consumed": is_consumed,
        "logged_at": meal_log.logged_at.isoformat() if meal_log.logged_at else None,
        "total": total,
        "items": [
            {"ingredient_id": iid, "quantity_g": float(qty), **nutr} 
            for iid, qty, nutr in items_payload
        ]
    }


def list_meal_logs(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    List meal logs for a user.
    
    Args:
        user_id: User ID
        limit: Maximum number of logs to return
        
    Returns:
        List of meal log dictionaries
    """
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
            "image_url": menu.image_url if menu else None,
            "servings": float(log.servings),
            "is_consumed": log.is_consumed,
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
    
    return payload


def confirm_meal_consumed(user_id: int, meal_log_id: int) -> bool:
    """Mark a meal log as consumed."""
    log = FoodMealLog.query.filter_by(id=meal_log_id, user_id=user_id).first()
    if not log:
        return False
    
    log.is_consumed = True
    db.session.commit()
    return True
