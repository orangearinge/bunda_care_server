from app.extensions import db
from app.models.feedback import Feedback

def create_feedback(user_id, rating, comment):
    """
    Creates a new user feedback entry in the database.
    """
    new_feedback = Feedback(
        user_id=user_id,
        rating=rating,
        comment=comment
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
