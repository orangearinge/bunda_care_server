
from datetime import datetime, time, timedelta
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
from app.utils.http import ok, error, json_body, validate_schema
from app.utils.enums import UserRole, MealType
from app.services.nutrition_service import calculate_nutritional_targets
from app.services.recommendation_service import generate_meal_recommendations
from app.schemas.user_schema import (
    UserPreferenceSchema, 
    UserProfileUpdateSchema, 
    AvatarUpdateSchema
)

def upsert_preference_handler():
    user_id = request.user_id
    body = json_body()
    
    # --- VALDIATE INPUT ---
    data, errors = validate_schema(UserPreferenceSchema, body, partial=True)
    if errors:
        return error("VALIDATION_ERROR", "Invalid input data", 400, details=errors)


    # --- STEP 1: GET OR CREATE USER PREFERENCE ---
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    is_new = False

    if not pref:
        is_new = True
        default_role = data.get("role") or request.user_role or UserRole.IBU_HAMIL.value
        pref = UserPreference(user_id=user_id, role=default_role.upper())
        db.session.add(pref)

    # --- STEP 2: UPDATE FIELDS FROM DATA ---
    fields_to_update = [
        "height_cm", "weight_kg", "age_year", "age_month", 
        "lila_cm", "lactation_phase", "hpht", 
        "food_prohibitions", "allergens"
    ]
    
    for field in fields_to_update:
        if field in data:
            setattr(pref, field, data[field])

    # --- STEP 4: GET USER AND UPDATE NAME ---
    user = User.query.get(user_id)

    # Update name if provided
    if user and data.get("name"):
        user.name = data["name"]

    # --- STEP 4.5: ROLE UPDATE ---
    incoming_role = data.get("role")
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

    # --- STEP 5: FINAL SCHEMA VALIDATION FOR ROLE REQUIREMENTS ---
    # Re-validate fully if it's not partial anymore or just to be sure
    # Since we did partial=True above, we should check if the resulting pref is valid
    # But our schema validates_schema already ran during validate_schema call.
    # If we need to ensure the final state is valid:
    full_data = {
        "role": pref.role,
        "height_cm": pref.height_cm,
        "weight_kg": float(pref.weight_kg) if pref.weight_kg is not None else None,
        "age_year": pref.age_year,
        "age_month": pref.age_month,
        "hpht": pref.hpht,
        "lila_cm": pref.lila_cm,
        "lactation_phase": pref.lactation_phase
    }
    _, errors = validate_schema(UserPreferenceSchema, full_data)
    if errors:
        return error("VALIDATION_ERROR", "Incomplete preference data for selected role", 400, details=errors)

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
    data, errors = validate_schema(UserProfileUpdateSchema, json_body(), partial=True)
    if errors:
        return error("VALIDATION_ERROR", "Invalid input data", 400, details=errors)

    # Get user
    user = User.query.get(user_id)
    if not user:
        return error("USER_NOT_FOUND", "User not found", 404)

    # Update allowed fields
    if "name" in data:
        user.name = data["name"]
    if "avatar" in data:
        user.avatar = data["avatar"]


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
    data, errors = validate_schema(AvatarUpdateSchema, json_body())
    if errors:
        return error("VALIDATION_ERROR", "Invalid input data", 400, details=errors)

    avatar_url = data.get("avatar") or data.get("avatar_url")

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

    # 2. Get Consumed Logs for TODAY (WIB - GMT+7)
    now_utc = datetime.utcnow()
    now_wib = now_utc + timedelta(hours=7)
    
    # Calculate boundaries in WIB
    start_of_day_wib = datetime(now_wib.year, now_wib.month, now_wib.day)
    end_of_day_wib = start_of_day_wib + timedelta(days=1)
    
    # Convert WIB boundaries back to UTC to match DB (server_default=now())
    start_of_day_utc = start_of_day_wib - timedelta(hours=7)
    end_of_day_utc = end_of_day_wib - timedelta(hours=7)

    # Filter only meals that have been marked as consumed/eaten TODAY
    logs = FoodMealLog.query.filter(
        FoodMealLog.user_id == user_id,
        FoodMealLog.is_consumed == True,
        FoodMealLog.logged_at >= start_of_day_utc,
        FoodMealLog.logged_at < end_of_day_utc
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
    now_hour = now_wib.hour # Uses the WIB time calculated above
    current_meal_type = MealType.BREAKFAST
    if 10 <= now_hour < 15:
        current_meal_type = MealType.LUNCH
    elif 15 <= now_hour < 21:
        current_meal_type = MealType.DINNER
    elif 21 <= now_hour or now_hour < 4:
        current_meal_type = MealType.DINNER # Still dinner for late night

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


def get_history_handler():
    user_id = request.user_id
    
    # 1. Get current targets (as a reference)
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        return error("PREFERENCE_REQUIRED", "Please complete preferences", 409)
    targets = calculate_nutritional_targets(pref)

    # 2. Get all consumed logs (sorted by date desc)
    logs = FoodMealLog.query.filter_by(user_id=user_id, is_consumed=True).order_by(FoodMealLog.logged_at.desc()).all()
    
    history_map = {}
    
    for log in logs:
        # Convert UTC to WIB Date for grouping
        wib_time = log.logged_at + timedelta(hours=7)
        date_str = wib_time.strftime("%Y-%m-%d")
        
        if date_str not in history_map:
            history_map[date_str] = {
                "date": date_str,
                "calories": 0,
                "protein_g": 0.0,
                "carbs_g": 0.0,
                "fat_g": 0.0,
                "meal_count": 0
            }
        
        history_map[date_str]["calories"] += log.total_calories
        history_map[date_str]["protein_g"] += float(log.total_protein_g)
        history_map[date_str]["carbs_g"] += float(log.total_carbs_g)
        history_map[date_str]["fat_g"] += float(log.total_fat_g)
        history_map[date_str]["meal_count"] += 1

    # Convert map to sorted list
    history_list = []
    for date_str in sorted(history_map.keys(), reverse=True):
        entry = history_map[date_str]
        # Round values for clean response
        entry["protein_g"] = round(entry["protein_g"], 1)
        entry["carbs_g"] = round(entry["carbs_g"], 1)
        entry["fat_g"] = round(entry["fat_g"], 1)
        
        # Add context targets (current targets are used as reference)
        entry["target_calories"] = targets["calories"]
        entry["percentage"] = min(100, int((entry["calories"] / targets["calories"]) * 100)) if targets["calories"] > 0 else 0
        
        history_list.append(entry)
        
    return ok(history_list)


def get_history_detail_handler(date_str):
    user_id = request.user_id
    
    try:
        # Parse visual date string
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return error("INVALID_DATE", "Format must be YYYY-MM-DD", 400)
    
    # Calculate WIB boundaries for that specific date
    start_of_day_wib = datetime.combine(target_date, time.min)
    end_of_day_wib = datetime.combine(target_date, time.max)
    
    # Convert WIB boundaries back to UTC for DB query
    start_of_day_utc = start_of_day_wib - timedelta(hours=7)
    end_of_day_utc = end_of_day_wib - timedelta(hours=7)
    
    logs = FoodMealLog.query.filter(
        FoodMealLog.user_id == user_id,
        FoodMealLog.is_consumed == True,
        FoodMealLog.logged_at >= start_of_day_utc,
        FoodMealLog.logged_at <= end_of_day_utc
    ).order_by(FoodMealLog.logged_at.asc()).all()
    
    # Load related menu data for names and images
    menu_ids = [log.menu_id for log in logs]
    menus = FoodMenu.query.filter(FoodMenu.id.in_(menu_ids or [0])).all()
    menu_map = {menu.id: menu for menu in menus}
    
    result = []
    for log in logs:
        menu = menu_map.get(log.menu_id)
        result.append({
            "id": log.id,
            "menu_name": menu.name if menu else "Makanan",
            "image_url": menu.image_url if menu and menu.image_url else f"https://picsum.photos/seed/{log.menu_id}/200",
            "calories": log.total_calories,
            "protein_g": float(log.total_protein_g),
            "carbs_g": float(log.total_carbs_g),
            "fat_g": float(log.total_fat_g),
            "logged_at": (log.logged_at + timedelta(hours=7)).isoformat()
        })
        
    return ok(result)

