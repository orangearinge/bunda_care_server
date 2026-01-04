"""
Food Scan Service

Handles food scanning and ingredient detection using AI.
"""

from typing import Dict, Any

from app.extensions import db
from app.utils.ai import recognize
from app.models.ingredient import FoodIngredient
from app.services.food_helpers import normalize_name
from app.services.food_constants import DEFAULT_TOP_CANDIDATES


def score_ingredient_match(
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
    

    
    # Apply confidence factor
    score = score * (0.5 + confidence)
    
    return score


def build_candidate_from_ingredient(
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


def scan_food_image(image) -> Dict[str, Any]:
    """
    Scan food image and return ingredient candidates.
    
    Uses AI to recognize food items in the image and matches them
    against the ingredient database.
    
    Args:
        image: Image file to scan
        
    Returns:
        Dictionary with candidates and detected_ids
    """
    # Get AI recognition results
    labels = recognize(image)
    label_names = [
        str(label.get("label", "")).strip().lower() 
        for label in labels 
        if label.get("label")
    ]
    
    if not label_names:
        return {"candidates": [], "detected_ids": []}
    
    # Query ingredients that might match
    # Use individual words for broader search coverage
    search_terms = set()
    for name in label_names:
        search_terms.add(name)
        # Split Label into individual words (e.g., 'daging ayam' -> 'daging', 'ayam')
        for word in name.split():
            if len(word) > 2: # Ignore very short words
                search_terms.add(word)

    like_patterns = [f"%{term}%" for term in search_terms]
    or_clauses = [
        clause 
        for pattern in like_patterns 
        for clause in (
            FoodIngredient.name.ilike(pattern),
            FoodIngredient.alt_names.ilike(pattern)
        )
    ]
    
    ingredients = FoodIngredient.query.filter(db.or_(*or_clauses)).limit(50).all()
    
    # Score and rank candidates for each detected label
    candidates = []
    
    for label in labels:
        label_text = label["label"].lower()
        confidence = float(label.get("confidence", 0) or 0)
        
        # Score all ingredients for this label and filter out non-matches
        scored = [
            (score_ingredient_match(label_text, ing, confidence), ing)
            for ing in ingredients
        ]
        # Only keep candidates with actual match score > 0
        scored = [s for s in scored if s[0] > 0]
        
        # Sort by score (descending)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Take top N candidates
        for _, ingredient in scored[:DEFAULT_TOP_CANDIDATES]:
            candidates.append(build_candidate_from_ingredient(ingredient, confidence))
    
    # Deduplicate - keep highest confidence for each ingredient
    deduped = {}
    for candidate in candidates:
        ingredient_id = candidate["ingredient_id"]
        if (ingredient_id not in deduped or 
            candidate["confidence"] > deduped[ingredient_id]["confidence"]):
            deduped[ingredient_id] = candidate
    
    return {
        "candidates": list(deduped.values()),
        "detected_ids": [c["ingredient_id"] for c in deduped.values()],
    }
