import csv
import os
import sys

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.models.ingredient import FoodIngredient

def import_ingredients():
    app = create_app()
    
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'utils', 'Nutrisi Bahan Pangan - CAPSTONE .csv')
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    with app.app_context():
        print("Starting ingredient import...")
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                added_count = 0
                updated_count = 0
                
                for row in reader:
                    if not row or len(row) < 5:
                        continue
                        
                    name = row[0].strip()
                    try:
                        calories = int(float(row[1])) # Handle "58" or "58.0"
                        protein = float(row[2])
                        fat = float(row[3])
                        carbs = float(row[4])
                    except ValueError as e:
                        print(f"Skipping row for {name}: Invalid data - {e}")
                        continue
                    
                    ingredient = FoodIngredient.query.filter_by(name=name).first()
                    
                    if ingredient:
                        ingredient.calories = calories
                        ingredient.protein_g = protein
                        ingredient.fat_g = fat
                        ingredient.carbs_g = carbs
                        updated_count += 1
                        print(f"Updated: {name}")
                    else:
                        new_ingredient = FoodIngredient(
                            name=name,
                            calories=calories,
                            protein_g=protein,
                            fat_g=fat,
                            carbs_g=carbs
                        )
                        db.session.add(new_ingredient)
                        added_count += 1
                        print(f"Added: {name}")
                
                db.session.commit()
                print(f"\nImport complete!")
                print(f"Added: {added_count}")
                print(f"Updated: {updated_count}")
                
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    import_ingredients()
