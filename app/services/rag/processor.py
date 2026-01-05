import os
import csv
from pypdf import PdfReader

class DocumentProcessor:
    """
    Bertanggung jawab untuk memuat dokumen (PDF/CSV) dan memecahnya menjadi potongan kecil (chunking).
    """
    
    @staticmethod
    def load_pdf(file_path):
        """Membaca file PDF dan mengembalikan teks lengkap."""
        text = ""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error loading PDF {file_path}: {e}")
        return text

    @staticmethod
    def load_csv(file_path, column_name='sentence'):
        """Membaca file CSV dan mengembalikan list teks dari kolom tertentu."""
        texts = []
        try:
            # Menggunakan utf-8-sig untuk menangani BOM (\ufeff)
            with open(file_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if column_name in row and row[column_name]:
                        texts.append(row[column_name])
        except Exception as e:
            print(f"Error loading CSV {file_path}: {e}")
        return texts

    @staticmethod
    def split_text(text, chunk_size=500, chunk_overlap=50):
        """
        Memecah teks panjang menjadi potongan-potongan kecil.
        """
        if not text:
            return []
        chunks = []
        for i in range(0, len(text), chunk_size - chunk_overlap):
            chunks.append(text[i:i + chunk_size])
        return chunks

    def process_file(self, file_path):
        """Memproses satu file berdasarkan ekstensinya."""
        if file_path.endswith(".pdf"):
            text = self.load_pdf(file_path)
            return self.split_text(text)
        elif file_path.endswith(".csv"):
            # Untuk CSV dataset_final, kita ambil baris per baris sebagai chunk
            return self.load_csv(file_path)
        return []

    def process_directory(self, directory_path):
        """Memproses semua file yang didukung di direktori."""
        all_chunks = []
        if not os.path.exists(directory_path):
            return all_chunks
            
        for filename in os.listdir(directory_path):
            path = os.path.join(directory_path, filename)
            chunks = self.process_file(path)
            all_chunks.extend(chunks)
        return all_chunks
