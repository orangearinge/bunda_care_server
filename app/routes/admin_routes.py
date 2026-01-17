from flask import Blueprint
from app.utils.auth import require_admin
from app.controllers.admin_user_controller import (
    list_users_handler,
    get_user_detail_handler,
    update_user_role_handler
)
from app.controllers.feedback_controller import admin_list_feedbacks_handler
from app.controllers.dashboard_controller import get_stats_handler, get_user_growth_handler

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.route("/users", methods=["GET"])
@require_admin
def list_users():
    return list_users_handler()

@admin_bp.route("/users/<int:id>", methods=["GET"])
@require_admin
def get_user(id):
    return get_user_detail_handler(id)

@admin_bp.route("/users/<int:id>/role", methods=["PUT"])
@require_admin
def update_user_role(id):
    return update_user_role_handler(id)

@admin_bp.route("/health", methods=["GET"])
def admin_health():
    return {"status": "ok"}

@admin_bp.route("/feedbacks", methods=["GET"])
@require_admin
def list_feedbacks():
    return admin_list_feedbacks_handler()

@admin_bp.route("/dashboard/stats", methods=["GET"])
@require_admin
def dashboard_stats():
    return get_stats_handler()

@admin_bp.route("/dashboard/user-growth", methods=["GET"])
@require_admin
def dashboard_user_growth():
    return get_user_growth_handler()
