import os
import torch
from transformers import pipeline

AUDIO_FILE_PATH = "test_audio.wav"


# "openai/whisper-tiny.en"  (English-only, very small and fast)
# "openai/whisper-tiny"     (Multilingual, very small and fast)
# "openai/whisper-base.en"  (English-only, small)
# "openai/whisper-base"     (Multilingual, small - GOOD STARTING POINT)
# "openai/whisper-small.en" (English-only)
# "openai/whisper-small"    (Multilingual)
# "openai/whisper-medium.en"(English-only)
# "openai/whisper-medium"   (Multilingual)
# "openai/whisper-large-v3" (Multilingual, latest, most accurate, slowest, needs more RAM/VRAM)
MODEL_NAME = "openai/whisper-base" # Good starting point for quality/speed balance

# Using GPU significantly speeds up transcription
if torch.backends.mps.is_available():
    DEVICE = "mps"
    print("MPS is available! PyTorch can use your Apple Silicon GPU.")
elif torch.cuda.is_available(): # Fallback for other systems if CUDA is present
    DEVICE = "cuda:0"
    print("CUDA is available! PyTorch can use your NVIDIA GPU.")
else:
    DEVICE = "cpu"
    print("MPS and CUDA NOT available. PyTorch will use CPU.")
    
print(f"Using device: {DEVICE}")

if DEVICE == "cpu" and ("large" in MODEL_NAME or "medium" in MODEL_NAME):
    print(f"WARNING: Running a '{MODEL_NAME}' model on CPU will be very slow. "
          "Consider using a smaller model (e.g., 'openai/whisper-base' or 'openai/whisper-tiny') "
          "or ensure you have a CUDA-enabled GPU set up correctly with PyTorch.")

# --- Main Transcription Function ---
def transcribe_audio_local_whisper(file_path, model_name, device_to_use):
    """
    Transcribes an audio file using a local Whisper model via Hugging Face Transformers.

    Args:
        file_path (str): The path to the audio file.
        model_name (str): The name of the Whisper model to use from Hugging Face Hub.
        device_to_use (str): The device to run the model on ("cuda:0" or "cpu").

    Returns:
        str: The transcribed text, or None if an error occurred.
    """
    try:
        print(f"Loading model '{model_name}'... This might take a while on the first run as it downloads the model.")
        # Initialize the ASR pipeline
        asr_pipeline = pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=device_to_use,
            torch_dtype=torch.float16 if device_to_use == "cuda:0" and torch.cuda.is_available() else torch.float32,
        
            chunk_length_s=30, 
        )
        print(f"Model '{model_name}' loaded. Transcribing {file_path}...")

        transcription_output = asr_pipeline(
            file_path,
            generate_kwargs={"task": "transcribe"}, # Ensure it's in transcribe mode
            return_timestamps=True
        )

        
        print("Using return_timestamps=True for potentially long audio...")
        transcription_output = asr_pipeline(file_path, return_timestamps=True)
        
        transcript = transcription_output["text"]

        return transcript

    except FileNotFoundError:
        print(f"Error: Audio file not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        if "out of memory" in str(e).lower():
            print("This might be an out-of-memory error. Try a smaller model, "
                    "or if using GPU, ensure you have enough VRAM. "
                    "If on CPU, ensure you have enough RAM.")
        return None

# --- Script Execution ---
if __name__ == "__main__":
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"Error: The audio file specified ('{AUDIO_FILE_PATH}') does not exist.")
        print("Please check the AUDIO_FILE_PATH variable in the script and ensure the file is there.")
    else:
        transcription = transcribe_audio_local_whisper(AUDIO_FILE_PATH, MODEL_NAME, DEVICE)

        if transcription:
            print("\n--- Transcription ---")
            print(transcription)

           