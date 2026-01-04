from flask import Blueprint, request
from app.utils.auth import require_auth
from app.controllers.user_controller import (
    upsert_preference_handler, 
    get_preference_handler,
    get_dashboard_summary_handler
)

user_bp = Blueprint("user", __name__, url_prefix="/api/user")

@user_bp.route("/preference", methods=["GET", "POST"])
@require_auth
def preference():
    if request.method == "GET":
        return get_preference_handler()
    return upsert_preference_handler()

@user_bp.route("/dashboard", methods=["GET"])
@require_auth
def dashboard():
    return get_dashboard_summary_handler()
