from flask import jsonify

def home_index():
    return jsonify({
        "message": "Backend Flask berhasil menggunakan struktur modular!",
    })
