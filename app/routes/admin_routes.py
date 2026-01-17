from flask import Blueprint
from app.utils.auth import require_admin
from app.controllers.admin_user_controller import (
    list_users_handler,
    get_user_detail_handler,
    update_user_role_handler
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.get("/users")
@require_admin
def list_users():
    return list_users_handler()

@admin_bp.get("/users/<int:id>")
@require_admin
def get_user(id):
    return get_user_detail_handler(id)

@admin_bp.put("/users/<int:id>/role")
@require_admin
def update_user_role(id):
    return update_user_role_handler(id)

from app.controllers.feedback_controller import admin_list_feedbacks_handler

@admin_bp.get("/feedbacks")
@require_admin
def list_feedbacks():
    return admin_list_feedbacks_handler()

from app.controllers.dashboard_controller import get_stats_handler, get_user_growth_handler

@admin_bp.get("/dashboard/stats")
@require_admin
def dashboard_stats():
    return get_stats_handler()

@admin_bp.get("/dashboard/user-growth")
@require_admin
def dashboard_user_growth():
    return get_user_growth_handler()
