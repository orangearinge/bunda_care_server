# from flask import request
# from app.extensions import db
# from app.models.preference import UserPreference
# from app.models.user import User
# from app.models.role import Role
# from app.utils.auth import create_token
# from app.utils.http import ok, error, json_body

# def upsert_preference_handler():
#     user_id = request.user_id
#     body = json_body()

#     # Ambil atau buat UserPreference baru
#     pref = UserPreference.query.get(user_id)
#     if not pref:
#         pref = UserPreference(
#             user_id=user_id,
#             role=body.get("role") or request.user_role or "IBU_HAMIL"
#         )
#         db.session.add(pref)
        
#     for f in [
#         "role","height_cm","weight_kg","age_year","hpht",
#         "belly_circumference_cm","lila_cm","lactation_ml",
#         "food_prohibitions","allergens","calorie_target"
#     ]:
#         if f in body:
#             setattr(pref, f, body[f])

#     # Validasi berdasarkan role
#     current_role = str((body.get("role") or pref.role or "")).upper()
#     if current_role in {"IBU_HAMIL", "IBU_MENYUSUI", "ANAK_BALITA"}:
#         required_by_role = {
#             "IBU_HAMIL": [
#                 "weight_kg", "height_cm", "age_year",
#                 "hpht", "belly_circumference_cm", "lila_cm"
#             ],
#             "IBU_MENYUSUI": [
#                 "weight_kg", "height_cm", "age_year", "lactation_ml"
#             ],
#             "ANAK_BALITA": [
#                 "weight_kg", "height_cm", "age_year"
#             ],
#         }

#         missing = []
#         for key in required_by_role[current_role]:
#             val = getattr(pref, key, None)
#             if val is None or (
#                 isinstance(val, (int, float)) and float(val) == 0.0
#             ):
#                 missing.append(key)

#         if missing:
#             return error(
#                 "VALIDATION_ERROR",
#                 f"Missing required fields for {current_role}: {', '.join(missing)}",
#                 400
#             )

#     # Validasi role & update user table
#     role_name = body.get("role")
#     if role_name:
#         role_obj = Role.query.filter(
#             db.func.upper(Role.name) == str(role_name).upper()
#         ).first()

#         if not role_obj:
#             return error("ROLE_NOT_FOUND", f"Role '{role_name}' not found", 400)

#         pref.role = role_obj.name

#         user = User.query.get(user_id)
#         if user and user.role_id != role_obj.id:
#             user.role_id = role_obj.id

#     db.session.commit()

#     # Response
#     resp = {
#         "user_id": user_id,
#         "role": pref.role,
#         "height_cm": pref.height_cm,
#         "weight_kg": float(pref.weight_kg) if pref.weight_kg is not None else None,
#         "age_year": pref.age_year,
#         "hpht": pref.hpht,
#         "belly_circumference_cm": pref.belly_circumference_cm,
#         "lila_cm": pref.lila_cm,
#         "lactation_ml": pref.lactation_ml,
#         "food_prohibitions": pref.food_prohibitions or [],
#         "allergens": pref.allergens or [],
#         "calorie_target": pref.calorie_target,
#         "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
#     }

#     if role_name:
#         resp["token"] = create_token(user_id, pref.role)

#     return ok(resp)




from datetime import datetime
from flask import request
from app.extensions import db
from app.models.preference import UserPreference
from app.models.user import User
from app.models.role import Role
from app.utils.auth import create_token
from app.utils.http import ok, error, json_body
from app.services.nutrition_service import calculate_nutritional_targets


def upsert_preference_handler():
    user_id = request.user_id
    body = json_body()

    # --- STEP 1: GET OR CREATE USER PREFERENCE ---
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    is_new = False

    if not pref:
        is_new = True
        default_role = body.get("role") or request.user_role or "IBU_HAMIL"
        pref = UserPreference(user_id=user_id, role=default_role.upper())
        db.session.add(pref)

    # --- STEP 2: UPDATE SIMPLE FIELDS TERLEBIH DAHULU ---
    normal_fields = [
        "height_cm", "weight_kg", "age_year",
        "belly_circumference_cm", "lila_cm", "lactation_ml"
    ]

    for field in normal_fields:
        if field in body:
            setattr(pref, field, body[field])

    # Special handling for hpht (date)
    if "hpht" in body:
        val = body["hpht"]
        if val:
            try:
                # Expecting YYYY-MM-DD or date object
                if isinstance(val, str):
                    pref.hpht = datetime.strptime(val, "%Y-%m-%d").date()
                else:
                    pref.hpht = val
            except (ValueError, TypeError):
                return error("INVALID_FORMAT", "hpht must be in YYYY-MM-DD format", 400)
        else:
            pref.hpht = None

    # --- STEP 3: HANDLE ARRAY FIELDS (PASTIKAN SELALU LIST) ---
    list_fields = ["food_prohibitions", "allergens"]

    for field in list_fields:
        if field in body:
            val = body[field]
            if isinstance(val, list):
                setattr(pref, field, val)
            elif val in (None, "", " ", []):
                setattr(pref, field, [])
            else:
                return error("INVALID_FORMAT", f"'{field}' must be a list", 400)

    # --- STEP 4: ROLE UPDATE (HANYA JIKA ADA DI BODY) ---
    incoming_role = body.get("role")
    role_changed = False

    if incoming_role:
        role_obj = Role.query.filter(
            db.func.upper(Role.name) == incoming_role.upper()
        ).first()

        if not role_obj:
            return error("ROLE_NOT_FOUND", f"Role '{incoming_role}' not found", 400)

        # Role valid → assign
        incoming_role = role_obj.name.upper()

        if pref.role != incoming_role:
            pref.role = incoming_role
            role_changed = True

        # Update user.role_id jika berbeda
        user = User.query.get(user_id)
        if user and user.role_id != role_obj.id:
            user.role_id = role_obj.id

    # Role final setelah update
    current_role = pref.role.upper()

    # --- STEP 5: ROLE VALIDATION ---
    ROLE_REQUIREMENTS = {
        "IBU_HAMIL": [
            "weight_kg", "height_cm", "age_year",
            "hpht", "belly_circumference_cm", "lila_cm"
        ],
        "IBU_MENYUSUI": [
            "weight_kg", "height_cm", "age_year", "lactation_ml"
        ],
        "ANAK_BALITA": [
            "weight_kg", "height_cm", "age_year"
        ],
    }

    if current_role in ROLE_REQUIREMENTS:
        missing = []
        for key in ROLE_REQUIREMENTS[current_role]:
            val = getattr(pref, key, None)
            if val is None:
                missing.append(key)

        if missing:
            return error(
                "VALIDATION_ERROR",
                f"Missing required fields for {current_role}: {', '.join(missing)}",
                400
            )

    # --- STEP 6: COMMIT ---
    db.session.commit()

    # Calculate nutritional targets to return in response
    targets = calculate_nutritional_targets(pref)

    # --- STEP 7: RESPONSE ---
    response = {
        "user_id": user_id,
        "role": pref.role,
        "height_cm": pref.height_cm,
        "weight_kg": pref.weight_kg,
        "age_year": pref.age_year,
        "hpht": pref.hpht.isoformat() if pref.hpht else None,
        "gestational_age_weeks": pref.gestational_age_weeks,
        "belly_circumference_cm": pref.belly_circumference_cm,
        "lila_cm": pref.lila_cm,
        "lactation_ml": pref.lactation_ml,
        "food_prohibitions": pref.food_prohibitions or [],
        "allergens": pref.allergens or [],
        "calorie_target": targets["calories"],
        "nutritional_targets": targets,
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
    }

    # Token hanya ketika role berubah
    if role_changed:
        response["token"] = create_token(user_id, pref.role)

    return ok(response)
