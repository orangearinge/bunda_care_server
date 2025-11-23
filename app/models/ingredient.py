from app.extensions import db

class FoodIngredient(db.Model):
    __tablename__ = "food_ingredients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    alt_names = db.Column(db.Text)
    calories = db.Column(db.Integer, nullable=False, default=0)
    protein_g = db.Column(db.Numeric(8,2), nullable=False, default=0)
    carbs_g = db.Column(db.Numeric(8,2), nullable=False, default=0)
    fat_g = db.Column(db.Numeric(8,2), nullable=False, default=0)

