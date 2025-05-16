import os
from openai import OpenAI

try:
    client = OpenAI()
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    print("Please ensure your OPENAI_API_KEY environment variable is set correctly.")
    exit()

AUDIO_FILE_PATH = "test_audio.wav" 

# --- Main Transcription Function ---
def transcribe_audio_with_whisper(file_path):
    """
    Transcribes an audio file using OpenAI's Whisper API.

    Args:
        file_path (str): The path to the audio file.

    Returns:
        str: The transcribed text, or None if an error occurred.
    """
    try:
        with open(file_path, "rb") as audio_file:
            print(f"Transcribing {file_path}...")
            # Using the 'whisper-1' model
            # You can add more parameters here if needed, e.g., language
            # For CHW-patient conversations in Nigeria, you might experiment with:
            # response = client.audio.transcriptions.create(
            #     model="whisper-1",
            #     file=audio_file,
            #     language="en" #  Specify English, or let Whisper auto-detect
            #     # prompt="This is a conversation between a health worker and a patient about symptoms." # Can help guide the model
            # )
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            transcript = response.text
            return transcript
    except FileNotFoundError:
        print(f"Error: Audio file not found at {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred during transcription: {e}")
        return None

# --- Script Execution ---
if __name__ == "__main__":
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"Error: The audio file specified ({AUDIO_FILE_PATH}) does not exist.")
        print("Please check the AUDIO_FILE_PATH variable in the script and ensure the file is there.")
    else:
        transcription = transcribe_audio_with_whisper(AUDIO_FILE_PATH)

        if transcription:
            print("\n--- Transcription ---")
            print(transcription)

            # Optional: Save to a file
            # output_filename = os.path.splitext(AUDIO_FILE_PATH)[0] + "_transcript.txt"
            # with open(output_filename, "w") as f:
            #     f.write(transcription)
            # print(f"\nTranscript saved to {output_filename}")