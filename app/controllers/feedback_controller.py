from flask import request
from app.utils.http import ok, error, json_body, validate_schema
from app.schemas.feedback_schema import FeedbackSchema
from app.services.feedback_service import create_feedback, get_user_feedbacks, get_all_feedbacks

def admin_list_feedbacks_handler():
    feedbacks = get_all_feedbacks()
    
    result = []
    for f in feedbacks:
        result.append({
            "id": f.id,
            "user_id": f.user_id,
            "rating": f.rating,
            "comment": f.comment,
            "classification": f.classification,
            "created_at": f.created_at.isoformat(),
            "user_name": f.user.full_name if f.user else "Unknown"
        })
        
    return ok(result)

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
