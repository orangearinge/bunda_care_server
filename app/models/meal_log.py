from app.extensions import db

class FoodMealLog(db.Model):
    __tablename__ = "food_meal_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey("food_menus.id"), nullable=False)
    total_calories = db.Column(db.Integer, nullable=False, default=0)
    total_protein_g = db.Column(db.Numeric(10,2), nullable=False, default=0)
    total_carbs_g = db.Column(db.Numeric(10,2), nullable=False, default=0)
    total_fat_g = db.Column(db.Numeric(10,2), nullable=False, default=0)
    servings = db.Column(db.Numeric(8,2), nullable=False, default=1)
    is_consumed = db.Column(db.Boolean, default=False, nullable=False)
    logged_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class FoodMealLogItem(db.Model):
    __tablename__ = "food_meal_log_items"

    id = db.Column(db.Integer, primary_key=True)
    meal_log_id = db.Column(db.Integer, db.ForeignKey("food_meal_logs.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("food_ingredients.id"), nullable=False)
    quantity_g = db.Column(db.Numeric(8,2), nullable=False)
    calories = db.Column(db.Integer, nullable=False, default=0)
    protein_g = db.Column(db.Numeric(10,2), nullable=False, default=0)
    carbs_g = db.Column(db.Numeric(10,2), nullable=False, default=0)
    fat_g = db.Column(db.Numeric(10,2), nullable=False, default=0)
