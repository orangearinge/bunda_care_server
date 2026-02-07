import os
import csv
from typing import List
from pypdf import PdfReader

class DocumentProcessor:
    """
    Bertanggung jawab untuk memuat dokumen (PDF/CSV) dan memecahnya menjadi potongan kecil (chunking).
    """

    @staticmethod
    def load_csv(file_path: str, column_name: str = 'sentence') -> List[str]:
        """
        Membaca file CSV dan mengembalikan list teks dari kolom tertentu.
        
        Args:
            file_path: Path ke file CSV.
            column_name: Nama kolom yang akan diambil teksnya.
            
        Returns:
            List[str]: List teks yang berhasil diekstrak.
        """
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
    def load_pdf(file_path: str) -> str:
        """
        Membaca file PDF dan mengekstrak teksnya.
        
        Args:
            file_path: Path ke file PDF.
            
        Returns:
            str: Teks yang berhasil diekstrak dari PDF.
        """
        text = ""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error loading PDF {file_path}: {e}")
        return text

    @staticmethod
    def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """
        Memecah teks panjang menjadi potongan-potongan kecil.
        
        Args:
            text: Teks yang akan dipecah.
            chunk_size: Ukuran maksimal setiap potongan (karakter).
            chunk_overlap: Jumlah karakter yang tumpang tindih antar potongan.
            
        Returns:
            List[str]: List potongan teks.
        """
        if not text:
            return []
            
        chunks = []
        # Menggunakan step (chunk_size - chunk_overlap) untuk membuat overlap
        for i in range(0, len(text), chunk_size - chunk_overlap):
            chunks.append(text[i:i + chunk_size])
        return chunks

    def process_file(self, file_path: str) -> List[str]:
        """
        Memproses satu file berdasarkan ekstensinya.
        
        Args:
            file_path: Path ke file yang akan diproses.
            
        Returns:
            List[str]: List potongan teks (chunks).
        """
        if file_path.endswith(".pdf"):
            text = self.load_pdf(file_path)
            return self.split_text(text)
        elif file_path.endswith(".csv"):
            # Untuk CSV dataset_final, kita ambil baris per baris sebagai chunk
            return self.load_csv(file_path)
        return []

    def process_directory(self, directory_path: str) -> List[str]:
        """
        Memproses semua file yang didukung di direktori.
        
        Args:
            directory_path: Path ke direktori berisi file-file.
            
        Returns:
            List[str]: Kumpulan semua chunks dari semua file.
        """
        all_chunks = []
        if not os.path.exists(directory_path):
            return all_chunks
            
        for filename in os.listdir(directory_path):
            path = os.path.join(directory_path, filename)
            if os.path.isfile(path):
                chunks = self.process_file(path)
                all_chunks.extend(chunks)
        return all_chunks
