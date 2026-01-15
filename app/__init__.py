from flask import Flask
from app.extensions import db, cors
from flask_migrate import Migrate
from app.routes import register_routes
from app.models.user import User
from app.models.role import Role
from app.utils.auth import hash_password
import time
import logging

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Initialize database dengan retry mechanism untuk menangani SSL EOF
    _init_database_with_retry(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # CORS Configuration
    cors.init_app(app,
                  origins="*",
                  supports_credentials=True,
                  allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
                  methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                  expose_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"])

    register_routes(app)

    return app

def _init_database_with_retry(app, max_retries=3, retry_delay=2):
    """Initialize database dengan retry mechanism untuk menangani koneksi SSL EOF"""
    for attempt in range(max_retries):
        try:
            db.init_app(app)
            # Test koneksi dengan query sederhana
            with app.app_context():
                with db.engine.connect() as conn:
                    conn.execute(db.text("SELECT 1"))
                    conn.commit()
            logger.info("Database connection established successfully")
            return
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Failed to establish database connection after all retries")
                raise e
