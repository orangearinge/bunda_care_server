from flask import Flask
from app.extensions import db, cors
from flask_migrate import Migrate
from app.routes import register_routes
from app.models.user import User
from app.models.role import Role
from app.utils.auth import hash_password

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Initialize database
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # CORS Configuration
    cors.init_app(app, 
                  origins=["http://localhost:5173"],
                  supports_credentials=True,
                  allow_headers=["Content-Type", "Authorization"],
                  methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                  expose_headers=["Content-Type", "Authorization"])

    register_routes(app)

    return app
