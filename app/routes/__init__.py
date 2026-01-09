from .home_routes import home_bp
from .auth_routes import auth_bp
from .user_routes import user_bp
from .food_routes import food_bp
from .ingredient_routes import bp as ingredient_bp
from .admin_routes import admin_bp
from .test_routes import test_bp
from .chat_routes import chat_bp
from .article_routes import article_bp

def register_routes(app):
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(food_bp)
    app.register_blueprint(ingredient_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(article_bp)
