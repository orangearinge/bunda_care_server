from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.preference import UserPreference
from app.utils.auth import require_auth

user_bp = Blueprint("user", __name__, url_prefix="/api/user")

@user_bp.post("/preference")
@require_auth
def upsert_preference():
    user_id = request.user_id  # set by middleware
    body = request.get_json(silent=True) or {}

    pref = UserPreference.query.get(user_id)
    if not pref:
        pref = UserPreference(user_id=user_id, role=body.get("role") or request.user_role or "IBU_HAMIL")
        db.session.add(pref)

    # assign allowed fields
    for f in [
        "role","height_cm","weight_kg","age_year","gestational_age_week",
        "belly_circumference_cm","lila_cm","dietary_restrictions","allergens","calorie_target"
    ]:
        if f in body:
            setattr(pref, f, body[f])

    db.session.commit()

    return jsonify({
        "user_id": user_id,
        "role": pref.role,
        "height_cm": pref.height_cm,
        "weight_kg": float(pref.weight_kg) if pref.weight_kg is not None else None,
        "age_year": pref.age_year,
        "gestational_age_week": pref.gestational_age_week,
        "belly_circumference_cm": pref.belly_circumference_cm,
        "lila_cm": pref.lila_cm,
        "dietary_restrictions": pref.dietary_restrictions or [],
        "allergens": pref.allergens or [],
        "calorie_target": pref.calorie_target,
        "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
    })
