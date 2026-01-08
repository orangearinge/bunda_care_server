from app.extensions import db
from app.models.role import Role

# Define the required roles for the application
REQUIRED_ROLES = [
    {"name": "ADMIN", "description": "Administrator with full access"},
    {"name": "IBU_HAMIL", "description": "Pregnant mother"},
    {"name": "IBU_MENYUSUI", "description": "Post‑natal mother"},
    {"name": "ANAK_BATITA", "description": "Infant 0-24 months"},
]

def seed_roles():
    """Create missing roles in the database.

    This function can be executed manually (e.g., ``python -m app.scripts.seed_roles``)
    after migrations have been applied. It checks for each role in ``REQUIRED_ROLES``
    and inserts it if it does not already exist.
    """
    for role_data in REQUIRED_ROLES:
        role = Role.query.filter_by(name=role_data["name"]).first()
        if not role:
            role = Role(name=role_data["name"], description=role_data.get("description"))
            db.session.add(role)
            print(f"Added role: {role.name}")
    db.session.commit()
    print("Role seeding complete.")

if __name__ == "__main__":
    # When run as a script, ensure the Flask app context is available.
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_roles()
