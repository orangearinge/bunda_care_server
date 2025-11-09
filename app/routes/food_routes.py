from flask import Blueprint
from app.utils.auth import require_auth
from app.controllers.food_controller import (
    scan_food_handler,
    recommendation_handler,
    create_meal_log_handler,
    list_meal_log_handler,
)

food_bp = Blueprint("food", __name__, url_prefix="/api")

@food_bp.post("/scan-food")
@require_auth
def scan_food():
    return scan_food_handler()


@food_bp.get("/recommendation")
@require_auth
def recommendation():
    return recommendation_handler()


# Alias plural path for convenience
@food_bp.get("/recommendations")
@require_auth
def recommendations():
    return recommendation_handler()


@food_bp.get("/meal-log")
@require_auth
def list_meal_log():
    return list_meal_log_handler()


@food_bp.post("/meal-log")
@require_auth
def create_meal_log():
    return create_meal_log_handler()
