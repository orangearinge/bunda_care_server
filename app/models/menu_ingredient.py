from app.extensions import db

class FoodMenuIngredient(db.Model):
    __tablename__ = "food_menu_ingredients"

    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey("food_menus.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("food_ingredients.id"), nullable=True)
    quantity_g = db.Column(db.Numeric(8,2), nullable=True)  # Now nullable for display-only ingredients
    display_quantity = db.Column(db.String(100), nullable=True)  # e.g., "3 lembar", "Secukupnya", "1 geprek"

    # Removed uq_menu_ingredient to allow multiple manual text entries without IDs
