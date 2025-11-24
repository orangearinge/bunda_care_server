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

# Admin Routes
from app.utils.auth import require_admin
from app.controllers.food_controller import (
    create_menu_handler,
    update_menu_handler,
    delete_menu_handler,
    get_menu_detail_handler
)

@food_bp.post("/menus")
@require_admin
def create_menu():
    return create_menu_handler()

@food_bp.get("/menus/<int:id>")
@require_auth
def get_menu(id):
    return get_menu_detail_handler(id)

@food_bp.put("/menus/<int:id>")
@require_admin
def update_menu(id):
    return update_menu_handler(id)

@food_bp.delete("/menus/<int:id>")
@require_admin
def delete_menu(id):
    return delete_menu_handler(id)
