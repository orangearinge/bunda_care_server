from flask import request
from sqlalchemy import or_
from app.extensions import db
from app.models.ingredient import FoodIngredient
from app.utils.http import ok, error, json_body, arg_int, validate_schema
from app.schemas.ingredient_schema import IngredientSchema, IngredientQuerySchema

def get_all_ingredients():
    """
    List ingredients with search and pagination.
    
    Query Parameters:
        - page: Page number (default: 1)
        - limit: Items per page (default: 10)
        - search: Search term for name or alternative names
    """
    query_data = {
        "page": request.args.get("page"),
        "limit": request.args.get("limit"),
        "search": request.args.get("search")
    }
    query_data = {k: v for k, v in query_data.items() if v is not None}
    
    data, errors = validate_schema(IngredientQuerySchema, query_data)
    if errors:
        return error("VALIDATION_ERROR", "Invalid query parameters", 400, details=errors)

    page = data["page"]
    limit = data["limit"]
    search = data.get("search")
    
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
    data, errors = validate_schema(IngredientSchema, json_body())
    if errors:
        return error("VALIDATION_ERROR", "Invalid input data", 400, details=errors)
    
    name = data["name"]
    
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
    
    data, errors = validate_schema(IngredientSchema, json_body(), partial=True)
    if errors:
        return error("VALIDATION_ERROR", "Invalid input data", 400, details=errors)
    
    if "name" in data:
        name = data["name"]
        existing = FoodIngredient.query.filter(FoodIngredient.name == name, FoodIngredient.id != id).first()
        if existing:
            return error("DUPLICATE_ENTRY", "Ingredient with this name already exists", 409)
        ing.name = name
    
    for field in ["alt_names", "calories", "protein_g", "carbs_g", "fat_g"]:
        if field in data:
            setattr(ing, field, data[field])


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
