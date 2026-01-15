from flask import jsonify
from app.extensions import db

def home_index():
    return jsonify({
        "message": "Backend Flask berhasil menggunakan struktur modular!",
    })

def health_check():
    db_status = "healthy"
    try:
        # Ping the database
        db.session.execute(db.text('SELECT 1'))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        
    return jsonify({
        "status": "online",
        "database": db_status,
        "server_time": db.func.now() if db_status == "healthy" else None
    })
