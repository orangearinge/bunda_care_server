"""
Food Service Constants

Contains all constants and configuration values used in food-related services.
"""

# Keywords for detecting raw ingredients
RAW_KEYWORDS = ["dada", "paha", "fillet", "kulit", "hati", "ati", "telur", "mentah", "raw"]

# Valid meal types
MEAL_TYPES = ["BREAKFAST", "LUNCH", "DINNER"]

# Nutrition calculation constants
CALORIES_PER_GRAM_CARBS = 4.0
CALORIES_PER_GRAM_FAT = 9.0

# Default nutritional targets
DEFAULT_CALORIE_TARGET = 2000
DEFAULT_MIN_PROTEIN_G = 50.0
DEFAULT_CARBS_PERCENTAGE = 0.5
DEFAULT_FAT_PERCENTAGE = 0.3

# Scoring and boost defaults
DEFAULT_TOP_CANDIDATES = 3
DEFAULT_OPTIONS_PER_MEAL = 3
DEFAULT_BOOST_PER_HIT = 400
DEFAULT_BOOST_PER_100G = 5
DEFAULT_MIN_HITS = 1

# Gestational age thresholds (weeks)
FIRST_TRIMESTER_WEEKS = 13
SECOND_TRIMESTER_WEEKS = 28
