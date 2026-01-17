import os
import re
from collections import Counter
from google import genai
from google.genai import types
from flask import current_app

from app.services.rag.processor import DocumentProcessor
from app.services.rag.vector_store import VectorStore

class RAGService:
    """
    RAG Service yang dioptimalkan untuk kesehatan ibu dan anak.
    Menggunakan Hybrid Search: Menggabungkan Pencarian Vektor (Semantik) 
    dan Pencarian Keyword untuk akurasi maksimal.
    """
    
    def __init__(self, data_dir=None):
        self.chunks = []
        self.client = None
        self.processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.data_dir = data_dir
        
        self.stopwords = {'yang', 'dan', 'di', 'ke', 'dari', 'pada', 'untuk', 'adalah', 
                          'dengan', 'atau', 'ini', 'itu', 'dalam', 'akan', 'telah', 
                          'juga', 'oleh', 'sebagai', 'dapat', 'karena', 'apa', 'bagaimana'}
        
        api_key = current_app.config.get("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        
        if data_dir and os.path.exists(data_dir):
            self._load_data(data_dir)
    
    def _load_data(self, data_dir):
        """Load data menggunakan DocumentProcessor dan siapkan VectorStore."""
        csv_path = os.path.join(data_dir, 'dataset_final.csv')
        index_path = os.path.join(data_dir, 'bunda_care_vector')
        
        if os.path.exists(csv_path):
            # 1. Load teks asli menggunakan processor
            self.chunks = self.processor.load_csv(csv_path)
            print(f"Loaded {len(self.chunks)} chunks from CSV using DocumentProcessor")
            
            # 2. Coba load index FAISS jika sudah ada, jika tidak, buat baru
            if os.path.exists(f"{index_path}.index"):
                print("Loading existing vector index...")
                self.vector_store.load(index_path)
            else:
                print("Building new vector index (this may take a moment)...")
                self.vector_store.create_index(self.chunks)
                self.vector_store.save(index_path)
        else:
            print(f"CSV file not found: {csv_path}")
    
    def _normalize_text(self, text):
        """Normalisasi text untuk matching yang lebih baik."""
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_keywords(self, text):
        """Extract keywords dengan filtering stopwords."""
        text = self._normalize_text(text)
        words = re.findall(r'\b\w+\b', text)
        keywords = [w for w in words if w not in self.stopwords and len(w) > 2]
        return keywords
    
    def _calculate_keyword_score(self, chunk, query_keywords):
        """Hitung skor relevansi berbasis kata kunci."""
        chunk_lower = self._normalize_text(chunk)
        score = 0
        
        for keyword in query_keywords:
            count = chunk_lower.count(keyword)
            if count > 0:
                score += (count * 10) + (count ** 0.5 * 5)
                try:
                    position = chunk_lower.index(keyword)
                    position_bonus = max(0, 50 - (position / 10))
                    score += position_bonus
                except ValueError:
                    pass
        
        query_text = ' '.join(query_keywords)
        if query_text in chunk_lower:
            score += 100
        
        return score
    
    def rag_search(self, query):
        """
        Hybrid Search: Menggabungkan kelebihan Vector Search dan Keyword Search.
        """
        if not self.chunks:
            return ""
        
        # 1. Semantic Search (Model AI)
        # Menemukan hasil yang mirip secara makna meski kata-katanya berbeda
        semantic_results = self.vector_store.search(query, top_k=10)
        
        # 2. Keyword Search (Manual)
        # Menemukan hasil yang mengandung kata-kata spesifik yang tepat
        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            query_keywords = [self._normalize_text(query)]
            
        scored_chunks = {}
        
        # Beri skor awal dari hasil semantic search
        for i, chunk in enumerate(semantic_results):
            # Hasil teratas diberi skor lebih tinggi
            semantic_score = (10 - i) * 20 
            scored_chunks[chunk] = semantic_score
            
        # Tambahkan skor dari keyword matching
        for chunk in self.chunks:
            k_score = self._calculate_keyword_score(chunk, query_keywords)
            if k_score > 0:
                if chunk in scored_chunks:
                    scored_chunks[chunk] += k_score
                else:
                    scored_chunks[chunk] = k_score
        
        # Urutkan berdasarkan total skor tertinggi
        sorted_results = sorted(scored_chunks.items(), key=lambda x: x[1], reverse=True)
        
        # Ambil top 15 untuk konteks Gemini
        top_chunks = [item[0] for item in sorted_results[:15]]
        
        return "\n---\n".join(top_chunks)
    
    def generate_answer(self, query, context):
        """Menghasilkan jawaban yang akurat dan informatif menggunakan Gemini."""
        if not self.client:
            return "Konfigurasi AI belum lengkap. Silakan periksa GEMINI_API_KEY di pengaturan."

        if not context:
            return "Maaf Bunda, saya tidak menemukan informasi yang relevan dalam database untuk pertanyaan tersebut. Silakan coba pertanyaan lain atau hubungi tenaga kesehatan profesional."

        system_prompt = (
            "Anda adalah 'Bunda Care AI Assistant', asisten kesehatan ibu dan anak sekaligus panduan penggunaan aplikasi Bunda Care yang terpercaya.\n\n"
            "INSTRUKSI PENTING:\n"
            "1. Jawablah secara LENGKAP, terstruktur, dan tuntas mengenai kesehatan maupun cara penggunaan fitur aplikasi (Scan, Edukasi, Rekomendasi, dll).\n"
            "2. Gunakan bahasa Indonesia yang ramah, hangat, dan sangat profesional.\n"
            "3. WAJIB menggunakan format Markdown yang rapi (H2/H3 untuk judul, bullet points untuk daftar).\n"
            "4. BERSIHKAN TEKS: Jangan menyertakan simbol aneh seperti ']', quotation marks yang tidak perlu, atau karakter rusak dari database.\n"
            "5. Berikan jawaban yang AKURAT berdasarkan informasi di KONTEKS saja.\n"
            "6. Gunakan sapaan 'Bunda' atau 'Ayah'.\n"
            "7. Pastikan kalimat terakhir selesai dengan tanda titik dan merupakan penutup yang baik.\n"
            "8. TUNTASKAN JAWABAN: Pastikan pesan tidak berhenti di tengah kalimat. Selesaikan seluruh penjelasan sampai benar-benar selesai dengan penutup yang sopan.\n"
            "9. JANGAN TERPOTONG: Jika jawaban dirasa akan terlalu panjang, ringkaslah penjelasan agar tetap masuk dalam satu respon utuh yang tuntas.\n"
            "10. Selalu ingatkan untuk konsultasi dengan tenaga kesehatan untuk keputusan medis.\n\n"
            "LARANGAN:\n"
            "- JANGAN menyertakan karakter sampah seperti `]`, `“`, atau header yang rusak.\n"
            "- JANGAN mengarang fakta di luar KONTEKS.\n"
            "- JANGAN memberikan diagnosis medis.\n"
        )
        
        full_prompt = (
            f"{system_prompt}\n\n"
            f"KONTEKS DARI DATABASE BUNDA CARE:\n"
            f"{context}\n\n"
            f"PERTANYAAN BUNDA: {query}\n\n"
            f"JAWABAN ANDA:"
        )

        try:
            safety_settings = [
                types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
            ]

            response = self.client.models.generate_content(
                model='gemini-flash-latest',
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=2048,
                    top_p=0.9,
                    top_k=40,
                    safety_settings=safety_settings
                )
            )
            
            if response and response.text:
                return response.text.strip()
            else:
                current_app.logger.warning(f"Empty response from Gemini for query: {query}")
                return (
                    "Maaf Bunda, saya mengalami kendala dalam memproses jawaban saat ini. "
                    "Silakan coba beberapa saat lagi atau hubungi administrator jika masalah berlanjut."
                )
                
        except Exception as e:
            current_app.logger.error(f"Gemini API Error: {str(e)}")
            return (
                "Terjadi kesalahan teknis saat memproses pertanyaan Bunda. "
                "Tim kami telah mencatat masalah ini. Silakan coba lagi dalam beberapa saat."
            )

    def chat(self, query):
        """
        Entry point utama untuk RAG chat.
        """
        if not query or len(query.strip()) < 3:
            return "Maaf Bunda, pertanyaan terlalu pendek. Silakan jelaskan pertanyaan Bunda dengan lebih detail."
        
        context = self.rag_search(query)
        return self.generate_answer(query, context)
