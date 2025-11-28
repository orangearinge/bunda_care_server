"""
Menu Service

Handles menu CRUD operations.
"""

from typing import Dict, Any, List, Optional
from flask import request

from app.extensions import db
from app.models.ingredient import FoodIngredient  
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient
from app.services.food_constants import MEAL_TYPES
from app.utils.http import arg_int


def list_menus(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    meal_type: Optional[str] = None,
    is_active: Optional[bool] = None
) -> Dict[str, Any]:
    """
    List menus with search, filter, and pagination.
    
    Args:
        page: Page number
        limit: Items per page
        search: Search term for name or tags
        meal_type: Filter by meal type
        is_active: Filter by active status
        
    Returns:
        Dictionary with items, pagination info
    """
    query = FoodMenu.query
    
    # Apply filters
    if search:
        term = f"%{search}%"
        query = query.filter(db.or_(
            FoodMenu.name.ilike(term),
            FoodMenu.tags.ilike(term)
        ))
    
    if meal_type and meal_type.upper() in MEAL_TYPES:
        query = query.filter(FoodMenu.meal_type == meal_type.upper())
        
    if is_active is not None:
        query = query.filter(FoodMenu.is_active == is_active)
        
    # Order by
    query = query.order_by(FoodMenu.meal_type, FoodMenu.name)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    menus = pagination.items
    menu_ids = [menu.id for menu in menus]
    
    # Get all menu ingredients for the current page
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
    
    return {
        "items": data,
        "total": pagination.total,
        "page": page,
        "limit": limit,
        "pages": pagination.pages
    }


def get_menu_detail(menu_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a menu including its ingredients.
    
    Args:
        menu_id: Menu ID
        
    Returns:
        Menu details dictionary or None if not found
    """
    menu = FoodMenu.query.get(menu_id)
    if not menu:
        return None
    
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
    
    return {
        "id": menu.id,
        "name": menu.name,
        "meal_type": menu.meal_type,
        "tags": menu.tags,
        "is_active": menu.is_active,
        "ingredients": ingredients
    }


def create_menu(
    name: str,
    meal_type: str,
    tags: str = "",
    is_active: bool = True,
    ingredients: List[Dict] = None
) -> int:
    """
    Create a new menu with ingredients.
    
    Args:
        name: Menu name
        meal_type: BREAKFAST/LUNCH/DINNER
        tags: Comma-separated tags
        is_active: Whether menu is active
        ingredients: List of {ingredient_id, quantity_g}
        
    Returns:
        New menu ID
        
    Raises:
        Exception: For database errors
    """
    if ingredients is None:
        ingredients = []
    
    # Create menu
    menu = FoodMenu(
        name=name,
        meal_type=meal_type.upper(),
        tags=tags,
        is_active=is_active
    )
    db.session.add(menu)
    db.session.flush()
    
    # Add ingredients
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
    return menu.id


def update_menu(
    menu_id: int,
    name: Optional[str] = None,
    meal_type: Optional[str] = None,
    tags: Optional[str] = None,
    is_active: Optional[bool] = None,
    ingredients: Optional[List[Dict]] = None
) -> bool:
    """
    Update an existing menu.
    
    Args:
        menu_id: Menu ID
        name: Menu name
        meal_type: BREAKFAST/LUNCH/DINNER
        tags: Comma-separated tags
        is_active: Whether menu is active
        ingredients: List of {ingredient_id, quantity_g} (replaces all)
        
    Returns:
        True if successful, False if menu not found
        
    Raises:
        Exception: For database errors
    """
    menu = FoodMenu.query.get(menu_id)
    if not menu:
        return False
    
    # Update fields if provided
    if name is not None:
        menu.name = name
    if meal_type is not None:
        menu.meal_type = meal_type.upper()
    if tags is not None:
        menu.tags = tags
    if is_active is not None:
        menu.is_active = is_active
    
    # Update ingredients if provided
    if ingredients is not None:
        # Delete existing ingredients
        FoodMenuIngredient.query.filter_by(menu_id=menu_id).delete()
        
        # Add new ingredients
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
    return True


def delete_menu(menu_id: int) -> bool:
    """
    Delete a menu and its associated ingredients.
    
    Args:
        menu_id: Menu ID
        
    Returns:
        True if successful, False if menu not found
        
    Raises:
        Exception: For database errors
    """
    menu = FoodMenu.query.get(menu_id)
    if not menu:
        return False
    
    # Delete menu ingredients first
    FoodMenuIngredient.query.filter_by(menu_id=menu_id).delete()
    
    # Delete menu
    db.session.delete(menu)
    db.session.commit()
    
    return True
