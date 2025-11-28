"""
Nutrition Service

Handles nutritional calculations and targets based on user preferences and roles.
"""

from typing import Dict, Any, Tuple
from flask import request

from app.models.preference import UserPreference
from app.services.food_constants import (
    CALORIES_PER_GRAM_CARBS,
    CALORIES_PER_GRAM_FAT,
    DEFAULT_CALORIE_TARGET,
    DEFAULT_MIN_PROTEIN_G,
    DEFAULT_CARBS_PERCENTAGE,
    DEFAULT_FAT_PERCENTAGE,
    FIRST_TRIMESTER_WEEKS,
    SECOND_TRIMESTER_WEEKS
)


def calculate_nutritional_targets(preference: UserPreference) -> Dict[str, Any]:
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
        calorie_target, protein_g = calculate_pregnant_targets(preference, weight)
    elif role == "IBU_MENYUSUI":
        calorie_target, protein_g = calculate_lactating_targets(preference, weight)
    elif role == "ANAK_BALITA":
        calorie_target, protein_g = calculate_toddler_targets(weight)
        fat_percentage = 0.35
    
    return {
        "calories": calorie_target,
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carbs_percentage * calorie_target / CALORIES_PER_GRAM_CARBS, 1),
        "fat_g": round(fat_percentage * calorie_target / CALORIES_PER_GRAM_FAT, 1),
        "bmi": round(bmi, 1) if bmi else None,
    }


def calculate_pregnant_targets(
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


def calculate_lactating_targets(
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


def calculate_toddler_targets(weight: float) -> Tuple[int, float]:
    """Calculate calorie and protein targets for toddlers."""
    default_weight = weight or 12
    calorie_target = int(max(900, min(1400, 90 * default_weight)))
    protein_g = max(20.0, 1.1 * default_weight)
    
    return calorie_target, protein_g
