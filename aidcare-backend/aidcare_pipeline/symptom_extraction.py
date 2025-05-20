# aidcare_pipeline/symptom_extraction.py
import google.generativeai as genai
import json
import os
import time

GEMINI_MODEL_NAME_EXTRACTION = os.getenv("GEMINI_MODEL_EXTRACTION", 'gemini-1.5-flash-latest')
GOOGLE_API_KEY_SYMPTOMS = os.environ.get("GOOGLE_API_KEY") # Expect API key from environment

def extract_symptoms_with_gemini(transcript_text: str) -> list:
    if not GOOGLE_API_KEY_SYMPTOMS:
        raise ValueError("GOOGLE_API_KEY not found in environment for symptom extraction.")
    
    genai.configure(api_key=GOOGLE_API_KEY_SYMPTOMS)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME_EXTRACTION)
    
    system_instruction = (
        "You are an expert medical information extractor..." # Keep your good system prompt
    )
    prompt = f"""
    Transcript:
    ---
    {transcript_text}
    ---
    Based on the transcript above, extract all symptoms mentioned.
    Return the symptoms as a JSON formatted list of strings.
    For example: ["headache", "fever", "cough"]
    If no symptoms are clearly mentioned, return an empty JSON list: []
    Symptoms (JSON list):
    """
    # ... (rest of your Gemini call and robust JSON parsing logic from extract_symptoms_gemini.py)
    # ... (ensure it returns a list of strings)

    # Simplified for brevity, ensure your robust parsing is here
    generation_config = genai.types.GenerationConfig(temperature=0.1, max_output_tokens=256)
    full_prompt = system_instruction + "\n\n" + prompt if not GEMINI_MODEL_NAME_EXTRACTION.startswith('gemini-1.5') else prompt
    
    if GEMINI_MODEL_NAME_EXTRACTION.startswith('gemini-1.5'):
        model_instance = genai.GenerativeModel(
            GEMINI_MODEL_NAME_EXTRACTION,
            system_instruction=system_instruction, # Pass system instruction here
            generation_config=generation_config
        )
        response = model_instance.generate_content(prompt) # User prompt only
    else:
        model_instance = model
        response = model_instance.generate_content(full_prompt, generation_config=generation_config)

    # Your robust JSON parsing from extract_symptoms_gemini.py
    # Placeholder for brevity:
    try:
        if not response.parts:
            # Handle no parts, potentially access response.text
            if hasattr(response, 'text') and response.text:
                 raw_json_str = response.text.strip()
            else:
                print("Error: No content in Gemini symptom response")
                return []
        else:
            raw_json_str = response.parts[0].text.strip()

        if raw_json_str.startswith("```json"): raw_json_str = raw_json_str[7:]
        if raw_json_str.endswith("```"): raw_json_str = raw_json_str[:-3]
        raw_json_str = raw_json_str.strip()
        
        if not raw_json_str: return []
        data = json.loads(raw_json_str)
        
        s_list = []
        if isinstance(data, list): s_list = data
        elif isinstance(data, dict):
            for key in ["symptoms", "extracted_symptoms", "symptom_list"]:
                if key in data and isinstance(data[key], list):
                    s_list = data[key]
                    break
        return [str(s).lower().strip() for s in s_list if str(s).strip()]
    except Exception as e:
        print(f"Error in Gemini symptom extraction processing: {e}")
        raise # Re-raise