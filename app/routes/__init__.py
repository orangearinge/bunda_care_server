from .home_routes import home_bp
from .auth_routes import auth_bp
from .user_routes import user_bp
from .food_routes import food_bp

def register_routes(app):
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(food_bp)
