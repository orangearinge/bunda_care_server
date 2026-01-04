from app import create_app
from app.extensions import db
from app.models.ingredient import FoodIngredient

app = create_app()
with app.app_context():
    data = [
        {"name": "Daging Ayam", "alt_names": "chicken meat", "calories": 239, "protein_g": 27.0, "carbs_g": 0.0, "fat_g": 14.0},
        {"name": "Nasi Putih", "alt_names": "white rice", "calories": 130, "protein_g": 2.7, "carbs_g": 28.0, "fat_g": 0.3},
        {"name": "Telur Rebus", "alt_names": "boiled egg", "calories": 155, "protein_g": 13.0, "carbs_g": 1.1, "fat_g": 11.0},
        {"name": "Wortel", "alt_names": "carrot", "calories": 41, "protein_g": 0.9, "carbs_g": 10.0, "fat_g": 0.2},
    ]
    
    for item in data:
        existing = FoodIngredient.query.filter_by(name=item["name"]).first()
        if not existing:
            ing = FoodIngredient(**item)
            db.session.add(ing)
            print(f"Added: {item['name']}")
    
    db.session.commit()
    print("Seeding complete.")
