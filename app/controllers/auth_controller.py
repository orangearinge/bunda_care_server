from flask import request, current_app
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

def logout_handler():
    """
    Handle logout request.
    Since we're using JWT tokens, the actual logout is handled on the client-side
    by removing the token from storage. This endpoint confirms the logout action.
    """
    return ok({"message": "Logged out successfully"})

def google_login_handler():
    data = json_body()
    token = data.get("token")
    if not token:
        return error("VALIDATION_ERROR", "Token required", 400)

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        
        # Verify the token
        client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        id_info = id_token.verify_oauth2_token(token, google_requests.Request(), audience=client_id)

        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
             return error("INVALID_TOKEN", "Invalid issuer", 401)

        google_id = id_info['sub']
        email = id_info.get('email')
        name = id_info.get('name')
        picture = id_info.get('picture')

        if not email:
             return error("INVALID_TOKEN", "Email not found in token", 400)

        # Check if user exists by google_id or email
        user = User.query.filter((User.google_id == google_id) | (User.email == email)).first()

        if user:
            # Update google_id if not set (linking account)
            if not user.google_id:
                user.google_id = google_id
            # Update avatar if not set
            if not user.avatar and picture:
                user.avatar = picture
            db.session.commit()
        else:
            # Create new user
            user = User(
                name=name,
                email=email,
                google_id=google_id,
                avatar=picture
            )
            db.session.add(user)
            db.session.commit()

        role_name = user.role.name if user.role else ""
        jwt_token = create_token(user.id, role_name)
        
        return ok({
            "token": jwt_token,
            "user": {
                "id": user.id, 
                "name": user.name, 
                "email": user.email, 
                "role": role_name,
                "avatar": user.avatar
            }
        })

    except ValueError as e:
        return error("INVALID_TOKEN", f"Token verification failed: {str(e)}", 401)
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)
