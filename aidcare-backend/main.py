# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import time
import json
import asyncio # For async placeholders if needed, or running sync code in threadpool

# --- Import your AI pipeline modules ---
from aidcare_pipeline.transcription import transcribe_audio_local, load_whisper_model
from aidcare_pipeline.symptom_extraction import extract_symptoms_with_gemini
from aidcare_pipeline.rag_retrieval import get_guideline_retriever, GuidelineRetriever # Import class for type hinting
from aidcare_pipeline.recommendation import generate_triage_recommendation

# --- Environment Variable Checks & Setup ---
if not os.environ.get("GOOGLE_API_KEY"):
    print("CRITICAL WARNING: GOOGLE_API_KEY environment variable is not set. Gemini calls will fail.")

TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# --- FastAPI App Initialization & Lifespan Events for Model Loading ---
app = FastAPI(title="AidCare AI Assistant API")

app_state = {} 

@app.on_event("startup")
async def startup_event():
    """
    Load models and resources when the FastAPI application starts.
    """
    print("FastAPI app starting up...")
    # Load Whisper model (this will initialize asr_pipeline_global in transcription.py)
    print("Initializing Whisper model...")
    load_whisper_model() 
    
    # Load RAG Guideline Retriever
    print("Initializing Guideline Retriever...")
    app_state["guideline_retriever"] = get_guideline_retriever()
    
    print("FastAPI app startup complete. Models loaded.")

@app.on_event("shutdown")
async def shutdown_event():
    print("FastAPI app shutting down.")
    # Add any cleanup logic here if necessary


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], # Your Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency for RAG Retriever ---
def get_retriever() -> GuidelineRetriever:
    retriever = app_state.get("guideline_retriever")
    if not retriever:
        # This should ideally not happen if startup event worked
        print("CRITICAL: GuidelineRetriever not found in app_state. Re-initializing.")
        retriever = get_guideline_retriever() # Attempt to load it again
        app_state["guideline_retriever"] = retriever
    return retriever

# --- API Endpoints ---
@app.post("/triage/process_audio/")
async def process_audio_for_triage(
    audio_file: UploadFile = File(...),
    retriever: GuidelineRetriever = Depends(get_retriever) # Dependency injection
):
    # Generate a unique filename to avoid collisions, or use a UUID
    unique_suffix = f"{int(time.time() * 1000)}_{audio_file.filename}"
    file_path = os.path.join(TEMP_AUDIO_DIR, unique_suffix)

    try:
        # Save uploaded file temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        print(f"Audio file saved to {file_path}")

        # --- Phase 2: Audio -> Text (Local Whisper) ---
        # FastAPI runs synchronous blocking IO in a thread pool automatically.
        # So, direct calls to your (now synchronous) AI functions are fine.
        print("Starting Phase 2: Transcription...")
        transcript = transcribe_audio_local(file_path)
        if not transcript:
            raise HTTPException(status_code=500, detail="Transcription failed or returned empty.")
        print(f"Phase 2 Complete. Transcript: {transcript[:100]}...")

        # --- Phase 3: Symptom Extraction (Gemini API) ---
        print("Starting Phase 3: Symptom Extraction...")
        symptoms = extract_symptoms_with_gemini(transcript)
        if not symptoms and "error" not in symptoms : # if empty list is valid (no symptoms) allow it
             print("Phase 3 Complete. No symptoms extracted (or valid empty list).")
        elif "error" in symptoms: # Check if Gemini function returned an error structure
            raise HTTPException(status_code=500, detail=f"Symptom extraction failed: {symptoms.get('error')}")
        else:
            print(f"Phase 3 Complete. Extracted Symptoms: {symptoms}")


        # --- Phase 4: RAG Triage Engine (Local RAG) ---
        print("Starting Phase 4: Guideline Retrieval...")
        retrieved_docs = retriever.retrieve_relevant_guidelines(symptoms, top_k=3)
        print(f"Phase 4 Complete. Retrieved {len(retrieved_docs)} guideline documents.")

        # --- Phase 5: Triage Recommendation (Gemini API) ---
        print("Starting Phase 5: Recommendation Generation...")
        recommendation = generate_triage_recommendation(symptoms, retrieved_docs)
        if not recommendation or "error" in recommendation:
            error_detail = recommendation.get("error") if recommendation else "Unknown error"
            raise HTTPException(status_code=500, detail=f"Failed to generate recommendation: {error_detail}")
        print("Phase 5 Complete. Recommendation generated.")
        
        return {
            "transcript": transcript,
            "extracted_symptoms": symptoms,
            "retrieved_guidelines_summary": [
                {
                    "source": d.get("source_document"),
                    "code": d.get("subsection_code"),
                    "case": d.get("case"),
                    "score": d.get("retrieval_score (distance)")
                } for d in retrieved_docs
            ],
            "triage_recommendation": recommendation
        }

    except FileNotFoundError as e:
        print(f"File not found error: {e}")
        raise HTTPException(status_code=404, detail=f"Required file not found: {e}")
    except ValueError as e: # For API key issues etc.
        print(f"Value error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e # Re-raise FastAPI's own HTTP exceptions
    except Exception as e:
        print(f"Unhandled error processing audio: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    finally:
        # Clean up temporary audio file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Temporary audio file {file_path} removed.")
            except Exception as e_rem:
                print(f"Error removing temporary file {file_path}: {e_rem}")

@app.get("/")
async def read_root():
    return {"message": "Welcome to AidCare API. Use /docs for API documentation and health check."}

@app.get("/health")
async def health_check():
    # Basic health check: verify models seem loaded
    whisper_ok = True # Assume loaded via startup, or check a flag
    rag_retriever_ok = "guideline_retriever" in app_state and app_state["guideline_retriever"] is not None
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "whisper_model": "initialized" if whisper_ok else "not_initialized",
            "rag_retriever": "initialized" if rag_retriever_ok else "not_initialized",
            "gemini_api_connectivity": "dependent_on_key_and_network"
        }
    }

@app.post("/test_upload/")
async def test_upload_endpoint(file: UploadFile = File(...)):
    print(f"Received file: {file.filename}")
    print(f"Content type: {file.content_type}")
    return {"filename": file.filename, "content_type": file.content_type}