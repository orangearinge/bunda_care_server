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
    target_role: Optional[str] = None,
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

    if target_role:
        target_role = target_role.upper()
        if target_role.startswith("ANAK_"):
            # If searching for specific child age, also show generic "ANAK" and "ALL"
            query = query.filter(db.or_(
                FoodMenu.target_role == target_role,
                FoodMenu.target_role == "ANAK",
                FoodMenu.target_role == "ALL"
            ))
        elif target_role == "ANAK":
            # If searching for generic child, show all child specific ones and "ALL"
            query = query.filter(db.or_(
                FoodMenu.target_role.like("ANAK%"),
                FoodMenu.target_role == "ALL"
            ))
        else:
            # For IBU or specific roles, show that and "ALL"
            query = query.filter(db.or_(
                FoodMenu.target_role == target_role,
                FoodMenu.target_role == "ALL"
            ))
        
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
            "image_url": menu.image_url,
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
    menu_ingredients = FoodMenuIngredient.query.filter_by(menu_id=menu_id).all()

    # Calculate nutrition
    nutrition = {
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
    }
    
    ingredients_list = []
    
    for menu_ingredient in menu_ingredients:
        ingredient = FoodIngredient.query.get(menu_ingredient.ingredient_id)
        if ingredient:
            qty = float(menu_ingredient.quantity_g)
            
            # Nutrition calc (assuming DB values are per 100g)
            ratio = qty / 100.0
            
            nutrition["calories"] += float(ingredient.calories) * ratio
            nutrition["protein_g"] += float(ingredient.protein_g) * ratio
            nutrition["carbs_g"] += float(ingredient.carbs_g) * ratio
            nutrition["fat_g"] += float(ingredient.fat_g) * ratio
            
            ingredients_list.append({
                "ingredient_id": ingredient.id,
                "name": ingredient.name,
                "quantity": qty, # Frontend expects 'quantity'
                "quantity_g": qty,
                "unit": "gram" # Default unit
            })
    
    return {
        "id": menu.id,
        "name": menu.name,
        "description": menu.description,
        "meal_type": menu.meal_type,
        "tags": menu.tags,
        "image_url": menu.image_url,
        "categories": [menu.meal_type], # Flutter might expect this or category
        "category": menu.meal_type,     # Matching Flutter model
        "cooking_instructions": menu.cooking_instructions,
        "cooking_time_minutes": menu.cooking_time_minutes,
        "is_active": menu.is_active,
        "nutrition": nutrition,
        "ingredients": ingredients_list
    }


def create_menu(
    name: str,
    meal_type: str,
    tags: str = "",
    image_url: Optional[str] = None,
    description: Optional[str] = None,
    cooking_instructions: Optional[str] = None,
    cooking_time_minutes: Optional[int] = None,
    target_role: str = "ALL",
    is_active: bool = True,
    ingredients: List[Dict] = None
) -> int:
    """
    Create a new menu with ingredients.
    
    Args:
        name: Menu name
        meal_type: BREAKFAST/LUNCH/DINNER
        tags: Comma-separated tags
        image_url: URL to image
        description: Menu description
        cooking_instructions: How to cook
        cooking_time_minutes: Time in minutes
        target_role: IBU, ANAK, or ALL
        is_active: Whether menu is active
        ingredients: List of {ingredient_id, quantity_g}
        
    Returns:
        New menu ID
        
    Raises:
        Exception: For database errors
    """
    if ingredients is None:
        ingredients = []
    
    print(f"[CREATE_MENU_SERVICE] Creating menu: {name}")
    print(f"[CREATE_MENU_SERVICE] image_url: {image_url}")
    print(f"[CREATE_MENU_SERVICE] ingredients: {ingredients}")
    
    # Create menu
    menu = FoodMenu(
        name=name,
        meal_type=meal_type.upper(),
        tags=tags,
        image_url=image_url,
        description=description,
        cooking_instructions=cooking_instructions,
        cooking_time_minutes=cooking_time_minutes,
        target_role=target_role.upper() if target_role else "ALL",
        is_active=is_active
    )
    db.session.add(menu)
    db.session.flush()
    
    print(f"[CREATE_MENU_SERVICE] Menu created with ID: {menu.id}, image_url: {menu.image_url}")
    
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
    print(f"[CREATE_MENU_SERVICE] Menu committed to database")
    return menu.id


def update_menu(
    menu_id: int,
    name: Optional[str] = None,
    meal_type: Optional[str] = None,
    tags: Optional[str] = None,
    image_url: Optional[str] = None,
    description: Optional[str] = None,
    cooking_instructions: Optional[str] = None,
    cooking_time_minutes: Optional[int] = None,
    target_role: Optional[str] = None,
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
        image_url: URL to image
        description: Menu description
        cooking_instructions: How to cook
        cooking_time_minutes: Time in minutes
        target_role: IBU, ANAK, or ALL
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
    if image_url is not None:
        menu.image_url = image_url
    if description is not None:
        menu.description = description
    if cooking_instructions is not None:
        menu.cooking_instructions = cooking_instructions
    if cooking_time_minutes is not None:
        menu.cooking_time_minutes = cooking_time_minutes
    if target_role is not None:
        menu.target_role = target_role.upper()
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
