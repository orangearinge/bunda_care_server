from flask import Blueprint
from app.utils.auth import require_auth
from app.controllers.feedback_controller import (
    create_feedback_handler,
    get_my_feedbacks_handler
)

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api/feedback")

@feedback_bp.route("", methods=["POST"])
@require_auth
def create_feedback():
    return create_feedback_handler()

@feedback_bp.route("/me", methods=["GET"])
@require_auth
def get_my_feedbacks():
    return get_my_feedbacks_handler()
