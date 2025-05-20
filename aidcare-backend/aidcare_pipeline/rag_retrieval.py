# aidcare_pipeline/rag_retrieval.py
import json
import os
import faiss
from sentence_transformers import SentenceTransformer

FAISS_INDEX_PATH_RAG = os.getenv("FAISS_INDEX_PATH", "guidelines_index.faiss")
METADATA_PATH_RAG = os.getenv("METADATA_PATH", "guidelines_metadata.json")
EMBEDDING_MODEL_NAME_RAG = os.getenv("EMBEDDING_MODEL_RAG", 'all-MiniLM-L6-v2')

class GuidelineRetriever:
    def __init__(self): # Removed parameters, will load from constants/env vars
        if not os.path.exists(FAISS_INDEX_PATH_RAG):
            raise FileNotFoundError(f"FAISS index file not found: {FAISS_INDEX_PATH_RAG}")
        if not os.path.exists(METADATA_PATH_RAG):
            raise FileNotFoundError(f"Metadata file not found: {METADATA_PATH_RAG}")

        print(f"Loading RAG FAISS index from: {FAISS_INDEX_PATH_RAG}")
        self.index = faiss.read_index(FAISS_INDEX_PATH_RAG)
        print(f"RAG FAISS index loaded. Total vectors: {self.index.ntotal}")

        print(f"Loading RAG metadata from: {METADATA_PATH_RAG}")
        with open(METADATA_PATH_RAG, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
        print(f"RAG Metadata loaded. Total entries: {len(self.metadata)}")

        print(f"Loading RAG sentence transformer model: {EMBEDDING_MODEL_NAME_RAG}...")
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME_RAG)
        print("RAG Sentence transformer model loaded.")

    def retrieve_relevant_guidelines(self, symptoms_list: list, top_k: int = 3) -> list:
        # ... (Keep your existing retrieve_relevant_guidelines method logic here) ...
        # ... (ensure it returns a list of metadata dictionaries) ...
        if not symptoms_list or self.index.ntotal == 0: return []
        query_text = f"Patient symptoms: {', '.join(symptoms_list)}."
        query_embedding = self.model.encode([query_text], convert_to_numpy=True)
        distances, indices = self.index.search(query_embedding, top_k)
        
        retrieved_entries = []
        if indices.size > 0:
            for i in range(min(top_k, len(indices[0]))):
                retrieved_idx = indices[0][i]
                if 0 <= retrieved_idx < len(self.metadata):
                    entry_metadata = self.metadata[retrieved_idx]
                    entry_metadata['retrieval_score (distance)'] = float(distances[0][i])
                    retrieved_entries.append(entry_metadata)
        return retrieved_entries

# Global instance to be loaded once
guideline_retriever_instance = None

def get_guideline_retriever():
    global guideline_retriever_instance
    if guideline_retriever_instance is None:
        print("Initializing GuidelineRetriever instance...")
        guideline_retriever_instance = GuidelineRetriever()
    return guideline_retriever_instance