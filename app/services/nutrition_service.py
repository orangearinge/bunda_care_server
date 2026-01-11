"""
Nutrition Service

Handles nutritional calculations and targets based on user preferences and roles.
"""

from typing import Dict, Any, Tuple
from datetime import date
from flask import request

from app.models.preference import UserPreference
from app.services.food_constants import (
    CALORIES_PER_GRAM_CARBS,
    CALORIES_PER_GRAM_FAT,
    AKG_BASE,
    PREGNANCY_INCREMENTS,
    AKG_TAMBAHAN_MENYUSUI,
    DEFAULT_CALORIE_TARGET,
    DEFAULT_MIN_PROTEIN_G,
    DEFAULT_CARBS_PERCENTAGE,
    DEFAULT_FAT_PERCENTAGE,
    FIRST_TRIMESTER_WEEKS,
    SECOND_TRIMESTER_WEEKS
)


def get_base_akg(age_year: int) -> Dict[str, Any]:
    """Get base AKG values based on age."""
    if not age_year:
        return AKG_BASE["19-29"]
    
    if age_year < 30:
        return AKG_BASE["19-29"]
    elif age_year < 50:
        return AKG_BASE["30-49"]
    elif age_year < 65:
        return AKG_BASE["50-64"]
    elif age_year < 80:
        return AKG_BASE["65-80"]
    else:
        return AKG_BASE["80+"]


def calculate_nutritional_targets(preference: UserPreference) -> Dict[str, Any]:
    """
    Calculate nutritional targets based on user role and preferences.
    
    Args:
        preference: User preference object
        
    Returns:
        Dictionary with calorie and macronutrient targets
    """
    role = (preference.role or "").upper()
    height_m = (float(preference.height_cm or 0) / 100.0) if preference.height_cm else 0.0
    weight = float(preference.weight_kg or 0)
    bmi = (weight / (height_m * height_m)) if height_m > 0 else None
    
    # Get base values from AKG table
    base = get_base_akg(preference.age_year)
    calorie_target = base["energy"]
    protein_g = base["protein"]
    fat_g = base["fat"]
    carbs_g = base["carbs"]
    
    # Role-specific adjustments
    if role == "IBU_HAMIL":
        targets = calculate_pregnant_targets(preference, base)
        calorie_target = targets["energy"]
        protein_g = targets["protein"]
        fat_g = targets["fat"]
        carbs_g = targets["carbs"]
    elif role == "IBU_MENYUSUI":
        targets = calculate_lactating_targets(preference, base)
        calorie_target = targets["energy"]
        protein_g = targets["protein"]
        fat_g = targets["fat"]
        carbs_g = targets["carbs"]
    elif role == "ANAK_BATITA":
        calorie_target, protein_g = calculate_infant_targets(preference, weight)
        # Infant solid food targets
        fat_percentage = 0.45
        carbs_g = (1.0 - fat_percentage - 0.15) * calorie_target / CALORIES_PER_GRAM_CARBS # simple estimate
        fat_g = fat_percentage * calorie_target / CALORIES_PER_GRAM_FAT
    
    return {
        "calories": int(calorie_target),
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carbs_g, 1),
        "fat_g": round(fat_g, 1),
        "bmi": round(bmi, 1) if bmi else None,
    }


def calculate_pregnant_targets(
    preference: UserPreference,
    base: Dict[str, Any]
) -> Dict[str, float]:
    """Calculate calorie and macronutrient targets for pregnant women based on table."""
    gestational_age = preference.gestational_age_weeks or 0
    
    # Determine trimester
    if gestational_age < FIRST_TRIMESTER_WEEKS:
        trimester = 1
    elif gestational_age < SECOND_TRIMESTER_WEEKS:
        trimester = 2
    else:
        trimester = 3
        
    increment = PREGNANCY_INCREMENTS[trimester]
    
    energy = base["energy"] + increment["energy"]
    protein = base["protein"] + increment["protein"]
    fat = base["fat"] + increment["fat"]
    carbs = base["carbs"] + increment["carbs"]
    
    # LILA (mid-upper arm circumference) adjustment for undernutrition (KEK)
    try:
        lila_cm = float(preference.lila_cm or 0)
        if lila_cm and lila_cm < 23.5:
            # Special boost for KEK (Chronic Energy Deficiency)
            energy += 200
            protein += 10 # Adding roughly 10g protein for KEK
    except (ValueError, TypeError):
        pass
    
    return {
        "energy": energy,
        "protein": protein,
        "fat": fat,
        "carbs": carbs
    }

def calculate_lactating_targets(
    preference: UserPreference,
    base: Dict[str, Any]
) -> Dict[str, float]:
    """Calculate calorie and macronutrient targets for lactating women."""
    # Use lactation_phase from preference ("0-6" or "6-12")
    # Default to "0-6" if not set
    period = preference.lactation_phase or "0-6"
    
    # Ensure period is valid, fallback to "0-6"
    if period not in AKG_TAMBAHAN_MENYUSUI:
        period = "0-6"
        
    increment = AKG_TAMBAHAN_MENYUSUI[period]
    
    energy = base["energy"] + increment["energy"]
    protein = base["protein"] + increment["protein"]
    fat = base["fat"] + increment["fat"]
    carbs = base["carbs"] + increment["carbs"]
    
    return {
        "energy": energy,
        "protein": protein,
        "fat": fat,
        "carbs": carbs
    }



def calculate_infant_targets(
    preference: UserPreference,
    weight: float
) -> Tuple[int, float]:
    """Calculate calorie and protein targets for infants 0-24 months."""
    # Calculate age in months
    age_months = (preference.age_year or 0) * 12
    
    if age_months <= 6:
        # 0-6 months: primarily milk feeding
        calorie_target = int(max(500, min(750, 100 * weight)))
        protein_g = max(9.0, 1.5 * weight)
    else:
        # 7-24 months: introducing solid foods
        calorie_target = int(max(750, min(1200, 85 * weight)))
        protein_g = max(14.0, 1.2 * weight)
    
    return calorie_target, protein_g
