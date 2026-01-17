from flask import request
from app.utils.http import ok, error, json_body, validate_schema, arg_int
from app.schemas.feedback_schema import FeedbackSchema
from app.services.feedback_service import create_feedback, get_user_feedbacks, get_all_feedbacks

from sqlalchemy import or_
from app.models.user import User
from app.models.feedback import Feedback

from sqlalchemy.orm import joinedload

def admin_list_feedbacks_handler():
    page = arg_int("page", 1, min_value=1)
    limit = arg_int("limit", 10, min_value=1, max_value=100)
    search = (request.args.get("search") or "").strip()
    classification = (request.args.get("classification") or "").strip().upper()

    query = Feedback.query.options(joinedload(Feedback.user))

    if search:
        term = f"%{search}%"
        query = query.join(User).filter(or_(
            Feedback.comment.ilike(term),
            User.name.ilike(term)
        ))
    
    if classification and classification != "ALL":
        print(f"DEBUG: Filtering by classification: {classification}")
        if classification == "POSITIF":
            query = query.filter(or_(
                Feedback.classification.ilike("%positif%"),
                Feedback.classification.ilike("%positive%")
            ))
        elif classification == "NEGATIF":
            query = query.filter(or_(
                Feedback.classification.ilike("%negatif%"),
                Feedback.classification.ilike("%negative%")
            ))
        else:
            query = query.filter(Feedback.classification.ilike(f"%{classification}%"))
    
    print(f"DEBUG: Final Query: {query}")
    pagination = query.order_by(Feedback.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
    
    result = []
    for f in pagination.items:
        result.append({
            "id": f.id,
            "user_id": f.user_id,
            "rating": f.rating,
            "comment": f.comment,
            "classification": f.classification,
            "created_at": f.created_at.isoformat(),
            "user_name": f.user.name if f.user else "Unknown"
        })
        
    return ok({
        "items": result,
        "total": pagination.total,
        "page": page,
        "limit": limit,
        "pages": pagination.pages
    })

def create_feedback_handler():
    user_id = getattr(request, 'user_id', None)
    if not user_id:
        return error("UNAUTHORIZED", "User must be logged in to provide feedback", 401)
        
    data, errors = validate_schema(FeedbackSchema, json_body())
    if errors:
        return error("VALIDATION_ERROR", "Invalid feedback data", 400, details=errors)
        
    feedback = create_feedback(user_id, data['rating'], data['comment'])
    
    return ok({
        "id": feedback.id,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "created_at": feedback.created_at.isoformat()
    })

def get_my_feedbacks_handler():
    user_id = getattr(request, 'user_id', None)
    if not user_id:
        return error("UNAUTHORIZED", "User must be logged in", 401)
        
    feedbacks = get_user_feedbacks(user_id)
    
    result = []
    for f in feedbacks:
        result.append({
            "id": f.id,
            "rating": f.rating,
            "comment": f.comment,
            "created_at": f.created_at.isoformat()
        })
        
    return ok(result)
