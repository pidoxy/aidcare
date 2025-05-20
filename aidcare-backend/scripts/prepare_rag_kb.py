import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss 

# --- Configuration ---
CHO_ORDERS_FILEPATH = "national_standing_orders_cho.json" 
CHEW_ORDERS_FILEPATH = "national_standing_orders_chew.json"
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2' 

OUTPUT_FAISS_INDEX_PATH = "guidelines_index.faiss"
OUTPUT_METADATA_PATH = "guidelines_metadata.json"

# --- Helper Functions ---
def load_json_data(filepath, source_doc_name):
    """Loads JSON data and adds a source document name."""
    if not os.path.exists(filepath):
        print(f"Warning: File not found at '{filepath}'. Skipping.")
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for section in data.get("sections", []):
            section['source_document'] = source_doc_name
        print(f"Successfully loaded and tagged data from '{filepath}'")
        return data.get("sections", [])
    except Exception as e:
        print(f"Error loading or processing '{filepath}': {e}")
        return []

def create_text_chunks_from_guidelines(all_sections_data):
    """
    Processes guideline data into searchable text chunks and corresponding metadata.
    Each 'entry' will become a chunk.
    """
    chunks = []
    metadata = []

    for section in all_sections_data:
        section_title = section.get("title", "N/A")
        source_doc = section.get("source_document", "N/A")
        age_group = section.get("age_group", "")

        for subsection in section.get("subsections", []):
            subsection_title = subsection.get("title", "N/A")
            subsection_code = subsection.get("code", "N/A")

            for entry in subsection.get("entries", []):
                case = entry.get("case", "N/A")
                history_items = entry.get("history", [])
                examination_items = entry.get("examination", [])
                # For CHEW, 'notes' might also be relevant. For CHO, 'clinical_judgement' and 'action'
                # are more for Phase 5, but some keywords might be useful for retrieval.
                # Let's focus on case, history, examination for retrieval for now.

                history_text = ". ".join(history_items) if history_items else "No specific history listed."
                # For examination, we might want to be selective, or just join them.
                # For simplicity now, let's join them.
                examination_text = ". ".join(examination_items) if examination_items else "No specific examination points listed."

                # Construct the text chunk for embedding
                # The more descriptive this chunk, the better the semantic search.
                chunk_text = (
                    f"Document: {source_doc}. Section: {section_title}. Age group: {age_group}. "
                    f"Subsection: {subsection_title} (Code: {subsection_code}). "
                    f"Case: {case}. "
                    f"History includes: {history_text}. "
                    f"Examination may involve: {examination_text}."
                )
                chunks.append(chunk_text)
                
                # Store metadata. We'll retrieve this alongside the relevant chunk.
                # Phase 5 will use 'clinical_judgement' and 'action'.
                entry_metadata = {
                    "source_document": source_doc,
                    "section_title": section_title,
                    "age_group": age_group,
                    "subsection_code": subsection_code,
                    "subsection_title": subsection_title,
                    "case": case,
                    "history": history_items,
                    "examination": examination_items,
                    "clinical_judgement": entry.get("clinical_judgement", ""),
                    "action": entry.get("action", []),
                    "notes": entry.get("notes", []), # From CHEW data
                    "original_text_chunk": chunk_text # For reference
                }
                metadata.append(entry_metadata)
                
    print(f"Created {len(chunks)} text chunks from guidelines.")
    return chunks, metadata

# --- Main Script ---
if __name__ == "__main__":
    # 1. Load CHO and CHEW data
    print("Loading guideline data...")
    cho_sections = load_json_data(CHO_ORDERS_FILEPATH, "CHO Guidelines")
    chew_sections = load_json_data(CHEW_ORDERS_FILEPATH, "CHEW Guidelines")
    
    all_guideline_sections = []
    if cho_sections:
        all_guideline_sections.extend(cho_sections)
    if chew_sections:
        all_guideline_sections.extend(chew_sections)

    if not all_guideline_sections:
        print("No guideline data loaded. Exiting.")
        exit()

    # 2. Create text chunks
    print("\nCreating text chunks for embedding...")
    text_chunks, guideline_metadata = create_text_chunks_from_guidelines(all_guideline_sections)

    if not text_chunks:
        print("No text chunks created. Exiting.")
        exit()
    
    # Print a sample chunk and its metadata
    print(f"\nSample Chunk (0): {text_chunks[0]}")
    print(f"Sample Metadata (0): {json.dumps(guideline_metadata[0], indent=2)}")


    # 3. Load Sentence Transformer model
    print(f"\nLoading sentence transformer model: {EMBEDDING_MODEL_NAME}...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("Model loaded.")

    # 4. Generate embeddings for all chunks
    print("\nGenerating embeddings for guideline chunks... (This may take a while)")
    chunk_embeddings = model.encode(text_chunks, show_progress_bar=True, convert_to_numpy=True)
    print(f"Generated {chunk_embeddings.shape[0]} embeddings of dimension {chunk_embeddings.shape[1]}.")

    # 5. Create and populate FAISS index
    print("\nCreating FAISS index...")
    dimension = chunk_embeddings.shape[1]
    # Using IndexFlatL2, a simple brute-force L2 distance search. Good for moderate number of vectors.
    # For very large datasets, more complex indexes like IndexIVFFlat might be better.
    index = faiss.IndexFlatL2(dimension) 
    index.add(chunk_embeddings) # Add embeddings to the index
    print(f"FAISS index created and populated. Total vectors in index: {index.ntotal}")

    # 6. Save the FAISS index and the metadata
    print(f"\nSaving FAISS index to: {OUTPUT_FAISS_INDEX_PATH}")
    faiss.write_index(index, OUTPUT_FAISS_INDEX_PATH)
    
    print(f"Saving metadata to: {OUTPUT_METADATA_PATH}")
    with open(OUTPUT_METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(guideline_metadata, f, indent=2)

    print("\n--- Knowledge Base Preparation Complete! ---")
    print(f"Index and metadata are ready for Phase 4B (Retrieval).")

    # Optional: Test a quick retrieval (example)
    if index.ntotal > 0:
        print("\n--- Quick Retrieval Test ---")
        test_symptoms = ["fever", "cough", "difficulty breathing"]
        test_query_text = f"Patient presents with symptoms: {', '.join(test_symptoms)}."
        print(f"Test Query: {test_query_text}")
        
        query_embedding = model.encode([test_query_text], convert_to_numpy=True)
        
        k = 3 # Number of top results to retrieve
        distances, indices = index.search(query_embedding, k) # Search the index
        
        print(f"\nTop {k} retrieved guideline entries:")
        for i in range(k):
            retrieved_idx = indices[0][i]
            retrieved_metadata = guideline_metadata[retrieved_idx]
            print(f"\nRank {i+1} (Distance: {distances[0][i]:.4f}):")
            print(f"  Source: {retrieved_metadata['source_document']}")
            print(f"  Section: {retrieved_metadata['section_title']}")
            print(f"  Subsection: {retrieved_metadata['subsection_title']} (Code: {retrieved_metadata['subsection_code']})")
            print(f"  Case: {retrieved_metadata['case']}")