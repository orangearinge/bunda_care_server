import os
import re
from collections import Counter
from google import genai
from google.genai import types
from flask import current_app

class RAGService:
    """
    RAG Service yang dioptimalkan untuk kesehatan ibu dan anak.
    Menggunakan TF-IDF sederhana dan keyword expansion untuk pencarian yang lebih akurat.
    """
    
    def __init__(self, data_dir=None):
        self.chunks = []
        self.client = None
        self.stopwords = {'yang', 'dan', 'di', 'ke', 'dari', 'pada', 'untuk', 'adalah', 
                          'dengan', 'atau', 'ini', 'itu', 'dalam', 'akan', 'telah', 
                          'juga', 'oleh', 'sebagai', 'dapat', 'karena', 'apa', 'bagaimana'}
        
        api_key = current_app.config.get("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        
        if data_dir and os.path.exists(data_dir):
            self._load_data(data_dir)
    
    def _load_data(self, data_dir):
        """Load chunks dari CSV file dengan preprocessing."""
        import csv
        csv_path = os.path.join(data_dir, 'dataset_final.csv')
        
        if os.path.exists(csv_path):
            with open(csv_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'sentence' in row and row['sentence']:
                        # Simpan original text
                        self.chunks.append(row['sentence'].strip())
            
            print(f"Loaded {len(self.chunks)} chunks from CSV")
        else:
            print(f"CSV file not found: {csv_path}")
    
    def _normalize_text(self, text):
        """Normalisasi text untuk matching yang lebih baik."""
        # Lowercase
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_keywords(self, text):
        """Extract keywords dengan filtering stopwords."""
        text = self._normalize_text(text)
        # Split by non-alphanumeric
        words = re.findall(r'\b\w+\b', text)
        # Filter stopwords and short words
        keywords = [w for w in words if w not in self.stopwords and len(w) > 2]
        return keywords
    
    def _calculate_relevance_score(self, chunk, query_keywords):
        """
        Hitung skor relevansi menggunakan multiple factors:
        1. Keyword frequency
        2. Keyword position (earlier is better)
        3. Phrase matching (bonus for consecutive keywords)
        """
        chunk_lower = self._normalize_text(chunk)
        score = 0
        
        # Factor 1: Keyword frequency with TF weighting
        chunk_words = chunk_lower.split()
        for keyword in query_keywords:
            count = chunk_lower.count(keyword)
            if count > 0:
                # TF score: more occurrences = higher score, but with diminishing returns
                score += (count * 10) + (count ** 0.5 * 5)
                
                # Factor 2: Position bonus (keywords appearing early get bonus)
                try:
                    position = chunk_lower.index(keyword)
                    position_bonus = max(0, 50 - (position / 10))  # Max 50 points for position 0
                    score += position_bonus
                except ValueError:
                    pass
        
        # Factor 3: Phrase matching bonus
        query_text = ' '.join(query_keywords)
        if query_text in chunk_lower:
            score += 100  # Big bonus for exact phrase match
        
        # Factor 4: Partial phrase matching (consecutive keywords)
        for i in range(len(query_keywords) - 1):
            two_word_phrase = f"{query_keywords[i]} {query_keywords[i+1]}"
            if two_word_phrase in chunk_lower:
                score += 30
        
        return score
    
    def rag_search(self, query):
        """
        Optimized semantic search dengan multiple ranking factors.
        """
        if not self.chunks:
            return ""
        
        # Extract keywords dari query
        query_keywords = self._extract_keywords(query)
        
        if not query_keywords:
            # Jika tidak ada keywords (query sangat pendek), gunakan query langsung
            query_keywords = [self._normalize_text(query)]
        
        # Calculate relevance score untuk setiap chunk
        scored_chunks = []
        for chunk in self.chunks:
            score = self._calculate_relevance_score(chunk, query_keywords)
            if score > 0:
                scored_chunks.append((score, chunk))
        
        # Sort by score descending
        scored_chunks.sort(reverse=True, key=lambda x: x[0])
        
        # Ambil top 20 untuk diversity, tapi tetap relevant
        top_chunks = [chunk for score, chunk in scored_chunks[:20]]
        
        return "\n---\n".join(top_chunks)
    
    def generate_answer(self, query, context):
        """Menghasilkan jawaban yang akurat dan informatif menggunakan Gemini."""
        if not self.client:
            return "Konfigurasi AI belum lengkap. Silakan periksa GEMINI_API_KEY di pengaturan."

        if not context:
            return "Maaf Bunda, saya tidak menemukan informasi yang relevan dalam database untuk pertanyaan tersebut. Silakan coba pertanyaan lain atau hubungi tenaga kesehatan profesional."

        system_prompt = (
            "Anda adalah 'Bunda Care AI Assistant', asisten kesehatan ibu dan anak yang terpercaya.\n\n"
            "INSTRUKSI PENTING:\n"
            "1. Berikan jawaban yang AKURAT berdasarkan informasi di KONTEKS.\n"
            "2. Gunakan bahasa Indonesia yang ramah, hangat, dan profesional.\n"
            "3. Susun jawaban dalam 2-4 paragraf yang mudah dipahami.\n"
            "4. Jika ada data penting (angka, durasi, istilah medis), sebutkan dengan jelas.\n"
            "5. Gunakan sapaan 'Bunda' atau 'Ayah' untuk membuat percakapan lebih personal.\n"
            "6. Jika informasi di KONTEKS tidak lengkap untuk menjawab sepenuhnya, "
            "katakan dengan jujur bagian mana yang belum tersedia.\n"
            "7. Selalu ingatkan untuk konsultasi dengan tenaga kesehatan untuk keputusan medis.\n\n"
            "LARANGAN:\n"
            "- JANGAN mengarang fakta yang tidak ada di KONTEKS\n"
            "- JANGAN memberikan diagnosis medis\n"
            "- JANGAN menggunakan pengetahuan di luar KONTEKS yang diberikan\n"
        )
        
        full_prompt = (
            f"{system_prompt}\n\n"
            f"KONTEKS DARI DATABASE BUNDA CARE:\n"
            f"{context}\n\n"
            f"PERTANYAAN BUNDA: {query}\n\n"
            f"JAWABAN ANDA:"
        )

        try:
            # Safety settings untuk konten kesehatan
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
                    temperature=0.2,  # Rendah untuk akurasi, tapi tidak 0 agar bahasa tetap natural
                    max_output_tokens=1200,  # Cukup untuk jawaban detail
                    top_p=0.9,  # Fokus pada token dengan probabilitas tinggi
                    top_k=40,  # Batasi pilihan token untuk konsistensi
                    safety_settings=safety_settings
                )
            )
            
            if response and response.text:
                return response.text.strip()
            else:
                # Log untuk debugging
                current_app.logger.warning(f"Empty response from Gemini for query: {query}")
                return (
                    "Maaf Bunda, saya mengalami kendala dalam memproses jawaban saat ini. "
                    "Silakan coba beberapa saat lagi atau hubungi administrator jika masalah berlanjut."
                )
                
        except Exception as e:
            current_app.logger.error(f"Gemini API Error: {str(e)}")
            # Jangan expose error detail ke user
            return (
                "Terjadi kesalahan teknis saat memproses pertanyaan Bunda. "
                "Tim kami telah mencatat masalah ini. Silakan coba lagi dalam beberapa saat."
            )

    def chat(self, query):
        """
        Entry point utama untuk RAG chat.
        Menggabungkan retrieval dan generation.
        """
        # Input validation
        if not query or len(query.strip()) < 3:
            return "Maaf Bunda, pertanyaan terlalu pendek. Silakan jelaskan pertanyaan Bunda dengan lebih detail."
        
        # Retrieve relevant context
        context = self.rag_search(query)
        
        # Generate answer
        return self.generate_answer(query, context)
