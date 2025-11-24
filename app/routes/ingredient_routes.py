from flask import Blueprint
from app.controllers.ingredient_controller import get_all_ingredients, create_ingredient, update_ingredient, delete_ingredient
from app.utils.auth import require_admin, require_auth

bp = Blueprint("ingredients", __name__, url_prefix="/api/ingredients")

@bp.route("", methods=["GET"])
@require_auth
def list_ingredients():
    return get_all_ingredients()

@bp.route("", methods=["POST"])
@require_admin
def create():
    return create_ingredient()

@bp.route("/<int:id>", methods=["PUT"])
@require_admin
def update(id):
    return update_ingredient(id)

@bp.route("/<int:id>", methods=["DELETE"])
@require_admin
def delete(id):
    return delete_ingredient(id)
