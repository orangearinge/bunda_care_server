from app.extensions import db

class FoodMenu(db.Model):
    __tablename__ = "food_menus"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)
    tags = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
