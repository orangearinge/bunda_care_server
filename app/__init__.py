from flask import Flask
from app.extensions import db
from app.routes import register_routes
from app.models.user import User
from app.models.role import Role

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    register_routes(app)

    return app
