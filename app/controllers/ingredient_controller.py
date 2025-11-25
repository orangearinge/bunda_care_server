from flask import request
from sqlalchemy import or_
from app.extensions import db
from app.models.ingredient import FoodIngredient
from app.utils.http import ok, error, json_body, arg_int

def get_all_ingredients():
    """
    List ingredients with search and pagination.
    
    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 10)
        - search: Search term for name or alternative names
    """
    page = arg_int("page", 1, min_value=1)
    limit = arg_int("limit", 10, min_value=1, max_value=100)
    search = (request.args.get("search") or "").strip()
    
    query = FoodIngredient.query
    
    # Apply search filter
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            FoodIngredient.name.ilike(term),
            FoodIngredient.alt_names.ilike(term)
        ))
    
    # Order by name
    query = query.order_by(FoodIngredient.name)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    # Build response
    data = []
    for ing in pagination.items:
        data.append({
            "id": ing.id,
            "name": ing.name,
            "alt_names": ing.alt_names,
            "calories": ing.calories,
            "protein_g": float(ing.protein_g),
            "carbs_g": float(ing.carbs_g),
            "fat_g": float(ing.fat_g)
        })
    
    return ok({
        "items": data,
        "total": pagination.total,
        "page": page,
        "limit": limit,
        "pages": pagination.pages
    })

def create_ingredient():
    data = json_body()
    name = (data.get("name") or "").strip()
    if not name:
        return error("VALIDATION_ERROR", "Name is required", 400)
    
    existing = FoodIngredient.query.filter_by(name=name).first()
    if existing:
        return error("DUPLICATE_ENTRY", "Ingredient with this name already exists", 409)

    try:
        ing = FoodIngredient(
            name=name,
            alt_names=data.get("alt_names", ""),
            calories=data.get("calories", 0),
            protein_g=data.get("protein_g", 0),
            carbs_g=data.get("carbs_g", 0),
            fat_g=data.get("fat_g", 0)
        )
        db.session.add(ing)
        db.session.commit()
        return ok({
            "id": ing.id,
            "name": ing.name,
            "alt_names": ing.alt_names,
            "calories": ing.calories,
            "protein_g": float(ing.protein_g),
            "carbs_g": float(ing.carbs_g),
            "fat_g": float(ing.fat_g)
        }, 201)
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)

def update_ingredient(id):
    ing = FoodIngredient.query.get(id)
    if not ing:
        return error("NOT_FOUND", "Ingredient not found", 404)
    
    data = json_body()
    name = (data.get("name") or "").strip()
    if name:
        existing = FoodIngredient.query.filter(FoodIngredient.name == name, FoodIngredient.id != id).first()
        if existing:
            return error("DUPLICATE_ENTRY", "Ingredient with this name already exists", 409)
        ing.name = name
    
    if "alt_names" in data:
        ing.alt_names = data["alt_names"]
    if "calories" in data:
        ing.calories = data["calories"]
    if "protein_g" in data:
        ing.protein_g = data["protein_g"]
    if "carbs_g" in data:
        ing.carbs_g = data["carbs_g"]
    if "fat_g" in data:
        ing.fat_g = data["fat_g"]

    try:
        db.session.commit()
        return ok({
            "id": ing.id,
            "name": ing.name,
            "alt_names": ing.alt_names,
            "calories": ing.calories,
            "protein_g": float(ing.protein_g),
            "carbs_g": float(ing.carbs_g),
            "fat_g": float(ing.fat_g)
        })
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)

def delete_ingredient(id):
    ing = FoodIngredient.query.get(id)
    if not ing:
        return error("NOT_FOUND", "Ingredient not found", 404)
    
    try:
        db.session.delete(ing)
        db.session.commit()
        return ok({"message": "Ingredient deleted"})
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)
