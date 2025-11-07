from datetime import datetime, timedelta, date
from flask import Blueprint, request, jsonify
from sqlalchemy import desc
from app.extensions import db
from app.utils.auth import require_auth
from app.utils.ai import recognize
from app.models.ingredient import FoodIngredient
from app.models.food_log import FoodLog
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient
from app.models.preference import UserPreference

food_bp = Blueprint("food", __name__, url_prefix="/api")


def serialize_nutrition(ing: FoodIngredient, quantity_g: float):
    factor = (quantity_g or 100) / 100.0
    return {
        "calories": int(ing.calories * factor),
        "protein_g": float(ing.protein_g) * factor,
        "carbs_g": float(ing.carbs_g) * factor,
        "fat_g": float(ing.fat_g) * factor,
    }


@food_bp.get("/food-log")
@require_auth
def list_food_log():
    user_id = request.user_id
    try:
        limit = int(request.args.get("limit", 10))
    except Exception:
        limit = 10
    since_str = request.args.get("since")
    q = FoodLog.query.filter_by(user_id=user_id)
    if since_str:
        try:
            since_dt = datetime.fromisoformat(since_str)
            q = q.filter(FoodLog.logged_at >= since_dt)
        except Exception:
            pass
    q = q.order_by(desc(FoodLog.logged_at)).limit(limit)
    logs = q.all()

    items = []
    # preload ingredients
    ing_map = {i.id: i for i in FoodIngredient.query.filter(FoodIngredient.id.in_([l.ingredient_id for l in logs] or [0])).all()}
    for l in logs:
        ing = ing_map.get(l.ingredient_id)
        if not ing:
            continue
        items.append({
            "id": l.id,
            "ingredient_id": ing.id,
            "ingredient_name": ing.name,
            "quantity_g": float(l.quantity_g),
            **serialize_nutrition(ing, float(l.quantity_g)),
            "logged_at": l.logged_at.isoformat() if l.logged_at else None,
        })
    return jsonify({"items": items})


@food_bp.post("/food-log")
@require_auth
def create_food_log():
    user_id = request.user_id
    body = request.get_json(silent=True) or {}
    items = body.get("items") or []
    if not isinstance(items, list) or not items:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "items array required"}}), 400

    created = 0
    for it in items:
        ingredient_id = it.get("ingredient_id")
        if not ingredient_id:
            continue
        quantity_g = float(it.get("quantity_g", 100))
        logged_at = it.get("logged_at")
        logged_dt = datetime.fromisoformat(logged_at) if isinstance(logged_at, str) else datetime.utcnow()
        log = FoodLog(user_id=user_id, ingredient_id=int(ingredient_id), quantity_g=quantity_g, logged_at=logged_dt)
        db.session.add(log)
        created += 1
    db.session.commit()
    return jsonify({"created_count": created}), 201


@food_bp.post("/scan-food")
@require_auth
def scan_food():
    image = request.files.get("image")
    if not image:
        return jsonify({"error": {"code": "IMAGE_REQUIRED", "message": "image file is required"}}), 400

    labels = recognize(image)  # [{label, confidence}]
    label_names = [l.get("label") for l in labels]

    # naive match: ILIKE any label or alt_names contains
    if not label_names:
        return jsonify({"candidates": []})

    like_patterns = [f"%{name}%" for name in label_names]
    query = FoodIngredient.query
    or_clauses = []
    for pat in like_patterns:
        or_clauses.append(FoodIngredient.name.ilike(pat))
    ingrs = query.filter(db.or_(*or_clauses)).limit(20).all()

    # map best match by order
    candidates = []
    for l in labels:
        best = None
        for ing in ingrs:
            if l["label"].lower() in (ing.name or "").lower():
                best = ing
                break
        if not best and ingrs:
            best = ingrs[0]
        if best:
            candidates.append({
                "ingredient_id": best.id,
                "name": best.name,
                "confidence": float(l.get("confidence", 0)),
                "per_100g": {
                    "calories": best.calories,
                    "protein_g": float(best.protein_g),
                    "carbs_g": float(best.carbs_g),
                    "fat_g": float(best.fat_g),
                }
            })
    # dedup by ingredient_id keep max confidence
    dedup = {}
    for c in candidates:
        cid = c["ingredient_id"]
        if cid not in dedup or c["confidence"] > dedup[cid]["confidence"]:
            dedup[cid] = c
    return jsonify({"candidates": list(dedup.values())})


@food_bp.get("/recommendation")
@require_auth
def recommendation():
    user_id = request.user_id
    try:
        days = int(request.args.get("days", 7))
    except Exception:
        days = 7

    pref = UserPreference.query.get(user_id)
    if not pref:
        return jsonify({"error": {"code": "PREFERENCE_REQUIRED", "message": "Please complete preferences"}}), 409

    # simple targets
    base = pref.calorie_target or 2000
    if (pref.role or "").upper() == "IBU_HAMIL":
        ga = pref.gestational_age_week or 0
        add = 0 if ga < 13 else (340 if ga < 28 else 452)
        base = (pref.calorie_target or (2000 + add))
    targets = {
        "calories": int(base),
        "protein_g": float(pref.weight_kg or 60) * 1.1,
        "carbs_g": 0.5 * base / 4.0,
        "fat_g": 0.3 * base / 9.0,
    }

    # load menus and composition
    menus = FoodMenu.query.filter_by(is_active=True).all()
    menu_ids = [m.id for m in menus]
    ing_map = {i.id: i for i in FoodIngredient.query.all()}
    comp = FoodMenuIngredient.query.filter(FoodMenuIngredient.menu_id.in_(menu_ids)).all()
    comp_by_menu = {}
    for c in comp:
        comp_by_menu.setdefault(c.menu_id, []).append(c)

    # filter by restrictions/allergens via tags
    restr = set((pref.dietary_restrictions or []))
    allerg = set((pref.allergens or []))

    def menu_ok(m: FoodMenu):
        tags = set((m.tags or "").lower().split(","))
        if any(a.lower() in tags for a in allerg):
            return False
        if any(r.lower() in tags for r in restr):
            return False
        return True

    def menu_nutrition(m: FoodMenu):
        total = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        ingredients = []
        for c in comp_by_menu.get(m.id, []):
            ing = ing_map.get(c.ingredient_id)
            if not ing: continue
            q = float(c.quantity_g)
            n = serialize_nutrition(ing, q)
            total["calories"] += n["calories"]
            total["protein_g"] += n["protein_g"]
            total["carbs_g"] += n["carbs_g"]
            total["fat_g"] += n["fat_g"]
            ingredients.append({"ingredient_id": ing.id, "name": ing.name, "quantity_g": q})
        return total, ingredients

    def score_menu(nut):
        # simple L1 deviation from one-third of daily target per main meal
        target_split = {k: (targets[k] / 3.0) for k in ["calories","protein_g","carbs_g","fat_g"]}
        return sum(abs(float(nut[k]) - float(target_split[k])) for k in target_split)

    plan = []
    today = date.today()
    used = set()

    for d in range(days):
        day_date = today + timedelta(days=d)
        meals_payload = []
        for meal_type in ["BREAKFAST","LUNCH","DINNER"]:
            candidates = [m for m in menus if menu_ok(m) and m.meal_type == meal_type and m.id not in used]
            best = None
            best_score = None
            best_n = None
            best_ing = None
            for m in candidates:
                n, ing_list = menu_nutrition(m)
                sc = score_menu(n)
                if best is None or sc < best_score:
                    best = m; best_score = sc; best_n = n; best_ing = ing_list
            if best is not None:
                used.add(best.id)
                meals_payload.append({
                    "meal_type": meal_type,
                    "menu_id": best.id,
                    "menu_name": best.name,
                    "nutrition": best_n,
                    "ingredients": best_ing,
                })
        # summary
        summary = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for m in meals_payload:
            n = m["nutrition"]
            summary["calories"] += n["calories"]
            summary["protein_g"] += n["protein_g"]
            summary["carbs_g"] += n["carbs_g"]
            summary["fat_g"] += n["fat_g"]
        plan.append({
            "date": day_date.isoformat(),
            "daily_target": targets,
            "meals": meals_payload,
            "summary": summary
        })

    return jsonify({
        "user_id": user_id,
        "start_date": today.isoformat(),
        "days": plan
    })
