from enum import Enum

class UserRole(str, Enum):
    IBU_HAMIL = "IBU_HAMIL"
    IBU_MENYUSUI = "IBU_MENYUSUI"
    ANAK_BATITA = "ANAK_BATITA"
    ANAK_BALITA = "ANAK_BALITA" # Keep for compatibility if needed

class TargetRole(str, Enum):
    IBU = "IBU"
    ANAK_6_8 = "ANAK_6_8"
    ANAK_9_11 = "ANAK_9_11"
    ANAK_12_23 = "ANAK_12_23"

class MealType(str, Enum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"

class LactationPhase(str, Enum):
    PHASE_0_6 = "0-6"
    PHASE_6_12 = "6-12"
