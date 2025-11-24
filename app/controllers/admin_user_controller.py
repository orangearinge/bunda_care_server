from flask import request
from sqlalchemy import or_
from app.extensions import db
from app.models.user import User
from app.models.role import Role
from app.utils.http import ok, error, json_body, arg_int

def list_users_handler():
    page = arg_int("page", 1, min_value=1)
    limit = arg_int("limit", 10, min_value=1, max_value=100)
    search = (request.args.get("search") or "").strip()
    role_filter = (request.args.get("role") or "").strip()

    query = User.query

    if search:
        term = f"%{search}%"
        query = query.filter(or_(User.name.ilike(term), User.email.ilike(term)))
    
    if role_filter:
        query = query.join(Role).filter(Role.name == role_filter)

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    users = []
    for u in pagination.items:
        users.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.name if u.role else None,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
    
    return ok({
        "items": users,
        "total": pagination.total,
        "page": page,
        "limit": limit,
        "pages": pagination.pages
    })

def get_user_detail_handler(id):
    user = User.query.get(id)
    if not user:
        return error("NOT_FOUND", "User not found", 404)
    
    return ok({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.name if user.role else None,
        "created_at": user.created_at.isoformat() if user.created_at else None
    })

def update_user_role_handler(id):
    user = User.query.get(id)
    if not user:
        return error("NOT_FOUND", "User not found", 404)
    
    data = json_body()
    role_name = (data.get("role") or "").strip()
    if not role_name:
        return error("VALIDATION_ERROR", "Role name is required", 400)
    
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return error("NOT_FOUND", f"Role '{role_name}' not found", 404)
    
    try:
        user.role = role
        db.session.commit()
        return ok({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role.name
        })
    except Exception as e:
        db.session.rollback()
        return error("UNKNOWN_ERROR", str(e), 500)
