from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLAlchemy Engine Configuration untuk Neon PostgreSQL
    # Mencegah SSL SYSCALL EOF error dengan connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Pool settings untuk menangani idle connection drops
        'pool_pre_ping': True,  # Test connection sebelum digunakan
        'pool_recycle': 300,    # Recycle connections setiap 5 menit
        'pool_size': 5,         # Jumlah connection dalam pool
        'max_overflow': 10,     # Maximum overflow connections
        'pool_timeout': 30,     # Timeout untuk mendapatkan connection dari pool

        # SSL settings untuk Neon (pastikan DATABASE_URL sudah include sslmode=require)
        'connect_args': {
            'sslmode': 'require',
            'connect_timeout': 10,  # Timeout untuk initial connection
        }
    }

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

