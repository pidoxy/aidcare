import google.generativeai as genai
import json
import os
import time # For potential rate limiting

# --- Configuration ---
# IMPORTANT: Set your Google API Key as an environment variable named 'GOOGLE_API_KEY'
# Or, for testing, you can uncomment and paste it here (less secure):
# GOOGLE_API_KEY = "YOUR_GEMINI_API_KEY_HERE" 
# if "GOOGLE_API_KEY" not in os.environ and not GOOGLE_API_KEY:
#     print("Error: GOOGLE_API_KEY not set as environment variable or in the script.")
#     exit()

# Model choice: 'gemini-1.0-pro-latest' is a good general model.
# 'gemini-1.5-flash-latest' is newer, faster, and has a large context window, good for this.
GEMINI_MODEL_NAME = 'gemini-1.5-flash-latest' # Or 'gemini-1.0-pro-latest'

# --- Gemini Symptom Extraction Function ---
def extract_symptoms_with_gemini(transcript_text, api_key_to_use):
    """
    Extracts symptoms from a transcript using the Google Gemini API.
    """
    # Configure the API key for this function call
    try:
        genai.configure(api_key=api_key_to_use)
    except Exception as e:
        print(f"Error configuring Gemini API key: {e}. Ensure the key is valid.")
        return []

    model = genai.GenerativeModel(GEMINI_MODEL_NAME)

    # System instruction (if using a model that supports it well, like Gemini 1.5 Flash)
    # For gemini-1.0-pro, you might blend this into the main prompt.
    system_instruction = (
        "You are an expert medical information extractor. Your task is to carefully read the provided "
        "CHW-patient conversation transcript and identify all symptoms mentioned by the patient or "
        "observed by the CHW. Focus on physical ailments, discomforts, or unusual conditions. "
        "List only the symptoms. Exclude diagnoses, treatments, and general statements like "
        "'I am not feeling well' unless accompanied by specific symptoms. "
        "Normalize symptom terms to common medical phrasing where appropriate (e.g., 'runny nose' to 'nasal discharge' or keep as 'runny nose' if more natural). "
        "Handle negations correctly (e.g., if the patient says 'no fever', do not list 'fever' as a symptom)."
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

    generation_config = genai.types.GenerationConfig(
        temperature=0.1,  # Lower temperature for more deterministic/factual output
        max_output_tokens=256, # Adjust as needed for expected list length
        # response_mime_type="application/json" # Use if API/model explicitly supports direct JSON output
                                               # For Gemini 1.5 Flash, this is very useful.
                                               # If not supported, Gemini will output a JSON string.
    )
    
    # For models that support system instructions well (like Gemini 1.5 Flash)
    # model_instance = genai.GenerativeModel(
    #     GEMINI_MODEL_NAME,
    #     system_instruction=system_instruction,
    #     generation_config=generation_config
    # )
    # For gemini-1.0-pro, you might combine system_instruction into the main prompt
    if GEMINI_MODEL_NAME.startswith('gemini-1.5'):
        model_instance = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            system_instruction=system_instruction,
            generation_config=generation_config
        )
        # If using response_mime_type="application/json" with Gemini 1.5 Flash
        # You'd set it in generation_config and the response would be a dict directly.
        # For now, let's assume text output that we parse.
    else: # For gemini-1.0-pro or if system_instruction isn't as effective
        model_instance = model # Use the model instance directly
        # Prepend system instruction to the user prompt for older models
        prompt = system_instruction + "\n\n" + prompt


    print(f"Sending request to Gemini model '{GEMINI_MODEL_NAME}' for symptom extraction...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model_instance.generate_content(prompt) # Pass generation_config if not set on model_instance

            # --- Robust JSON parsing ---
            if not response.parts:
                print("Warning: Gemini response has no parts. Raw response:", response)
                # Try to access response.text directly if available and no parts
                if hasattr(response, 'text') and response.text:
                    raw_json_str = response.text.strip()
                else: # If no text and no parts, it's an issue
                    print("Error: No content found in Gemini response.")
                    if attempt < max_retries - 1:
                        print(f"Retrying ({attempt+1}/{max_retries})...")
                        time.sleep(2**attempt) # Exponential backoff
                        continue
                    return [] # Give up after retries
            else:
                raw_json_str = response.parts[0].text.strip()

            # Clean up potential markdown code block fences if present
            if raw_json_str.startswith("```json"):
                raw_json_str = raw_json_str[len("```json"):]
            if raw_json_str.startswith("```"): # General markdown fence
                raw_json_str = raw_json_str[len("```"):]
            if raw_json_str.endswith("```"):
                raw_json_str = raw_json_str[:-len("```")]
            raw_json_str = raw_json_str.strip()

            print(f"Raw Gemini response content: {raw_json_str}")

            if not raw_json_str:
                print("Warning: Gemini returned an empty string.")
                return []

            # Attempt to parse the JSON string
            extracted_data = json.loads(raw_json_str)

            symptoms_list = []
            if isinstance(extracted_data, list):
                symptoms_list = extracted_data
            elif isinstance(extracted_data, dict):
                # Look for common keys that might contain the list
                possible_keys = ["symptoms", "extracted_symptoms", "symptom_list", "patient_symptoms"]
                for key in possible_keys:
                    if key in extracted_data and isinstance(extracted_data[key], list):
                        symptoms_list = extracted_data[key]
                        break
                if not symptoms_list: # Fallback if no key found but dict has a single list value
                    for value in extracted_data.values():
                        if isinstance(value, list): # Take the first list found
                            symptoms_list = value
                            break
            else:
                print(f"Warning: Gemini returned an unexpected format after JSON parsing: {type(extracted_data)}")
            
            # Validate and convert to string
            validated_symptoms = [str(s).lower().strip() for s in symptoms_list if isinstance(s, (str, int, float)) and str(s).strip()]
            # Remove duplicates while preserving order (if order matters, otherwise set is fine)
            seen = set()
            unique_symptoms = [x for x in validated_symptoms if not (x in seen or seen.add(x))]
            return unique_symptoms

        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from Gemini response: '{raw_json_str}'")
            if attempt < max_retries - 1:
                print(f"Retrying ({attempt+1}/{max_retries})...")
                time.sleep(2**attempt)
                continue
            return [] # Give up after retries
        except Exception as e:
            # Check for specific API errors like quota or rate limits if possible
            print(f"An error occurred during Gemini API call or processing: {e}")
            # Example of checking for rate limit (error message might vary)
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                print("Rate limit or quota error. Waiting before retry...")
                if attempt < max_retries -1:
                    time.sleep(5 * (attempt + 1)) # Longer wait for quota/rate limit
                    continue
            elif attempt < max_retries -1:
                time.sleep(2**attempt)
                continue
            return [] # Give up after retries
    return [] # Should not be reached if retries are handled, but as a fallback

# --- Example Usage & Integration Placeholder ---
if __name__ == "__main__":
    # Attempt to get API key from environment variable
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Fallback to hardcoded key IF you uncommented it above (NOT RECOMMENDED for production)
        # api_key = GOOGLE_API_KEY if 'GOOGLE_API_KEY' in globals() and GOOGLE_API_KEY else None
        print("WARNING: GOOGLE_API_KEY environment variable not found.")
        print("Please set it or paste your key directly into the script (less secure).")
        # For now, let's allow running without a key just to see the script structure.
        # You can manually set a test key here if needed for a quick run:
        # api_key = "YOUR_MANUAL_TEST_API_KEY" # << ONLY FOR LOCAL TESTING
        if not api_key:
             print("Exiting: API key is required to run Gemini calls.")
             exit()


    # Transcripts from your previous test
    sample_transcript_1 = "Patient: Good morning. I've been having a really bad headache and a sore throat for the past two days. I also feel very weak and I've had a slight fever. My child also has a running nose and she's been coughing a lot."
    sample_transcript_2 = "CHW: Any other issues? Patient: Yes, there's some pain in my stomach and I've noticed some yellowish eyes. The baby also has diarrhea."
    sample_transcript_3 = "The patient mentioned difficulty breathing and chest pain. No convulsions reported."
    sample_transcript_4 = "Mother says the child is not feeding well and seems very lethargic. She also noticed some skin rashes."
    sample_transcript_5 = "I feel fine, just here for a routine checkup for my immunizations."

    # **IMPORTANT**: Add your own Whisper transcripts here for better testing
    your_whisper_transcripts = [
        # "Paste your first Whisper transcript string here",
        # "Paste your second Whisper transcript string here",
    ]

    transcripts_to_test = [
        sample_transcript_1,
        sample_transcript_2,
        sample_transcript_3,
        sample_transcript_4,
        sample_transcript_5
    ] + [t for t in your_whisper_transcripts if t] # Add non-empty user transcripts


    print("\n--- Testing Symptom Extraction with Gemini API ---")
    for i, transcript in enumerate(transcripts_to_test):
        if not transcript.strip():
            continue
        print(f"\n--- Processing Transcript {i+1} ---")
        print(f"Transcript: \"{transcript}\"")
        
        extracted_symptoms = extract_symptoms_with_gemini(transcript, api_key)
        print(f"Gemini-Extracted Symptoms: {extracted_symptoms}")
        print("-" * 30)
        time.sleep(1) 