import os
from app import create_app
from app.extensions import db
from app.models.role import Role
from app.models.user import User
from app.utils.auth import hash_password

app = create_app()

with app.app_context():
    # Ensure ADMIN role exists
    admin_role = Role.query.filter_by(name='ADMIN').first()
    if not admin_role:
        admin_role = Role(name='ADMIN', description='Administrator')
        db.session.add(admin_role)
        db.session.commit()
        print('Created ADMIN role')
    else:
        print('ADMIN role already exists')

    # Ensure admin user exists
    admin_email = 'admin@example.com'
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            name='Admin User',
            email=admin_email,
            password=hash_password('adminpass'),
            role=admin_role
        )
        db.session.add(admin_user)
        db.session.commit()
        print('Created admin user')
    else:
        print('Admin user already exists')
