import datetime as dt
from functools import wraps
from flask import request, jsonify, current_app
import jwt
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(plain: str) -> str:
    return generate_password_hash(plain)


def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(dt.datetime.utcnow().timestamp()),
        "exp": int((dt.datetime.utcnow() + dt.timedelta(hours=12)).timestamp()),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def decode_token(token: str):
    return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"]) 


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": {"code": "UNAUTHORIZED", "message": "Missing Bearer token"}}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
            request.user_id = int(payload["sub"])  # type: ignore
            request.user_role = payload.get("role")  # type: ignore
        except Exception:
            return jsonify({"error": {"code": "UNAUTHORIZED", "message": "Invalid token"}}), 401
        return f(*args, **kwargs)
    return wrapper

__all__ = ["hash_password", "create_token", "require_auth", "check_password_hash"]
