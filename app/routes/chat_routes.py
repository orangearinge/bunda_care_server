from flask import Blueprint, request, jsonify, current_app
from app.services.rag.rag_service import RAGService
from app.utils.auth import require_auth
from app.models.user import User
from app.models.preference import UserPreference
import os

chat_bp = Blueprint('chat', __name__,url_prefix='/api')

# Kita gunakan lazy initialization agar config app sudah tersedia saat service dibuat
_rag_service = None

def get_rag_service():
    global _rag_service
    if _rag_service is None:
        # Gunakan path data_dir dari argument atau default
        # Kita juga menambahkan path ke CSV dataset_final secara spesifik jika ada
        data_dir = os.path.join(current_app.root_path, 'services', 'rag')
        _rag_service = RAGService(data_dir=data_dir)
    return _rag_service

@chat_bp.route('/chat', methods=['POST'])
@require_auth
def chat():
    """
    Endpoint utama untuk bertanya pada bot RAG.
    Format JSON: {"query": "Apa itu periode emas?"}
    """
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({"error": "Query tidak boleh kosong"}), 400
        
    query = data['query']
    
    try:
        # 1. Ambil Data Profil User untuk Konteks
        user_id = request.user_id
        user = User.query.get(user_id)
        pref = UserPreference.query.get(user_id)
        
        user_context = f"Nama: {user.name}\n"
        if pref:
            role_display = "Ibu Hamil" if pref.role == 'IBU_HAMIL' else "Orang Tua/Anak Balita"
            user_context += f"Status: {role_display}\n"
            
            if pref.height_cm: user_context += f"Tinggi: {pref.height_cm} cm\n"
            if pref.weight_kg: user_context += f"Berat: {pref.weight_kg} kg\n"
            
            if pref.role == 'IBU_HAMIL':
                if pref.gestational_age_weeks is not None:
                    user_context += f"Usia Kehamilan: {pref.gestational_age_weeks} minggu\n"
                if pref.lila_cm:
                    user_context += f"LiLA: {pref.lila_cm} cm\n"
            elif pref.role == 'ANAK_BALITA':
                age_str = ""
                if pref.age_year: age_str += f"{pref.age_year} tahun "
                if pref.age_month: age_str += f"{pref.age_month} bulan"
                if age_str: user_context += f"Usia Anak: {age_str}\n"
                
            if pref.food_prohibitions:
                user_context += f"Pantangan: {', '.join(pref.food_prohibitions)}\n"
            if pref.allergens:
                user_context += f"Alergi: {', '.join(pref.allergens)}\n"

        # 2. Panggil Service dengan Konteks User
        service = get_rag_service()
        answer = service.chat(query, user_context=user_context)
        return jsonify({
            "query": query,
            "answer": answer,
            "status": "success"
        })
    except Exception as e:
        current_app.logger.error(f"RAG Error: {str(e)}")
        return jsonify({
            "error": "Terjadi kesalahan internal pada sistem RAG.",
            "message": str(e),
            "status": "failed"
        }), 500

@chat_bp.route('/chat/rebuild', methods=['POST'])
def rebuild_index():
    """
    Endpoint untuk memperbarui index jika ada dokumen/dataset baru.
    """
    try:
        global _rag_service
        _rag_service = None # Reset agar di-init ulang
        get_rag_service()
        return jsonify({"message": "Index berhasil diperbarui dengan dataset terbaru"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
