from flask import Blueprint
from app.utils.auth import require_auth
from app.controllers.user_controller import upsert_preference_handler

user_bp = Blueprint("user", __name__, url_prefix="/api/user")

@user_bp.post("/preference")
@require_auth
def upsert_preference():
    return upsert_preference_handler()
