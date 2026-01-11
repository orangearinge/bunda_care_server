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
    AKG_CHILD_BASE,
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
    """Get base AKG values based on age for adults."""
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


def get_child_base_akg(age_year: int, age_month: int = None) -> Dict[str, Any]:
    """Get base AKG values for children 0-3 years."""
    if age_year and age_year >= 1:
        # 1-3 years
        return AKG_CHILD_BASE["1-3y"]
    
    # Below 1 year, use months
    months = age_month if age_month is not None else 6  # Fallback to 6 months if month not provided
    
    if months <= 5:
        return AKG_CHILD_BASE["0-5m"]
    else:
        return AKG_CHILD_BASE["6-11m"]


def get_calibrated_base(preference: UserPreference, base: Dict[str, Any], is_child: bool = False) -> Dict[str, float]:
    """
    Calibrate base AKG values based on weight ratio.
    """
    weight = float(preference.weight_kg or 0)
    height = float(preference.height_cm or 0)
    ref_bb = float(base.get("ref_bb", 55))
    
    print(f"DEBUG NUTRITION: Role={'Child' if is_child else 'Woman'}, User Weight={weight}, Height={height}, Ref BB={ref_bb}")
    
    if not weight or not ref_bb:
        return {k: float(v) for k, v in base.items() if isinstance(v, (int, float))}

    calc_weight = weight
    
    # Only apply BMI-based truncation for adults
    if not is_child:
        height_m = height / 100.0
        bmi = (weight / (height_m * height_m)) if height_m > 0 else 22.0
        
        if bmi > 25.0 and height > 100:
            # Use Adjusted Body Weight for overweight adults
            bbi = (height - 100) * 0.9
            calc_weight = bbi + 0.25 * (weight - bbi)
            print(f"DEBUG NUTRITION: BMI={bmi} (>25), Adjusted Weight={calc_weight}")
    
    ratio = calc_weight / ref_bb
    print(f"DEBUG NUTRITION: Final Ratio={ratio}")
    
    # Bound the ratio
    ratio = max(0.7, min(1.5, ratio))
    
    return {
        "energy": base["energy"] * ratio,
        "protein": base["protein"] * ratio,
        "fat": base["fat"] * ratio,
        "carbs": base["carbs"] * ratio
    }


def calculate_nutritional_targets(preference: UserPreference) -> Dict[str, Any]:
    """
    Calculate nutritional targets based on user role and preferences.
    """
    role = (preference.role or "").upper()
    height_m = (float(preference.height_cm or 0) / 100.0) if preference.height_cm else 0.0
    weight = float(preference.weight_kg or 0)
    bmi = (weight / (height_m * height_m)) if height_m > 0 else None
    
    # Get base values and calibrate
    if role == "ANAK_BATITA":
        raw_base = get_child_base_akg(preference.age_year, preference.age_month)
        base = get_calibrated_base(preference, raw_base, is_child=True)
    else:
        raw_base = get_base_akg(preference.age_year)
        base = get_calibrated_base(preference, raw_base, is_child=False)

    calorie_target = base["energy"]
    protein_g = base["protein"]
    fat_g = base["fat"]
    carbs_g = base["carbs"]
    
    # Role-specific increments (pregnant/lactating)
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




