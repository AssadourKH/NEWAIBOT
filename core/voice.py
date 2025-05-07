# import os
# import requests
# import io
# import subprocess
# import gc
# from pathlib import Path
# from dotenv import load_dotenv, find_dotenv
# from azure.cognitiveservices.speech import (
#     SpeechConfig,
#     AudioConfig,
#     SpeechRecognizer,
#     ResultReason,
#     CancellationReason
# )

# # Load .env
# load_dotenv(find_dotenv())
# FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
# SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
# SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
# TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")

# def whatsapp_reply(incoming_msg, media_url, media_type):
#     """
#     Downloads audio from Twilio, converts to WAV, transcribes using Azure Speech.
#     Uses ar-LB by default unless user mentions en-US/en-UK.
#     """
#     temp_filename = "temp_audio.wav"

#     # Detect language from text (fallback approach)
#     language = "ar-LB"
#     if "en-us" in incoming_msg.lower():
#         language = "en-US"
#     elif "en-uk" in incoming_msg.lower():
#         language = "en-GB"

#     if media_url and "audio" in (media_type or ""):
#         try:
#             print(f"[DEBUG] Downloading audio from: {media_url}")
#             response = requests.get(media_url, auth=(TWILIO_SID, TWILIO_AUTH))
#             response.raise_for_status()
#             local_audio = io.BytesIO(response.content)

#             print("[DEBUG] Converting to WAV using ffmpeg...")
#             ffmpeg_cmd = [
#                 FFMPEG_PATH,
#                 "-i", "pipe:0",
#                 "-acodec", "pcm_s16le",
#                 "-ar", "16000",
#                 "-ac", "1",
#                 "-f", "wav",
#                 "pipe:1"
#             ]
#             ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#             out, err = ffmpeg.communicate(local_audio.read())

#             if ffmpeg.returncode != 0:
#                 print("[FFMPEG ERROR]", err.decode())
#                 raise RuntimeError("FFmpeg failed to convert audio.")

#             with open(temp_filename, "wb") as f:
#                 f.write(out)

#             speech_config = SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
#             speech_config.speech_recognition_language = language
#             audio_input = AudioConfig(filename=temp_filename)
#             recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

#             print("[DEBUG] Starting recognition...")
#             result = recognizer.recognize_once()

#             if result.reason == ResultReason.RecognizedSpeech:
#                 print(f"[DEBUG] ✅ Recognized: {result.text}")
#                 return result.text
#             elif result.reason == ResultReason.NoMatch:
#                 print("[DEBUG] ❌ No match found.")
#                 return "Sorry, I couldn’t understand the audio."
#             elif result.reason == ResultReason.Canceled:
#                 cancellation = result.cancellation_details
#                 reason = cancellation.reason if cancellation else "unknown"
#                 print("[DEBUG] 🚫 Canceled:", reason)
#                 return f"Speech recognition was canceled: {reason}"

#         except Exception as e:
#             print(f"[ERROR] Voice processing failed: {e}")
#             return "Something went wrong with the audio message."

#         finally:
#             try:
#                 if os.path.exists(temp_filename):
#                     os.remove(temp_filename)
#                 del recognizer
#                 gc.collect()
#             except:
#                 pass

#     return "Please send an audio message."

# core/voice.py
# core/voice.py

import os
import io
import subprocess
import gc
from dotenv import load_dotenv
from azure.cognitiveservices.speech import (
    SpeechConfig,
    AudioConfig,
    SpeechRecognizer,
    ResultReason
)

load_dotenv()

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

def transcribe_audio_bytes(audio_data):
    """
    Takes raw audio bytes (from WhatsApp), converts to WAV using ffmpeg, sends to Azure Speech-to-Text.
    Returns the recognized text.
    """
    temp_filename = "temp_audio.wav"

    try:
        # Convert OGG to WAV
        ffmpeg_cmd = [
            FFMPEG_PATH,
            "-i", "pipe:0",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            "pipe:1"
        ]
        ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = ffmpeg.communicate(audio_data)

        if ffmpeg.returncode != 0:
            print("[FFMPEG ERROR]", err.decode())
            raise RuntimeError("Failed to convert audio with ffmpeg.")

        # Save output to temp file
        with open(temp_filename, "wb") as f:
            f.write(out)

        speech_config = SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        speech_config.speech_recognition_language = "ar-LB"
        audio_input = AudioConfig(filename=temp_filename)
        recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

        print("[DEBUG] Starting Azure recognition...")
        result = recognizer.recognize_once()

        if result.reason == ResultReason.RecognizedSpeech:
            print(f"[DEBUG] ✅ Recognized: {result.text}")
            return result.text.strip()
        else:
            print("[DEBUG] ❌ Azure did not recognize speech.")
            return None

    except Exception as e:
        print(f"[ERROR] Voice transcription failed: {e}")
        return None

    finally:
        try:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            del recognizer
            gc.collect()
        except Exception:
            pass
