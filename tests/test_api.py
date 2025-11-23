import json
import datetime as dt
import os
import importlib.util
import sys
import pytest
from werkzeug.security import generate_password_hash

# Load create_app from package file path to avoid clash with root app.py
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INIT_PATH = os.path.join(ROOT_DIR, 'app', '__init__.py')
sys.path.insert(0, ROOT_DIR)
spec = importlib.util.spec_from_file_location(
    'app', INIT_PATH, submodule_search_locations=[os.path.join(ROOT_DIR, 'app')]
)
app_pkg = importlib.util.module_from_spec(spec)
app_pkg.__path__ = [os.path.join(ROOT_DIR, 'app')]  # type: ignore
sys.modules['app'] = app_pkg
assert spec and spec.loader
spec.loader.exec_module(app_pkg)  # type: ignore
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.role import Role
from app.models.ingredient import FoodIngredient
from app.models.menu import FoodMenu
from app.models.menu_ingredient import FoodMenuIngredient


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        db.create_all()
        # seed roles
        for name, desc in [
            ("IBU_HAMIL", "Ibu hamil"),
            ("IBU_MENYUSUI", "Ibu menyusui"),
            ("ANAK_BALITA", "Anak balita"),
            ("ADMIN", "Administrator"),
        ]:
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name, description=desc))
        db.session.commit()

        # seed user without role
        if not User.query.filter_by(email="user@example.com").first():
            u = User(name="User Demo", email="user@example.com", password=generate_password_hash("secret"))
            db.session.add(u)
            db.session.commit()

        # seed ingredients (raw preferred vs cooked)
        def add_ing(name, cal, p, c, f, alt=""):
            if not FoodIngredient.query.filter_by(name=name).first():
                from decimal import Decimal
                db.session.add(FoodIngredient(
                    name=name, alt_names=alt, calories=cal,
                    protein_g=Decimal(str(p)), carbs_g=Decimal(str(c)), fat_g=Decimal(str(f))
                ))
        add_ing("Dada ayam", 165, 31.0, 0.0, 3.6, alt="ayam, chicken, chicken breast, dada, fillet ayam")
        add_ing("Paha ayam", 209, 26.0, 0.0, 10.9, alt="ayam, chicken, chicken thigh, paha")
        add_ing("Ayam panggang", 239, 27.3, 0.0, 13.6, alt="ayam panggang, roast chicken")
        add_ing("Oat", 389, 16.9, 66.3, 6.9)
        add_ing("Telur", 155, 13.0, 1.1, 11.0)
        add_ing("Pisang", 89, 1.1, 22.8, 0.3)
        add_ing("Nasi putih", 130, 2.7, 28.0, 0.3)
        add_ing("Sayur campur", 40, 2.0, 7.0, 0.3)
        db.session.commit()

        # seed menus
        def ensure_menu(name, meal_type, items):
            m = FoodMenu.query.filter_by(name=name).first()
            if not m:
                m = FoodMenu(name=name, meal_type=meal_type, tags="umum")
                db.session.add(m); db.session.flush()
                for ing_name, qty in items:
                    ing = FoodIngredient.query.filter_by(name=ing_name).first()
                    db.session.add(FoodMenuIngredient(menu_id=m.id, ingredient_id=ing.id, quantity_g=qty))
                db.session.commit()
            return m
        ensure_menu("Oat + Telur + Pisang", "BREAKFAST", [("Oat",60),("Telur",50),("Pisang",100)])
        ensure_menu("Nasi + Ayam + Sayur", "LUNCH", [("Nasi putih",200),("Ayam panggang",120),("Sayur campur",100)])

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_login_and_preference_role_sync(client, app):
    # login
    r = client.post("/api/auth/login", json={"email":"user@example.com","password":"secret"})
    assert r.status_code == 200, r.data
    token = r.get_json()["token"]

    # upsert preference with role: IBU_HAMIL
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "role": "IBU_HAMIL",
        "height_cm": 160,
        "weight_kg": 60,
        "age_year": 28,
        "gestational_age_week": 22,
        "belly_circumference_cm": 90,
        "lila_cm": 24
    }
    r2 = client.post("/api/user/preference", json=body, headers=headers)
    assert r2.status_code == 200, r2.data
    data = r2.get_json()
    assert data["role"] == "IBU_HAMIL"
    assert "token" in data  # refreshed token after role set


def test_scan_food_prefers_raw(client, app):
    # login again
    r = client.post("/api/auth/login", json={"email":"user@example.com","password":"secret"})
    token = r.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # simulate upload using empty file-like (recognize() stub ignores content)
    from io import BytesIO
    data = {"image": (BytesIO(b"fake"), "ayam_panggang.jpg")}
    r2 = client.post("/api/scan-food", content_type='multipart/form-data', headers=headers, data=data)
    assert r2.status_code == 200, r2.data
    cands = r2.get_json().get("candidates", [])
    assert len(cands) >= 1
    # ensure raw appears among candidates and preferably first
    names = [c["name"].lower() for c in cands]
    assert any("dada" in n or "paha" in n for n in names)


def test_food_log_create_and_list(client, app):
    r = client.post("/api/auth/login", json={"email":"user@example.com","password":"secret"})
    token = r.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create food log for Dada ayam 120g
    with app.app_context():
        ing = FoodIngredient.query.filter_by(name="Dada ayam").first()
    r2 = client.post("/api/food-log", headers=headers, json={
        "items": [{"ingredient_id": ing.id, "quantity_g": 120}]
    })
    assert r2.status_code == 201, r2.data

    # list recent
    r3 = client.get("/api/food-log?limit=5", headers=headers)
    assert r3.status_code == 200
    items = r3.get_json().get("items", [])
    assert any(it["ingredient_name"] == "Dada ayam" for it in items)


def test_recommendation_role_targets_and_options(client, app):
    r = client.post("/api/auth/login", json={"email":"user@example.com","password":"secret"})
    token = r.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ibu hamil recommendation
    r2 = client.get("/api/recommendation?days=1&options_per_meal=2", headers=headers)
    assert r2.status_code == 200, r2.data
    data = r2.get_json()
    assert "days" in data and len(data["days"]) == 1
    day = data["days"][0]
    assert "daily_target" in day and "bmi" in day["daily_target"]
    # meals contains best pick and options blocks
    meal_blocks = day["meals"]
    # ensure there is at least one options block per meal type
    meal_types = [m.get("meal_type") for m in meal_blocks]
    assert meal_types.count("BREAKFAST") >= 2  # best + options
    # options must have food_log_payload
    options_blocks = [m for m in meal_blocks if isinstance(m.get("options"), list)]
    assert options_blocks, "options block missing"
    assert all("food_log_payload" in opt for blk in options_blocks for opt in blk["options"])
