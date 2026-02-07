import os
import pickle
import numpy as np
import faiss
from typing import List, Optional
from sentence_transformers import SentenceTransformer

class VectorStore:
    """
    Mengelola penyimpanan vektor dan pencarian kemiripan (similarity search).
    Menggunakan model SentenceTransformer untuk embedding dan FAISS untuk indexing.
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Inisialisasi VectorStore dengan model embedding tertentu.
        
        Args:
            model_name: Nama model SentenceTransformer yang digunakan.
        """
        # Load model embedding (lokal & ringan)
        self.model = SentenceTransformer(model_name)
        self.index: Optional[faiss.IndexFlatL2] = None
        self.metadata: List[str] = [] # Menyimpan teks asli berdasarkan index

    def create_index(self, chunks: List[str]) -> None:
        """
        Membuat index FAISS dari kumpulan text chunks.
        
        Args:
            chunks: Kumpulan potongan teks yang akan di-index.
        """
        if not chunks:
            return
            
        self.metadata = chunks
        embeddings = self.model.encode(chunks)
        
        # Dimensi vektor berdasarkan model
        dimension = embeddings.shape[1]
        
        # Menggunakan IndexFlatL2 untuk pencarian euclidean (cocok untuk dataset kecil-menengah)
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(np.array(embeddings).astype('float32'))
        
        print(f"Index created with {len(chunks)} chunks.")

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """
        Mencari chunks yang paling relevan dengan query.
        
        Args:
            query: Teks pencarian.
            top_k: Jumlah hasil terbaik yang dikembalikan.
            
        Returns:
            List[str]: Kumpulan potongan teks yang paling relevan.
        """
        if self.index is None:
            return []
            
        query_vector = self.model.encode([query])
        distances, indices = self.index.search(np.array(query_vector).astype('float32'), top_k)
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx != -1: # FAISS mengembalikan -1 jika tidak ada hasil
                results.append(self.metadata[idx])
        
        return results

    def save(self, file_path: str) -> None:
        """
        Menyimpan index ke file agar tidak perlu rebuild setiap saat.
        
        Args:
            file_path: Path (tanpa ekstensi) tempat menyimpan index dan metadata.
        """
        if self.index:
            faiss.write_index(self.index, f"{file_path}.index")
            with open(f"{file_path}.pkl", 'wb') as f:
                pickle.dump(self.metadata, f)

    def load(self, file_path: str) -> None:
        """
        Memuat index dari file.
        
        Args:
            file_path: Path (tanpa ekstensi) file index dan metadata.
        """
        if os.path.exists(f"{file_path}.index"):
            self.index = faiss.read_index(f"{file_path}.index")
            with open(f"{file_path}.pkl", 'rb') as f:
                self.metadata = pickle.load(f)
