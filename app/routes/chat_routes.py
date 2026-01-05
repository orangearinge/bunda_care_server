from flask import Blueprint, request, jsonify, current_app
from app.services.rag.rag_service import RAGService
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
        service = get_rag_service()
        answer = service.chat(query)
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
