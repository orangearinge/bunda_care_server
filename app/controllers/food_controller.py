from datetime import datetime, timedelta, date
from flask import request
from sqlalchemy import desc
from app.extensions import db
from app.utils.ai import recognize
from app.models.ingredient import FoodIngredient
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient
from app.models.preference import UserPreference
from app.utils.http import ok, error, json_body, arg_int, parse_iso_datetime
from app.models.meal_log import FoodMealLog, FoodMealLogItem

RAW_KW = ["dada","paha","fillet","kulit","hati","ati","telur","mentah","raw"]

def _norm_name(ing: FoodIngredient) -> str:
    return f"{(ing.name or '').lower()} {(ing.alt_names or '').lower()}"

def serialize_nutrition(ing: FoodIngredient, quantity_g: float):
    factor = (quantity_g or 100) / 100.0
    return {
        "calories": int(ing.calories * factor),
        "protein_g": float(ing.protein_g) * factor,
        "carbs_g": float(ing.carbs_g) * factor,
        "fat_g": float(ing.fat_g) * factor,
    }

def scan_food_handler():
    image = request.files.get("image")
    if not image:
        return error("IMAGE_REQUIRED", "image file is required", 400)

    labels = recognize(image)
    label_names = [str(l.get("label", "")).strip().lower() for l in labels if l.get("label")]

    if not label_names:
        return ok({"candidates": []})

    like_patterns = [f"%{name}%" for name in label_names]
    or_clauses = [clause for pat in like_patterns for clause in (FoodIngredient.name.ilike(pat), FoodIngredient.alt_names.ilike(pat))]
    ingrs = FoodIngredient.query.filter(db.or_(*or_clauses)).limit(20).all()

    def has_raw_hint(ing):
        txt = _norm_name(ing)
        return any(k in txt for k in RAW_KW)

    candidates = []
    TOP_N = 3
    for l in labels:
        label_l = l["label"].lower()
        scored = []
        for ing in ingrs:
            name_l = (ing.name or "").lower()
            alt_l = (ing.alt_names or "").lower()
            match = 0.0
            tokens = set(label_l.split())
            name_tokens = set(name_l.split())
            alt_tokens = set(alt_l.split())
            overlap = len(tokens & name_tokens)
            alt_overlap = len(tokens & alt_tokens)
            match += 3 * overlap + 2 * alt_overlap
            if label_l in name_l: match += 2
            if label_l in alt_l: match += 1
            if has_raw_hint(ing): match += 1
            conf = float(l.get("confidence", 0) or 0)
            match = match * (0.5 + conf)
            if match > 0:
                scored.append((match, ing))
        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = [ing for _, ing in scored]
        for ing in ranked[:TOP_N]:
            candidates.append({
                "ingredient_id": ing.id,
                "name": ing.name,
                "confidence": float(l.get("confidence", 0)),
                "per_100g": {
                    "calories": ing.calories,
                    "protein_g": float(ing.protein_g),
                    "carbs_g": float(ing.carbs_g),
                    "fat_g": float(ing.fat_g),
                },
                "suggested_quantity_g": 100
            })
    dedup = {}
    for c in candidates:
        cid = c["ingredient_id"]
        if cid not in dedup or c["confidence"] > dedup[cid]["confidence"]:
            dedup[cid] = c
    return ok({
        "candidates": list(dedup.values()),
        "detected_ids": [c["ingredient_id"] for c in dedup.values()],
    })

def recommendation_handler():
    user_id = request.user_id
    days = arg_int("days", 1, min_value=1, max_value=31)

    pref = UserPreference.query.get(user_id)
    if not pref:
        return error("PREFERENCE_REQUIRED", "Please complete preferences", 409)

    role = (pref.role or "").upper()
    height_m = (float(pref.height_cm or 0) / 100.0) if pref.height_cm else 0.0
    weight = float(pref.weight_kg or 0)
    bmi = (weight / (height_m * height_m)) if height_m > 0 else None

    def calc_targets_for_role():
        base = int(pref.calorie_target or 2000)
        protein = max(50.0, 0.9 * weight)
        carbs_pct = 0.5
        fat_pct = 0.3

        if role == "IBU_HAMIL":
            ga = pref.gestational_age_week or 0
            add = 0 if ga < 13 else (340 if ga < 28 else 452)
            base = int(pref.calorie_target or (2000 + add))
            protein = max(70.0, 1.1 * weight)
            carbs_pct = 0.5
            fat_pct = 0.3
            try:
                lila = float(pref.lila_cm or 0)
                if lila and lila < 23.5:
                    base += 200
                    protein = round(protein * 1.1, 1)
            except Exception:
                pass
        elif role == "IBU_MENYUSUI":
            lact_ml = None
            # Prefer query param if provided, else fallback to preference value
            qp = request.args.get("lactation_ml")
            if qp is not None and qp != "":
                try:
                    lact_ml = float(qp)
                except Exception:
                    lact_ml = None
            if lact_ml is None:
                try:
                    lact_ml = float(pref.lactation_ml or 0)
                except Exception:
                    lact_ml = None
            extra = int(0.67 * lact_ml) if (lact_ml and lact_ml > 0) else 500
            base = int(pref.calorie_target or (2200 + extra))
            protein = max(75.0, 1.1 * weight)
            carbs_pct = 0.5
            fat_pct = 0.3
        elif role == "ANAK_BALITA":
            base = int(max(900, min(1400, 90 * (weight or 12))))
            protein = max(20.0, 1.1 * (weight or 12))
            carbs_pct = 0.5
            fat_pct = 0.35

        return {
            "calories": base,
            "protein_g": round(protein, 1),
            "carbs_g": round(carbs_pct * base / 4.0, 1),
            "fat_g": round(fat_pct * base / 9.0, 1),
            "bmi": round(bmi, 1) if bmi else None,
        }

    targets = calc_targets_for_role()

    menus = FoodMenu.query.filter_by(is_active=True).order_by(FoodMenu.meal_type, FoodMenu.name).all()
    menu_ids = [m.id for m in menus]
    ing_map = {i.id: i for i in FoodIngredient.query.all()}
    comp = FoodMenuIngredient.query.filter(FoodMenuIngredient.menu_id.in_(menu_ids)).all()
    comp_by_menu = {}
    for c in comp:
        comp_by_menu.setdefault(c.menu_id, []).append(c)

    restr = set(pref.food_prohibitions or [])
    allerg = set(pref.allergens or [])

    # cooked-ingredient filtering removed: AI detects raw ingredients only

    detected_ids: set[int] = set()

    # 1) From query string: detected_ids=1,2,3
    detected_ids_param = (request.args.get("detected_ids") or "").strip()
    if detected_ids_param:
        for tok in detected_ids_param.replace(",", " ").split():
            try:
                detected_ids.add(int(tok))
            except Exception:
                pass

    # 2) From JSON body (common when using Postman)
    body = json_body() or {}

    # Accept several shapes:
    # - { detected_ids: [1,2,3] }
    # - { detected: [1,2,3] }
    # - { candidates: [{ingredient_id: 1}, ...] }
    # - { items: [{ingredient_id: 1}, ...] }
    def _add_from_iter(val):
        if isinstance(val, (list, tuple, set)):
            for v in val:
                try:
                    if isinstance(v, dict) and "ingredient_id" in v:
                        detected_ids.add(int(v.get("ingredient_id")))
                    else:
                        detected_ids.add(int(v))
                except Exception:
                    pass

    if isinstance(body, dict):
        if "detected_ids" in body:
            _add_from_iter(body.get("detected_ids"))
        if "detected" in body:
            _add_from_iter(body.get("detected"))
        if "candidates" in body:
            _add_from_iter(body.get("candidates"))
        if "items" in body:
            _add_from_iter(body.get("items"))

    boost_per_hit = arg_int("boost_per_hit", 400, min_value=0, max_value=1000)
    _req = request.args.get("require_detected")
    require_detected = (bool(detected_ids) if _req is None else (_req.lower() == "true"))
    boost_by_quantity = (request.args.get("boost_by_quantity", "true").lower() == "true")
    boost_per_100g = arg_int("boost_per_100g", 5, min_value=0, max_value=10000)
    min_hits = arg_int("min_hits", 1, min_value=1, max_value=10)
    _ho = request.args.get("hide_options")
    hide_options = (bool(detected_ids) if _ho is None else (_ho.lower() == "true"))

    def menu_ok(m: FoodMenu):
        tags = set((m.tags or "").lower().split(","))
        if any(a.lower() in tags for a in allerg):
            return False
        if any(r.lower() in tags for r in restr):
            return False
        # Ingredient-level filtering: check names and alt_names
        for c in comp_by_menu.get(m.id, []):
            ing = ing_map.get(c.ingredient_id)
            if not ing:
                continue
            name_l = (ing.name or "").lower()
            alt_l = (getattr(ing, "alt_names", None) or "").lower()
            if any(tok.lower() in name_l or tok.lower() in alt_l for tok in allerg):
                return False
            if any(tok.lower() in name_l or tok.lower() in alt_l for tok in restr):
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
            for k in ("calories", "protein_g", "carbs_g", "fat_g"):
                total[k] += n[k]
            ingredients.append({"ingredient_id": ing.id, "name": ing.name, "quantity_g": q})
        return total, ingredients

    def score_menu(nut, portion=3.0):
        target_split = {k: (targets[k] / portion) for k in ["calories","protein_g","carbs_g","fat_g"]}
        return sum(abs(float(nut[k]) - float(target_split[k])) for k in target_split)

    plan = []
    date_str = request.args.get("date")
    try:
        base_date = date.fromisoformat(date_str) if date_str else date.today()
    except Exception:
        base_date = date.today()
    options_per_meal = arg_int("options_per_meal", 3, min_value=1, max_value=5)

    meal_type_filter = (request.args.get("meal_type") or "").upper().strip()
    MEAL_TYPES = ["BREAKFAST","LUNCH","DINNER"]
    MEAL_TYPES = [meal_type_filter] if meal_type_filter in MEAL_TYPES else MEAL_TYPES

    for d in range(days):
        day_date = base_date + timedelta(days=d)
        meals_payload = []
        for meal_type in MEAL_TYPES:
            cand = [m for m in menus if m.meal_type.upper() == meal_type]
            scored_pool = []
            for m in cand:
                if not menu_ok(m):
                    continue
                n, ings = menu_nutrition(m)
                sc = score_menu(n)
                if detected_ids:
                    hits = 0
                    total_qty = 0.0
                    for it in ings:
                        try:
                            iid = int(it.get("ingredient_id"))
                            if iid in detected_ids:
                                hits += 1
                                q = float(it.get("quantity_g") or 0)
                                total_qty += max(0.0, q)
                        except Exception:
                            pass
                    if require_detected and hits < min_hits:
                        continue
                    boost_amount = 0
                    if hits > 0 and boost_per_hit > 0:
                        boost_amount += hits * boost_per_hit
                    if boost_by_quantity and total_qty > 0 and boost_per_100g > 0:
                        boost_amount += (total_qty / 100.0) * boost_per_100g
                    if boost_amount > 0:
                        sc = max(0, sc - boost_amount)
                scored_pool.append((sc, m, n, ings))

            scored_pool.sort(key=lambda x: (x[0], x[1].name.lower()))

            options = []
            for sc, m, n, ing_list in scored_pool[:options_per_meal]:
                options.append({
                    "menu_id": m.id,
                    "menu_name": m.name,
                    "nutrition": n,
                    "ingredients": ing_list,
                    "score": sc,
                    "food_log_payload": {
                        "items": [
                            {"ingredient_id": it["ingredient_id"], "quantity_g": it["quantity_g"]} for it in ing_list
                        ]
                    }
                })

            if options:
                best_opt = options[0]
                meals_payload.append({
                    "meal_type": meal_type,
                    **{k: best_opt[k] for k in ["menu_id","menu_name","nutrition","ingredients"]},
                    "food_log_payload": best_opt["food_log_payload"],
                })

            if not hide_options:
                meals_payload.append({
                    "meal_type": meal_type,
                    "options": options
                })
        summary = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for m in meals_payload:
            if "nutrition" in m:
                n = m["nutrition"]
                for k in ("calories", "protein_g", "carbs_g", "fat_g"):
                    summary[k] += n[k]
        plan.append({
            "date": day_date.isoformat(),
            "daily_target": targets,
            "meals": meals_payload,
            "summary": summary
        })

    return ok({
        "user_id": user_id,
        "start_date": date.today().isoformat(),
        "days": plan
    })


def create_meal_log_handler():
    user_id = request.user_id
    data = json_body()
    try:
        menu_id = int(data.get("menu_id"))
    except Exception:
        return error("VALIDATION_ERROR", "menu_id required", 400)
    try:
        servings = float(data.get("servings")) if data.get("servings") is not None else 1.0
    except Exception:
        servings = 1.0
    if servings <= 0:
        servings = 1.0

    menu = FoodMenu.q.uery.get(menu_id)
    if not menu:
        return error("MENU_NOT_FOUND", "menu_id does not exist", 400)
    comp = FoodMenuIngredient.query.filter_by(menu_id=menu_id).all()
    if not comp:
        return error("MENU_EMPTY", "No ingredients for the specified menu_id", 400)

    ing_map = {i.id: i for i in FoodIngredient.query.all()}

    total = {"calories": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    items_payload = []
    for c in comp:
        ing = ing_map.get(c.ingredient_id)
        if not ing:
            continue
        qty = float(c.quantity_g) * float(servings)
        n = serialize_nutrition(ing, qty)
        total["calories"] += n["calories"]
        total["protein_g"] += n["protein_g"]
        total["carbs_g"] += n["carbs_g"]
        total["fat_g"] += n["fat_g"]
        items_payload.append((ing.id, qty, n))

    try:
        logged_dt = parse_iso_datetime(data.get("logged_at")) or datetime.utcnow()

        ml = FoodMealLog(
            user_id=user_id,
            menu_id=menu_id,
            total_calories=int(total["calories"]),
            total_protein_g=float(total["protein_g"]),
            total_carbs_g=float(total["carbs_g"]),
            total_fat_g=float(total["fat_g"]),
            servings=float(servings),
            logged_at=logged_dt,
        )
        db.session.add(ml)
        db.session.flush()

        for iid, qty, n in items_payload:
            db.session.add(FoodMealLogItem(
                meal_log_id=ml.id,
                ingredient_id=iid,
                quantity_g=float(qty),
                calories=int(n["calories"]),
                protein_g=float(n["protein_g"]),
                carbs_g=float(n["carbs_g"]),
                fat_g=float(n["fat_g"]),
            ))

        db.session.commit()
        return ok({
            "meal_log_id": ml.id,
            "menu_id": menu_id,
            "menu_name": menu.name,
            "servings": float(servings),
            "logged_at": ml.logged_at.isoformat() if ml.logged_at else None,
            "total": total,
            "items": [
                {"ingredient_id": iid, "quantity_g": float(qty), **n} for iid, qty, n in items_payload
            ]
        }, 201)
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)


def list_meal_log_handler():
    user_id = request.user_id
    limit = arg_int("limit", 10)
    rows = (
        FoodMealLog.query
        .filter_by(user_id=user_id)
        .order_by(desc(FoodMealLog.logged_at))
        .limit(limit)
        .all()
    )
    menu_map = {m.id: m for m in FoodMenu.query.all()}
    ids = [r.id for r in rows]
    items = FoodMealLogItem.query.filter(FoodMealLogItem.meal_log_id.in_(ids or [0])).all()
    items_by_log = {}
    for it in items:
        items_by_log.setdefault(it.meal_log_id, []).append(it)
    payload = []
    for r in rows:
        m = menu_map.get(r.menu_id)
        payload.append({
            "meal_log_id": r.id,
            "menu_id": r.menu_id,
            "menu_name": m.name if m else None,
            "servings": float(r.servings),
            "logged_at": r.logged_at.isoformat() if r.logged_at else None,
            "total": {
                "calories": int(r.total_calories),
                "protein_g": float(r.total_protein_g),
                "carbs_g": float(r.total_carbs_g),
                "fat_g": float(r.total_fat_g),
            },
            "items": [
                {
                    "ingredient_id": it.ingredient_id,
                    "quantity_g": float(it.quantity_g),
                    "calories": int(it.calories),
                    "protein_g": float(it.protein_g),
                    "carbs_g": float(it.carbs_g),
                    "fat_g": float(it.fat_g),
                } for it in items_by_log.get(r.id, [])
            ]
        })
    return ok({"items": payload})
