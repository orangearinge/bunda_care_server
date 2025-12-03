"""
Food Helper Functions

Contains utility functions for food-related operations including:
- Ingredient matching and normalization
- Nutritional calculations
- General helper functions
"""

from typing import Dict, Set
from flask import request

from app.models.ingredient import FoodIngredient



def normalize_name(ingredient: FoodIngredient) -> str:
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





def parse_detected_ids_from_query() -> Set[int]:
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


def parse_detected_ids_from_body(body: Dict) -> Set[int]:
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
