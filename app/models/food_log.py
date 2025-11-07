from app.extensions import db

class FoodLog(db.Model):
    __tablename__ = "food_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("food_ingredients.id"), nullable=False)
    quantity_g = db.Column(db.Numeric(8,2), nullable=False, default=100)
    logged_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
