from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User
from app.utils.auth import create_token, check_password_hash

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "email and password required"}}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": {"code": "INVALID_CREDENTIALS", "message": "Email or password incorrect"}}), 401

    ok = False
    try:
        ok = check_password_hash(user.password, password)
    except Exception:
        ok = (user.password == password)
    if not ok:
        return jsonify({"error": {"code": "INVALID_CREDENTIALS", "message": "Email or password incorrect"}}), 401

    role_name = user.role.name if user.role else ""
    token = create_token(user.id, role_name)
    return jsonify({
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": role_name}
    })
