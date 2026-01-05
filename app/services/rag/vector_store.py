import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import os
import pickle

class VectorStore:
    """
    Mengelola penyimpanan vektor dan pencarian kemiripan (similarity search).
    """
    
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        # Load model embedding (lokal & ringan)
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.metadata = [] # Menyimpan teks asli berdasarkan index

    def create_index(self, chunks):
        """Membuat index FAISS dari kumpulan text chunks."""
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

    def search(self, query, top_k=3):
        """Mencari chunks yang paling relevan dengan query."""
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

    def save(self, file_path):
        """Menyimpan index ke file agar tidak perlu rebuild setiap saat."""
        if self.index:
            faiss.write_index(self.index, f"{file_path}.index")
            with open(f"{file_path}.pkl", 'wb') as f:
                pickle.dump(self.metadata, f)

    def load(self, file_path):
        """Memuat index dari file."""
        if os.path.exists(f"{file_path}.index"):
            self.index = faiss.read_index(f"{file_path}.index")
            with open(f"{file_path}.pkl", 'rb') as f:
                self.metadata = pickle.load(f)
