from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.ingredient import FoodIngredient
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient
from app.models.role import Role
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # ensure tables exist (non-destructive: won't alter existing columns)
    db.create_all()
    # user
    if not User.query.filter_by(email="user@example.com").first():
        role = Role.query.filter_by(name="IBU_HAMIL").first()
        if not role:
            role = Role(name="IBU_HAMIL", description="Ibu hamil")
            db.session.add(role)
            db.session.flush()
        u = User(name="User Demo", email="user@example.com",
                 password=generate_password_hash("secret"), role=role)
        db.session.add(u)

    def add_ing(name, cal, p, c, f):
        from decimal import Decimal
        if not FoodIngredient.query.filter_by(name=name).first():
            db.session.add(FoodIngredient(
                name=name, calories=cal,
                protein_g=Decimal(str(p)),
                carbs_g=Decimal(str(c)),
                fat_g=Decimal(str(f))
            ))

    add_ing("Oat", 389, 16.9, 66.3, 6.9)
    add_ing("Telur", 155, 13.0, 1.1, 11.0)
    add_ing("Pisang", 89, 1.1, 22.8, 0.3)
    add_ing("Ayam panggang", 239, 27.3, 0.0, 13.6)
    add_ing("Nasi putih", 130, 2.7, 28.0, 0.3)
    add_ing("Sayur campur", 40, 2.0, 7.0, 0.3)

    db.session.flush()

    if not FoodMenu.query.filter_by(name="Oat + Telur + Pisang").first():
        m1 = FoodMenu(name="Oat + Telur + Pisang", meal_type="BREAKFAST", tags="umum,ibu_hamil")
        db.session.add(m1)
        db.session.flush()

        db.session.add(FoodMenuIngredient(menu_id=m1.id,
                                          ingredient_id=FoodIngredient.query.filter_by(name="Oat").first().id,
                                          quantity_g=60))
        db.session.add(FoodMenuIngredient(menu_id=m1.id,
                                          ingredient_id=FoodIngredient.query.filter_by(name="Telur").first().id,
                                          quantity_g=50))
        db.session.add(FoodMenuIngredient(menu_id=m1.id,
                                          ingredient_id=FoodIngredient.query.filter_by(name="Pisang").first().id,
                                          quantity_g=100))

    if not FoodMenu.query.filter_by(name="Nasi + Ayam + Sayur").first():
        m2 = FoodMenu(name="Nasi + Ayam + Sayur", meal_type="LUNCH", tags="umum,protein")
        db.session.add(m2)
        db.session.flush()

        db.session.add(FoodMenuIngredient(menu_id=m2.id,
                                          ingredient_id=FoodIngredient.query.filter_by(name="Nasi putih").first().id,
                                          quantity_g=200))
        db.session.add(FoodMenuIngredient(menu_id=m2.id,
                                          ingredient_id=FoodIngredient.query.filter_by(name="Ayam panggang").first().id,
                                          quantity_g=120))
        db.session.add(FoodMenuIngredient(menu_id=m2.id,
                                          ingredient_id=FoodIngredient.query.filter_by(name="Sayur campur").first().id,
                                          quantity_g=100))

    db.session.commit()

    print("✅ Seed completed.")
