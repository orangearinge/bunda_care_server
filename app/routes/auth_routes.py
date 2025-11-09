from flask import Blueprint
from app.controllers.auth_controller import login_handler, register_handler

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.post("/login")
def login():
    return login_handler()


@auth_bp.post("/register")
def register():
    return register_handler()
