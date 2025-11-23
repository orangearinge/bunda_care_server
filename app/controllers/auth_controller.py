from flask import request
from app.extensions import db
from app.models.user import User
from app.utils.auth import create_token, check_password_hash, hash_password
from app.utils.http import ok, error, json_body

def login_handler():
    data = json_body()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return error("VALIDATION_ERROR", "email and password required", 400)

    user = User.query.filter_by(email=email).first()
    if not user:
        return error("INVALID_CREDENTIALS", "Email or password incorrect", 401)

    ok_pw = False
    try:
        ok_pw = check_password_hash(user.password, password)
    except Exception:
        ok_pw = (user.password == password)
    if not ok_pw:
        return error("INVALID_CREDENTIALS", "Email or password incorrect", 401)

    role_name = user.role.name if user.role else ""
    token = create_token(user.id, role_name)
    return ok({
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": role_name}
    })

def register_handler():
    data = json_body()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return error("VALIDATION_ERROR", "email and password required", 400)
    if len(password) < 6:
        return error("VALIDATION_ERROR", "password must be at least 6 characters", 400)
    exists = User.query.filter_by(email=email).first()
    if exists:
        return error("EMAIL_IN_USE", "email already registered", 409)
    try:
        pw_hash = hash_password(password)
        user = User(name=name, email=email, password=pw_hash)
        db.session.add(user)
        db.session.commit()
        role_name = user.role.name if user.role else ""
        token = create_token(user.id, role_name)
        return ok({
            "token": token,
            "user": {"id": user.id, "name": user.name, "email": user.email, "role": role_name}
        }, 201)
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)
