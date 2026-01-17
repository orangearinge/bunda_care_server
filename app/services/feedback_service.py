from app.extensions import db
from app.models.feedback import Feedback
from app.services.ai_feedback_service import classify_feedback

def create_feedback(user_id, rating, comment):
    """
    Creates a new user feedback entry in the database.
    Automatically classifies the feedback content using AI.
    """
    # Lakukan klasifikasi AI
    classification_result = None
    if comment:
        # Kita panggil service AI. Ini sinkronus (blocking).
        # Jika butuh performa tinggi, sebaiknya gunakan background task (Celery/RQ).
        # Untuk saat ini kita buat simpel sesuai request.
        classification_result = classify_feedback(comment)

    new_feedback = Feedback(
        user_id=user_id,
        rating=rating,
        comment=comment,
        classification=classification_result
    )
    
    db.session.add(new_feedback)
    db.session.commit()
    return new_feedback

def get_user_feedbacks(user_id):
    """
    Retrieves all feedback submitted by a specific user.
    """
    return Feedback.query.filter_by(user_id=user_id).order_by(Feedback.created_at.desc()).all()

def get_all_feedbacks(limit=50):
    """
    Retrieves all feedbacks for admin purposes.
    """
    return Feedback.query.order_by(Feedback.created_at.desc()).limit(limit).all()
