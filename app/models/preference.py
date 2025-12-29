from app.extensions import db
from sqlalchemy.dialects.mysql import JSON
from uuid import uuid4

class UserPreference(db.Model):
    __tablename__ = "user_preferences"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    height_cm = db.Column(db.Integer)
    weight_kg = db.Column(db.Numeric(6,2))
    age_year = db.Column(db.Integer)
    hpht = db.Column(db.Date)
    
    @property
    def gestational_age_weeks(self):
        if self.hpht:
            from datetime import date
            delta = date.today() - self.hpht
            return max(0, delta.days // 7)
        return None
    belly_circumference_cm = db.Column(db.Integer)
    lila_cm = db.Column(db.Integer)
    lactation_ml = db.Column(db.Integer)
    food_prohibitions = db.Column(JSON)
    allergens = db.Column(JSON)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)
