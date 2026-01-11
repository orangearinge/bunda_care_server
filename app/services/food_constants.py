"""
Food Service Constants

Contains all constants and configuration values used in food-related services.
"""



# Valid meal types
MEAL_TYPES = ["BREAKFAST", "LUNCH", "DINNER"]

# Nutrition calculation constants
CALORIES_PER_GRAM_CARBS = 4.0
CALORIES_PER_GRAM_FAT = 9.0

# Base AKG for infants/children (ref_bb: Berat Badan Referensi (kg), ref_tb: Tinggi Badan Referensi (cm))
# Values from image table
AKG_CHILD_BASE = {
    "0-5m": {"energy": 550, "protein": 9, "fat": 31, "carbs": 59, "ref_bb": 6, "ref_tb": 60},
    "6-11m": {"energy": 800, "protein": 15, "fat": 35, "carbs": 105, "ref_bb": 9, "ref_tb": 72},
    "1-3y": {"energy": 1350, "protein": 20, "fat": 45, "carbs": 215, "ref_bb": 13, "ref_tb": 92}
}

# Base AKG for women by age group (ref_bb: Berat Badan Referensi (kg), ref_tb: Tinggi Badan Referensi (cm))
# Values from image table
AKG_BASE = {
    "19-29": {"energy": 2250, "protein": 60, "fat": 65, "carbs": 360, "ref_bb": 55, "ref_tb": 159},
    "30-49": {"energy": 2150, "protein": 60, "fat": 60, "carbs": 340, "ref_bb": 56, "ref_tb": 158},
    "50-64": {"energy": 1800, "protein": 60, "fat": 50, "carbs": 280, "ref_bb": 56, "ref_tb": 158},
    "65-80": {"energy": 1550, "protein": 58, "fat": 45, "carbs": 230, "ref_bb": 53, "ref_tb": 157},
    "80+": {"energy": 1400, "protein": 58, "fat": 40, "carbs": 200, "ref_bb": 53, "ref_tb": 157}
}

# Pregnancy Increments (+an) from image table
PREGNANCY_INCREMENTS = {
    1: {"energy": 180, "protein": 1, "fat": 2.3, "carbs": 25}, # Trimester 1
    2: {"energy": 300, "protein": 10, "fat": 2.3, "carbs": 40}, # Trimester 2
    3: {"energy": 300, "protein": 30, "fat": 2.3, "carbs": 40}, # Trimester 3
}

# Lactation Increments (+an) from image table
AKG_TAMBAHAN_MENYUSUI = {
    "0-6": {"energy": 330, "protein": 20, "fat": 2.2, "carbs": 45}, # 6 bulan pertama
    "6-12": {"energy": 400, "protein": 15, "fat": 2.2, "carbs": 55}, # 6 bulan kedua
}

# Default nutritional targets (fallback)
DEFAULT_CALORIE_TARGET = 2150
DEFAULT_MIN_PROTEIN_G = 60.0
DEFAULT_CARBS_PERCENTAGE = 0.5
DEFAULT_FAT_PERCENTAGE = 0.3

# Scoring and boost defaults
DEFAULT_TOP_CANDIDATES = 1
DEFAULT_OPTIONS_PER_MEAL = 3
DEFAULT_BOOST_PER_HIT = 400
DEFAULT_BOOST_PER_100G = 5
DEFAULT_MIN_HITS = 1

# Gestational age thresholds (weeks)
FIRST_TRIMESTER_WEEKS = 13
SECOND_TRIMESTER_WEEKS = 28
