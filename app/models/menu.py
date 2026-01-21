from app.extensions import db

class FoodMenu(db.Model):
    __tablename__ = "food_menus"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)
    tags = db.Column(db.Text)
    image_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    cooking_instructions = db.Column(db.Text, nullable=True)
    cooking_time_minutes = db.Column(db.Integer, nullable=True)
    target_role = db.Column(db.String(50), nullable=True, default="ALL") # TargetRole: IBU, ANAK, ALL, ANAK_6_8, etc.
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Manual Nutrition Override (Golden Override)
    nutrition_is_manual = db.Column(db.Boolean, nullable=True, default=False)
    serving_unit = db.Column(db.String(50), nullable=True)  # e.g., "Porsi", "Mangkok", "Piring"
    manual_calories = db.Column(db.Integer, nullable=True)
    manual_protein_g = db.Column(db.Numeric(8, 2), nullable=True)
    manual_carbs_g = db.Column(db.Numeric(8, 2), nullable=True)
    manual_fat_g = db.Column(db.Numeric(8, 2), nullable=True)
