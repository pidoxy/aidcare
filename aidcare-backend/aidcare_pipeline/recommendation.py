# aidcare_pipeline/recommendation.py
import google.generativeai as genai
import json
import os
import time

GEMINI_MODEL_NAME_RECOMMEND = os.getenv("GEMINI_MODEL_RECOMMEND", 'gemini-1.5-flash-latest')
GOOGLE_API_KEY_RECOMMEND = os.environ.get("GOOGLE_API_KEY")

def generate_triage_recommendation(symptoms_list: list, retrieved_guideline_entries: list) -> dict:
    if not GOOGLE_API_KEY_RECOMMEND:
        # In a real app, you might want to raise an exception or handle this more gracefully
        print("ERROR: GOOGLE_API_KEY not found in environment for recommendation generation.")
        return {
            "error": "Configuration error: Missing Google API Key for recommendations."
        }

    try:
        genai.configure(api_key=GOOGLE_API_KEY_RECOMMEND)
    except Exception as e:
        print(f"Error configuring Gemini API key for recommendation: {e}")
        return {"error": f"Gemini API key configuration error: {e}"}

    model = genai.GenerativeModel(GEMINI_MODEL_NAME_RECOMMEND)
    
    context_str = "Relevant Guideline Information:\n"
    if not retrieved_guideline_entries:
        context_str += "No specific guideline entries were retrieved. Base recommendation on general knowledge for the given symptoms, if possible, or state that specific guidelines are needed for a definitive recommendation path.\n"
    else:
        for i, entry in enumerate(retrieved_guideline_entries[:3]): # Using top 3 relevant entries
            context_str += f"\n--- Guideline Entry {i+1} ---\n"
            context_str += f"Source Document: {entry.get('source_document', 'N/A')}\n"
            context_str += f"Section: {entry.get('section_title', 'N/A')}\n"
            context_str += f"Subsection: {entry.get('subsection_title', 'N/A')} (Code: {entry.get('subsection_code', 'N/A')})\n"
            context_str += f"Case/Condition: {entry.get('case', 'N/A')}\n"
            context_str += f"Clinical Judgement from Guideline: {entry.get('clinical_judgement', 'N/A')}\n"
            actions = entry.get('action', [])
            if isinstance(actions, list):
                context_str += f"Recommended Actions from Guideline: {'; '.join(actions)}\n"
            else:
                context_str += f"Recommended Actions from Guideline: {actions}\n"
            notes = entry.get('notes', [])
            if notes:
                if isinstance(notes, list):
                    context_str += f"Notes from Guideline: {'; '.join(notes)}\n"
                else:
                    context_str += f"Notes from Guideline: {notes}\n"

    symptoms_str = ", ".join(symptoms_list) if symptoms_list else "No specific symptoms reported by patient."

    system_instruction = (
        "You are an AI Medical Assistant for Community Health Workers (CHWs) in Nigeria, designed to provide triage recommendations. "
        "Your response MUST be strictly grounded in the provided 'Relevant Guideline Information'. "
        "Do NOT invent information or actions not present in the guidelines. "
        "You do NOT make definitive diagnoses. You help the CHW determine appropriate next steps based on the guidelines. "
        "The output should be clear, concise, and directly actionable for a CHW. "
        "Determine an urgency level based on the guidelines (e.g., 'Routine Care', 'Refer to Clinic', 'Urgent Referral to Hospital', 'Immediate Emergency Care/Referral')."
    )

    prompt = f"""
    Patient Symptoms:
    {symptoms_str}

    {context_str}

    Task:
    Based ONLY on the patient symptoms and the provided 'Relevant Guideline Information', generate a triage recommendation for the CHW.
    Structure your response as a SINGLE JSON object with the following keys:
    - "summary_of_findings": (string) A brief summary of the situation and potential concerns, referencing the most relevant guideline entry.
    - "recommended_actions_for_chw": (list of strings) Specific, numbered, step-by-step actions the CHW should take, derived DIRECTLY from the 'Recommended Actions from Guideline' in the MOST RELEVANT provided context. If multiple guidelines are relevant, synthesize or pick the primary one.
    - "urgency_level": (string) The determined level of urgency based on the 'Clinical Judgement from Guideline' and 'Recommended Actions from Guideline' (e.g., "Routine Care", "Monitor at Home", "Refer to Clinic for Assessment", "Urgent Referral to Higher Facility/Hospital", "Immediate Emergency Referral").
    - "key_guideline_references": (list of strings) List the 'Source Document', 'Subsection Code' and 'Case' of the primary guideline(s) used for this recommendation (e.g., ["CHEW Guidelines - Code: 2.3, Case: Child with fever"]).
    - "important_notes_for_chw": (list of strings, optional) Any critical 'Notes from Guideline' or other crucial brief reminders for the CHW relevant to the situation.

    Example for "recommended_actions_for_chw": ["1. Measure temperature.", "2. If fever > 38.5C, give paracetamol.", "3. Advise on fluid intake."]
    
    If the provided guidelines are insufficient or contradictory for the given symptoms, clearly state that in the 'summary_of_findings' and recommend general caution or referral for further assessment.
    If no symptoms were reported and guidelines suggest routine care, reflect that.

    Return ONLY the JSON object. Do not include any text before or after the JSON object.
    JSON Response:
    """

    generation_config = genai.types.GenerationConfig(
        temperature=0.15, 
        max_output_tokens=1536, # Increased slightly
        # For Gemini 1.5 Flash, this is very helpful for ensuring JSON output
        # response_mime_type="application/json" 
    )
    
    # Construct model instance based on whether it's Gemini 1.5 or older (for system_instruction handling)
    if GEMINI_MODEL_NAME_RECOMMEND.startswith('gemini-1.5'):
        # For Gemini 1.5, set response_mime_type if you want the model to strictly output JSON
        # generation_config.response_mime_type="application/json" # Uncomment if using
        model_instance = genai.GenerativeModel(
            GEMINI_MODEL_NAME_RECOMMEND,
            system_instruction=system_instruction,
            generation_config=generation_config
        )
        user_prompt_for_1_5 = prompt # System instruction is handled by the model_instance
    else: # For gemini-1.0-pro
        model_instance = model
        user_prompt_for_1_5 = system_instruction + "\n\n" + prompt # Prepend system instruction

    print(f"Sending request to Gemini model '{GEMINI_MODEL_NAME_RECOMMEND}' for recommendation generation...")
    max_retries = 2 # Reduced retries for faster feedback during dev
    for attempt in range(max_retries):
        try:
            response = model_instance.generate_content(user_prompt_for_1_5)

            # Robust JSON extraction from response
            if not response.parts:
                raw_json_str = response.text.strip() if hasattr(response, 'text') and response.text else ""
            else:
                raw_json_str = response.parts[0].text.strip()

            # Clean markdown fences
            if raw_json_str.startswith("```json"): raw_json_str = raw_json_str[len("```json"):]
            if raw_json_str.startswith("```"): raw_json_str = raw_json_str[len("```"):]
            if raw_json_str.endswith("```"): raw_json_str = raw_json_str[:-len("```")]
            raw_json_str = raw_json_str.strip()
            
            print(f"Raw Gemini response content for recommendation (Attempt {attempt+1}): {raw_json_str}")

            if not raw_json_str:
                if attempt < max_retries - 1: time.sleep(1); continue
                print("Warning: Gemini returned an empty string for recommendation.")
                return {"error": "Gemini returned an empty response."}
                
            recommendation_json = json.loads(raw_json_str)
            # Basic validation of expected structure
            expected_keys = ["summary_of_findings", "recommended_actions_for_chw", "urgency_level", "key_guideline_references"]
            if not all(key in recommendation_json for key in expected_keys):
                print(f"Warning: Gemini response missing one or more expected keys. Got: {recommendation_json.keys()}")
                # Optionally, retry or return an error structure
            return recommendation_json

        except json.JSONDecodeError as e:
            print(f"Error: Could not decode JSON from Gemini recommendation response (Attempt {attempt+1}): '{raw_json_str}'. Error: {e}")
            if attempt < max_retries - 1: time.sleep(2 * (attempt + 1)); continue # Longer sleep before retry
            return {"error": f"Failed to decode JSON from Gemini after multiple attempts. Last response: {raw_json_str}"}
        except Exception as e:
            print(f"An error occurred during Gemini recommendation call (Attempt {attempt+1}): {e}")
            # Specific error handling for common API issues
            if "rate limit" in str(e).lower() or "quota" in str(e).lower() or "429" in str(e):
                print("Rate limit or quota error detected.")
                if attempt < max_retries - 1: time.sleep(10 * (attempt + 1)); continue # Much longer sleep
            elif attempt < max_retries -1: time.sleep(2 * (attempt + 1)); continue
            return {"error": f"Unhandled error during Gemini call: {e}"}
            
    print("Failed to get recommendation after all retries.")
    return {"error": "Failed to generate recommendation after multiple retries."}