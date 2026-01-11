
from datetime import datetime, time
from flask import request
from app.extensions import db
from app.models.preference import UserPreference
from app.models.user import User
from app.models.role import Role
from app.models.meal_log import FoodMealLog
from app.models.menu import FoodMenu
from app.models.ingredient import FoodIngredient
from app.models.menu_ingredient import FoodMenuIngredient
from app.utils.auth import create_token
from app.utils.http import ok, error, json_body
from app.services.nutrition_service import calculate_nutritional_targets
from app.services.recommendation_service import generate_meal_recommendations


def upsert_preference_handler():
    user_id = request.user_id
    body = json_body()
    print(f"DEBUG UPSERT: Body received: {body}")

    # --- STEP 1: GET OR CREATE USER PREFERENCE ---
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    is_new = False

    if not pref:
        is_new = True
        default_role = body.get("role") or request.user_role or "IBU_HAMIL"
        pref = UserPreference(user_id=user_id, role=default_role.upper())
        db.session.add(pref)

    # --- STEP 2: UPDATE SIMPLE FIELDS TERLEBIH DAHULU ---
    # Numeric casting mapping
    numeric_fields = {
        "height_cm": int,
        "weight_kg": float,
        "age_year": int,
        "age_month": int,
        "lila_cm": float
    }

    for field in ["height_cm", "weight_kg", "age_year", "age_month", "lila_cm", "lactation_phase"]:
        if field in body:
            val = body[field]
            if val is not None and field in numeric_fields:
                try:
                    val = numeric_fields[field](val)
                except (ValueError, TypeError):
                    pass # Keep original value or handle error
            setattr(pref, field, val)

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

    # --- STEP 4: GET USER AND UPDATE NAME ---
    user = User.query.get(user_id)

    # Update name if provided (independent of role update)
    incoming_name = body.get("name") or body.get("nama")
    if user and incoming_name:
        user.name = incoming_name

    # --- STEP 4.5: ROLE UPDATE (HANYA JIKA ADA DI BODY) ---
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
        if user and user.role_id != role_obj.id:
            user.role_id = role_obj.id

    # Role final setelah update
    current_role = pref.role.upper()

    # --- STEP 5: ROLE VALIDATION ---
    ROLE_REQUIREMENTS = {
        "IBU_HAMIL": [
            "weight_kg", "height_cm", "age_year",
            "hpht", "lila_cm"
        ],
        "IBU_MENYUSUI": [
            "weight_kg", "height_cm", "age_year", "lactation_phase"
        ],
        "ANAK_BATITA": [
            "weight_kg", "height_cm", "age_year", "age_month"
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
        "name": user.name if user else None,
        "role": pref.role,
        "height_cm": pref.height_cm,
        "weight_kg": float(pref.weight_kg) if pref.weight_kg is not None else None,
        "age_year": pref.age_year,
        "age_month": pref.age_month,
        "hpht": pref.hpht.isoformat() if pref.hpht else None,
        "gestational_age_weeks": pref.gestational_age_weeks,
        "lila_cm": pref.lila_cm,
        "lactation_phase": pref.lactation_phase,
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


def get_user_profile_handler():
    user_id = request.user_id

    # Get user
    user = User.query.get(user_id)
    if not user:
        return error("USER_NOT_FOUND", "User not found", 404)

    # Return user data
    response = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar": user.avatar,
        "role": user.role.name if user.role else None,
    }

    return ok(response)


def update_user_profile_handler():
    user_id = request.user_id
    body = json_body()

    # Get user
    user = User.query.get(user_id)
    if not user:
        return error("USER_NOT_FOUND", "User not found", 404)

    # Update allowed fields
    allowed_fields = ['name', 'avatar']
    for field in allowed_fields:
        if field in body and body[field] is not None:
            setattr(user, field, body[field])

    db.session.commit()

    # Return updated user data
    response = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar": user.avatar,
        "role": user.role.name if user.role else None,
    }

    return ok(response)


def update_avatar_handler():
    user_id = request.user_id
    body = json_body()
    avatar_url = body.get("avatar") or body.get("avatar_url")
    if not avatar_url:
        return error("INVALID_INPUT", "Avatar URL is required", 400)

    user = User.query.get(user_id)
    if not user:
        return error("USER_NOT_FOUND", "User not found", 404)

    user.avatar = avatar_url
    db.session.commit()

    return ok({"user_id": user_id, "avatar": avatar_url})


def get_preference_handler():
    user_id = request.user_id

    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        return error("PREFERENCE_NOT_FOUND", "User preference not found", 404)

    # Get user info for name
    user = User.query.get(user_id)

    # Calculate nutritional targets
    targets = calculate_nutritional_targets(pref)

    response = {
        "user_id": user_id,
        "name": user.name if user else None,
        "email": user.email if user else None,
        "role": pref.role,
        "height_cm": pref.height_cm,
        "weight_kg": float(pref.weight_kg) if pref.weight_kg is not None else None,
        "age_year": pref.age_year,
        "age_month": pref.age_month,
        "hpht": pref.hpht.isoformat() if pref.hpht else None,
        "gestational_age_weeks": pref.gestational_age_weeks,
        "lila_cm": pref.lila_cm,
        "lactation_phase": pref.lactation_phase,
        "food_prohibitions": pref.food_prohibitions or [],
        "allergens": pref.allergens or [],
        "calorie_target": targets["calories"],
        "nutritional_targets": targets,
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
    }

    return ok(response)


def get_dashboard_summary_handler():
    user_id = request.user_id

    # 1. Get Preference & Targets
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        return error("PREFERENCE_REQUIRED", "Please complete preferences", 409)

    targets = calculate_nutritional_targets(pref)

    # 2. Get Consumed Logs (Not strictly per day, as requested: 'jangan untuk perhari dulu')
    # Filter only meals that have been marked as consumed/eaten
    logs = FoodMealLog.query.filter(
        FoodMealLog.user_id == user_id,
        FoodMealLog.is_consumed == True
    ).all()

    today_nutrition = {
        "calories": sum(log.total_calories for log in logs),
        "protein_g": float(sum(log.total_protein_g for log in logs)),
        "carbs_g": float(sum(log.total_carbs_g for log in logs)),
        "fat_g": float(sum(log.total_fat_g for log in logs)),
    }

    # 3. Calculate Remaining Targets
    remaining = {
        "calories": max(0, targets["calories"] - today_nutrition["calories"]),
        "protein_g": max(0.0, targets["protein_g"] - today_nutrition["protein_g"]),
        "carbs_g": max(0.0, targets["carbs_g"] - today_nutrition["carbs_g"]),
        "fat_g": max(0.0, targets["fat_g"] - today_nutrition["fat_g"]),
    }

    # 4. Get Recommendations (Prioritize current meal type based on time)
    now_hour = (datetime.utcnow().hour + 7) % 24 # WIB
    current_meal_type = "BREAKFAST"
    if 10 <= now_hour < 15:
        current_meal_type = "LUNCH"
    elif 15 <= now_hour < 21:
        current_meal_type = "DINNER"
    elif 21 <= now_hour or now_hour < 4:
        current_meal_type = "DINNER" # Still dinner for late night

    menus = FoodMenu.query.filter_by(is_active=True).all()
    menu_ids = [m.id for m in menus]

    ingredient_map = {ing.id: ing for ing in FoodIngredient.query.all()}
    compositions = FoodMenuIngredient.query.filter(
        FoodMenuIngredient.menu_id.in_(menu_ids or [0])
    ).all()

    composition_by_menu = {}
    for comp in compositions:
        composition_by_menu.setdefault(comp.menu_id, []).append(comp)

    # Parse parameters for recommendations
    from app.services.food_constants import (
        DEFAULT_BOOST_PER_HIT, DEFAULT_BOOST_PER_100G, 
        DEFAULT_MIN_HITS, DEFAULT_OPTIONS_PER_MEAL
    )
    from app.utils.http import arg_int
    
    boost_per_hit = arg_int("boost_per_hit", DEFAULT_BOOST_PER_HIT, min_value=0, max_value=1000)
    boost_per_100g = arg_int("boost_per_100g", DEFAULT_BOOST_PER_100G, min_value=0, max_value=10000)
    min_hits = arg_int("min_hits", DEFAULT_MIN_HITS, min_value=1, max_value=10)
    options_per_meal = arg_int("options_per_meal", DEFAULT_OPTIONS_PER_MEAL, min_value=1, max_value=10)
    
    require_detected_param = request.args.get("require_detected")
    require_detected = (
        None if require_detected_param is None 
        else (require_detected_param.lower() == "true")
    )
    
    boost_by_quantity = (
        request.args.get("boost_by_quantity", "true").lower() == "true"
    )
    
    meal_type_filter = request.args.get("meal_type")

    recommendation_data = generate_meal_recommendations(
        user_id=user_id,
        preference=pref,
        targets=targets,
        menus=menus,
        ingredient_map=ingredient_map,
        composition_by_menu=composition_by_menu,
        detected_ids=set(),
        boost_per_hit=boost_per_hit,
        boost_per_100g=boost_per_100g,
        min_hits=min_hits,
        options_per_meal=options_per_meal,
        require_detected=require_detected,
        boost_by_quantity=boost_by_quantity,
        meal_type_filter=meal_type_filter
    )

    # Extract recommendations with priority for current meal type
    all_recs = recommendation_data.get("recommendations", [])

    # Try to find the exact match for current meal type
    target_rec = next((r for r in all_recs if r["meal_type"] == current_meal_type), None)

    # If no match, take the first one as fallback
    if not target_rec and all_recs:
        target_rec = all_recs[0]

    dashboard_recommendations = []
    if target_rec:
        for option in target_rec.get("options", []):
            dashboard_recommendations.append({
                "id": option["menu_id"],
                "name": option["menu_name"],
                "calories": option["nutrition"]["calories"],
                "image_url": option.get("image_url") or f"https://picsum.photos/seed/{option['menu_id']}/200",
                "description": f"Target: {target_rec['meal_type'].capitalize()}"
            })

    dashboard_recommendations = dashboard_recommendations[:5]

    user_obj = User.query.get(user_id)

    return ok({
        "user": {
            "name": user_obj.name if user_obj else "Bunda",
            "role": pref.role,
            "preferences": {
                "weight_kg": float(pref.weight_kg) if pref.weight_kg else None,
                "height_cm": pref.height_cm,
                "age_year": pref.age_year,
                "age_month": pref.age_month,
                "lactation_phase": pref.lactation_phase,
                "lila_cm": pref.lila_cm,
                "hpht": pref.hpht.isoformat() if pref.hpht else None,
                "gestational_age_weeks": pref.gestational_age_weeks,
                "allergens": pref.allergens or [],
                "food_prohibitions": pref.food_prohibitions or []
            }
        },
        "targets": targets,
        "today_nutrition": today_nutrition,
        "remaining": remaining,
        "recommendations": dashboard_recommendations
    })
