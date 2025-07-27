import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class DynamicBookManager:
    def __init__(self, index_path="book_index.faiss", metadata_path="books_metadata.pkl"):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.load_data()

    def load_data(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.metadata_path, 'rb') as f:
            self.metadata = pickle.load(f)

    def save_data(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)

    def embed(self, text):
        emb = self.model.encode([text], convert_to_numpy=True)
        return (emb / np.linalg.norm(emb)).astype('float32')

    def add_book(self, book_details):
        desc = f"{book_details['title']}. {book_details['description']}"
        embedding = self.embed(desc)
        self.index.add(embedding)
        self.metadata.append(book_details)
        self.save_data()
        return "Book successfully added."

    def remove_book(self, title):
        idx_to_remove = next((i for i, b in enumerate(self.metadata) if b['title'].lower() == title.lower()), None)
        if idx_to_remove is None:
            return "Book not found."

        self.metadata.pop(idx_to_remove)

        embeddings = np.vstack([self.embed(f"{b['title']}. {b['description']}") for b in self.metadata])
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
        self.save_data()
        return "Book successfully removed."

