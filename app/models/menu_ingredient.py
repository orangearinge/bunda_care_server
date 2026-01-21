from app.extensions import db

class FoodMenuIngredient(db.Model):
    __tablename__ = "food_menu_ingredients"

    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey("food_menus.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("food_ingredients.id"), nullable=False)
    quantity_g = db.Column(db.Numeric(8,2), nullable=True)  # Now nullable for display-only ingredients
    display_quantity = db.Column(db.String(100), nullable=True)  # e.g., "3 lembar", "Secukupnya", "1 geprek"

    __table_args__ = (
        db.UniqueConstraint('menu_id', 'ingredient_id', name='uq_menu_ingredient'),
    )
