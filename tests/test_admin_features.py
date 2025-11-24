import json
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
spec.loader.exec_module(app_pkg)  # type: ignore
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.role import Role
from app.models.ingredient import FoodIngredient
from app.models.menu import FoodMenu

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
        for name in ["ADMIN", "USER"]:
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name))
        db.session.commit()

        # seed admin
        admin_role = Role.query.filter_by(name="ADMIN").first()
        if not User.query.filter_by(email="admin@example.com").first():
            u = User(name="Admin", email="admin@example.com", password=generate_password_hash("secret"), role=admin_role)
            db.session.add(u)
        
        # seed user
        user_role = Role.query.filter_by(name="USER").first()
        if not User.query.filter_by(email="user@example.com").first():
            u = User(name="User", email="user@example.com", password=generate_password_hash("secret"), role=user_role)
            db.session.add(u)
        
        db.session.commit()
    
    yield app

@pytest.fixture()
def client(app):
    return app.test_client()

def get_admin_token(client):
    r = client.post("/api/auth/login", json={"email":"admin@example.com","password":"secret"})
    return r.get_json()["token"]

def get_user_token(client):
    r = client.post("/api/auth/login", json={"email":"user@example.com","password":"secret"})
    return r.get_json()["token"]

def test_ingredient_crud(client, app):
    token = get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    r = client.post("/ingredients", headers=headers, json={
        "name": "Test Ingredient",
        "calories": 100,
        "protein_g": 10,
        "carbs_g": 5,
        "fat_g": 2
    })
    assert r.status_code == 201
    ing_id = r.get_json()["id"]

    # List
    r = client.get("/ingredients", headers=headers)
    assert r.status_code == 200
    assert any(i["id"] == ing_id for i in r.get_json())

    # Update
    r = client.put(f"/ingredients/{ing_id}", headers=headers, json={
        "name": "Updated Ingredient"
    })
    assert r.status_code == 200
    assert r.get_json()["name"] == "Updated Ingredient"

    # Delete
    r = client.delete(f"/ingredients/{ing_id}", headers=headers)
    assert r.status_code == 200

    # Verify Delete
    r = client.get("/ingredients", headers=headers)
    assert not any(i["id"] == ing_id for i in r.get_json())

def test_menu_crud(client, app):
    token = get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create Ingredient first
    r = client.post("/ingredients", headers=headers, json={
        "name": "Menu Ingredient",
        "calories": 50,
        "protein_g": 5,
        "carbs_g": 5,
        "fat_g": 1
    })
    ing_id = r.get_json()["id"]

    # Create Menu
    r = client.post("/api/menus", headers=headers, json={
        "name": "Test Menu",
        "meal_type": "BREAKFAST",
        "ingredients": [{"ingredient_id": ing_id, "quantity_g": 100}]
    })
    assert r.status_code == 201
    menu_id = r.get_json()["id"]

    # Get Detail
    r = client.get(f"/api/menus/{menu_id}", headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["name"] == "Test Menu"
    assert len(data["ingredients"]) == 1
    assert data["ingredients"][0]["ingredient_id"] == ing_id

    # Update
    r = client.put(f"/api/menus/{menu_id}", headers=headers, json={
        "name": "Updated Menu"
    })
    assert r.status_code == 200

    # Delete
    r = client.delete(f"/api/menus/{menu_id}", headers=headers)
    assert r.status_code == 200

def test_user_management(client, app):
    token = get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # List Users
    r = client.get("/admin/users", headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] >= 2 # Admin + User

    # Get User Detail
    # Find the user "User"
    user_item = next(u for u in data["items"] if u["email"] == "user@example.com")
    user_id = user_item["id"]

    r = client.get(f"/admin/users/{user_id}", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["role"] == "USER"

    # Update Role
    r = client.put(f"/admin/users/{user_id}/role", headers=headers, json={"role": "ADMIN"})
    assert r.status_code == 200
    assert r.get_json()["role"] == "ADMIN"

    # Verify Role Change
    r = client.get(f"/admin/users/{user_id}", headers=headers)
    assert r.get_json()["role"] == "ADMIN"

def test_dashboard(client, app):
    token = get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Stats
    r = client.get("/admin/dashboard/stats", headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "total_users" in data
    assert "total_active_menus" in data

    # User Growth
    r = client.get("/admin/dashboard/user-growth", headers=headers)
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    # Since we use in-memory sqlite, date functions might behave differently or return empty if no users created in range (but we seeded users).
    # However, sqlite doesn't support `func.date` the same way MySQL does usually, but SQLAlchemy tries to abstract it.
    # If it fails, we might need to adjust the test or controller for SQLite compatibility if we care about tests passing on SQLite.
    # But let's see.
