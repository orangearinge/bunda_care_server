import os
import logging
from gradio_client import Client
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Mengambil URL dari environment variable atau menggunakan default
GRADIO_API_URL = os.getenv("GRADIO_API_URL", "boyblanco/indobert-feedback")

def classify_feedback(text: str) -> Optional[str]:
    """
    Mengirimkan teks feedback ke model AI Gradio untuk klasifikasi.
    
    Args:
        text (str): Teks feedback dari user.
        
    Returns:
        Optional[str]: Label hasil klasifikasi (misal: "Positif", "Negatif") atau None jika gagal.
    """
    if not text:
        return None

    try:
        # Peringatan: Inisialisasi Client bisa memakan waktu jika harus mengunduh metadata.
        # Dalam produksi, idealnya Client diinisialisasi sekali secara global.
        # Namun untuk stabilitas jika API berubah, kita inisialisasi di sini atau gunakan pola Singleton.
        client = Client(GRADIO_API_URL)
        
        # Mengirim request ke endpoint /predict
        # Sesuai snippet yang diberikan user
        result = client.predict(
            text=text,
            api_name="/predict"
        )
        
        logger.info(f"AI Classification result for '{text[:20]}...': {result}")
        
        # Result bisa berupa string label atau struktur lain. 
        # Berdasarkan snippet user: "Returns 1 element... str | float | bool | list | dict"
        # Kita asumsikan ini mengembalikan label string langsung atau list yang berisi label.
        # Kita lakukan sedikit normalisasi.
        
        if isinstance(result, list):
            # Jika returns list, ambil elemen pertama
            return str(result[0])
        elif isinstance(result, dict):
            # Jika returns dict, coba cari label (ini tebakan safe handling)
            return str(result.get('label', result))
        else:
            return str(result)
            
    except Exception as e:
        logger.error(f"Error classifying feedback: {e}")
        # Jangan throw error agar proses feedback user tidak gagal hanya karena AI error
        return None
