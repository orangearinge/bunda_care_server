from flask import Blueprint
from app.controllers.auth_controller import login_handler, register_handler, logout_handler, google_login_handler, check_user_preferences_status
from app.utils.auth import require_auth
from app.utils.http import ok

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.post("/login")
def login():
    return login_handler()


@auth_bp.post("/register")
def register():
    return register_handler()


@auth_bp.post("/logout")
def logout():
    return logout_handler()

@auth_bp.post("/google")
def google_login():
    return google_login_handler()

@auth_bp.get("/preferences-status")
@require_auth
def get_preferences_status():
    from flask import request
    user_id = request.user_id
    has_preferences, preference = check_user_preferences_status(user_id)
    
    response_data = {
        "has_preferences": has_preferences,
        "needs_preferences": not has_preferences
    }
    
    if preference:
        response_data["current_role"] = preference.role
    
    return ok(response_data)
