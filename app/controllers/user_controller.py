from flask import request
from app.extensions import db
from app.models.preference import UserPreference
from app.models.user import User
from app.models.role import Role
from app.utils.auth import create_token
from app.utils.http import ok, error, json_body

def upsert_preference_handler():
    user_id = request.user_id
    body = json_body()

    pref = UserPreference.query.get(user_id)
    if not pref:
        pref = UserPreference(user_id=user_id, role=body.get("role") or request.user_role or "IBU_HAMIL")
        db.session.add(pref)

    # Alias support: allow 'larangan_makanan' or legacy 'dietary_restrictions' as input for food_prohibitions
    if "food_prohibitions" not in body:
        if "larangan_makanan" in body:
            body["food_prohibitions"] = body.get("larangan_makanan")
        elif "dietary_restrictions" in body:
            body["food_prohibitions"] = body.get("dietary_restrictions")

    for f in [
        "role","height_cm","weight_kg","age_year","gestational_age_week",
        "belly_circumference_cm","lila_cm","lactation_ml","food_prohibitions","allergens","calorie_target"
    ]:
        if f in body:
            setattr(pref, f, body[f])

    # Determine current role to validate fields
    current_role = str((body.get("role") or pref.role or "")).upper()
    if current_role in {"IBU_HAMIL", "IBU_MENYUSUI", "ANAK_BALITA"}:
        required_by_role = {
            # Ibu Hamil: IMT (berat & tinggi), usia ibu, usia kandungan, lingkar perut, LILA
            "IBU_HAMIL": [
                "weight_kg", "height_cm", "age_year", "gestational_age_week", "belly_circumference_cm", "lila_cm"
            ],
            # Ibu Menyusui: usia ibu, IMT (berat & tinggi), produksi ASI harian
            "IBU_MENYUSUI": [
                "weight_kg", "height_cm", "age_year", "lactation_ml"
            ],
            # Anak Balita: IMT (berat & tinggi), usia
            "ANAK_BALITA": ["weight_kg", "height_cm", "age_year"],
        }
        missing = []
        for key in required_by_role[current_role]:
            val = getattr(pref, key, None)
            if val is None or (isinstance(val, (int, float)) and float(val) == 0.0):
                missing.append(key)
        if missing:
            return error("VALIDATION_ERROR", f"Missing required fields for {current_role}: {', '.join(missing)}", 400)

    role_name = body.get("role")
    if role_name:
        role_obj = Role.query.filter(db.func.upper(Role.name) == str(role_name).upper()).first()
        if not role_obj:
            return error("ROLE_NOT_FOUND", f"Role '{role_name}' not found", 400)
        pref.role = role_obj.name
        user = User.query.get(user_id)
        if user and user.role_id != role_obj.id:
            user.role_id = role_obj.id

    db.session.commit()

    resp = {
        "user_id": user_id,
        "role": pref.role,
        "height_cm": pref.height_cm,
        "weight_kg": float(pref.weight_kg) if pref.weight_kg is not None else None,
        "age_year": pref.age_year,
        "gestational_age_week": pref.gestational_age_week,
        "belly_circumference_cm": pref.belly_circumference_cm,
        "lila_cm": pref.lila_cm,
        "lactation_ml": pref.lactation_ml,
        "larangan_makanan": pref.food_prohibitions or [],
        "food_prohibitions": pref.food_prohibitions or [],
        "allergens": pref.allergens or [],
        "calorie_target": pref.calorie_target,
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
    }
    if role_name:
        resp["token"] = create_token(user_id, pref.role)
    return ok(resp)
