from db.repository import  save_workflow

"""
AI VOICE BOT – READY NODES
Dependencies included and audio path configurable
"""

# ----------------------------
# 1️⃣ START CALL NODE
# ----------------------------
# Twilio call start
# Requires: pip install twilio
# Config: TWILIO_SID, TWILIO_AUTH, FROM_NUMBER
from twilio.rest import Client

from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Twilio
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
FROM_NUMBER = os.getenv("FROM_NUMBER")

# Base URL
BASE_URL = os.getenv("BASE_URL")

# OpenAI
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

# Twilio client
from twilio.rest import Client as TwilioClient
twilio_client = TwilioClient(TWILIO_SID, TWILIO_AUTH)

async def start_call(state: dict) -> dict:
    print("📞 Twilio Voice URL:", f"{BASE_URL}/twilio/voice")

    call = twilio_client.calls.create(
        to=state["phone"],
        from_=FROM_NUMBER,
        url=f"{BASE_URL}/twilio/voice",
        method="POST"  # 🔥 THIS WAS MISSING
    )

    call_sid = call.sid
    state["call_sid"] = call_sid

    # Map temp TTS file → real call SID
    temp_id = state.get("tts_temp_id")
    if temp_id:
        old_audio_path = AUDIO_FOLDER / f"tts_{temp_id}.mp3"
        new_audio_path = AUDIO_FOLDER / f"tts_{call_sid}.mp3"

        if old_audio_path.exists():
            old_audio_path.rename(new_audio_path)
            state["audio_file"] = str(new_audio_path)
            state["audio_url"] = f"{BASE_URL}/audio/tts_{call_sid}.mp3"

    save_workflow(
        call_sid=call_sid,
        lead_id=state.get("lead_id"),
        state=state
    )

    return {**state, "call_sid": call_sid, "current_node": "start_call"}

    # Print the result for debugging





# ----------------------------
# 2️⃣ SPEAK NODE (ASYNC TTS)
# --# ---------------------------

# 2️⃣ SPEAK NODE (ASYNC TTS) - Updated for ElevenLabs v2
from elevenlabs.client import ElevenLabs
from pathlib import Path
import uuid

# Use one AUDIO_FOLDER for both writing and serving
BASE_DIR = Path(__file__).resolve().parent
AUDIO_FOLDER = BASE_DIR / "audio_files"
AUDIO_FOLDER.mkdir(exist_ok=True)

# Your ElevenLabs client
# # ----------------------------
# ElevenLabs TTS CLIENT
# ----------------------------
# from elevenlabs.client import ElevenLabs

# Load ElevenLabs API key from env
# ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize ElevenLabs client
# client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
  # consider env variable


# async def speak(state: dict) -> dict:
#     # Use temp ID if call_sid is missing
#     temp_id = state.get("call_sid") or str(uuid.uuid4())
#     audio_path = AUDIO_FOLDER / f"tts_{temp_id}.mp3"

#     if not audio_path.exists():
#         text = (
#             f"Hello {state.get('lead_name','')}. "
#             "This is a real estate follow-up call. "
#             "Are you interested in buying, selling, or renting a property? "
#             "Say yes to continue, or no to stop."
#         )

#         audio_bytes = client.text_to_speech.convert(
#             text=text,
#             voice_id="CwhRBWXzGAHq8TQ4Fs17",
#             model_id="eleven_multilingual_v2",
#             output_format="mp3_44100_128"
#         )

#         # Convert generator to bytes if needed
#         if not isinstance(audio_bytes, bytes):
#             audio_bytes = b"".join(audio_bytes)

#         # Write MP3 file
#         audio_path.write_bytes(audio_bytes)

#     # Save state
#     state["tts_temp_id"] = temp_id
#     state["audio_file"] = str(audio_path)
#     state["audio_url"] = f"{BASE_URL}/audio/{audio_path.name}"  # THIS is what Twilio will play
#     state["current_node"] = "speak"

#     return state

from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent
AUDIO_FOLDER = BASE_DIR / "audio_files"

BASE_URL = os.getenv("BASE_URL")
TEMPLATE_AUDIO = AUDIO_FOLDER / "tts_CAf8a96ad95da2f1c3dc100d8c5aee4af0.mp3"

async def speak(state: dict) -> dict:
    call_sid = state.get("call_sid")

    if not call_sid:
        raise ValueError("call_sid missing in state")

    # 🎯 Unique audio per call
    audio_filename = f"tts_{call_sid}.mp3"
    audio_path = AUDIO_FOLDER / audio_filename

    # 🔁 Copy static template → call-specific file
    if not audio_path.exists():
        if not TEMPLATE_AUDIO.exists():
            raise FileNotFoundError("tts_template.mp3 not found") 

        shutil.copy(TEMPLATE_AUDIO, audio_path)

    # Update state (DB alignment perfect)
    state["audio_file"] = str(audio_path)
    state["audio_url"] = f"{BASE_URL}/audio/{audio_filename}"
    state["current_node"] = "speak"

    return state





# ----------------------------
# 3️⃣ LISTEN NODE (PAUSE NODE)
# ----------------------------
# LangGraph interrupt node
async def listen(state: dict) -> dict:
    return {**state,
        "is_paused": True,
        "waiting_for": "user_speech",
        "current_node": "listen",
    }

# ----------------------------
# 4️⃣ RESUME LISTEN (WEBHOOK + STT)
# ----------------------------
# Whisper offline STT
# Requires: pip install openai-whisper
# ----------------------------
# RESUME LISTEN NODE (OpenAI STT)
# ----------------------------
import openai

async def resume_listen(state: dict, audio_path: str) -> dict:
    """
    Resume workflow after user speaks
    state: current workflow state dict
    audio_path: path to user audio (wav/mp3)
    """
    with open(audio_path, "rb") as audio_file:
        transcript_response = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    transcript = transcript_response.text

    return {**state,
        "user_response": transcript,
        "is_paused": False,
        "waiting_for": None,
    }



# ----------------------------
# 5️⃣ DETECT INTENT NODE
# ----------------------------
# HuggingFace offline sentiment classifier
# Requires: pip install transformers
from transformers import pipeline
import asyncio

classifier = pipeline("sentiment-analysis")

async def detect_intent(state: dict) -> dict:
    text = state.get("user_response", "")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: classifier(text))
    label = result[0]["label"].lower()
    intent = "interested" if "positive" in label else "not_interested"
    return {
        "intent": intent,
        "current_node": "detect_intent",
    }


# ----------------------------
# 6️⃣ QUALIFY NODE
# ----------------------------
# Simple synchronous scoring
def qualify(state: dict) -> dict:
    text = state.get("user_response", "").lower()
    score = 0
    if "price" in text or "budget" in text:
        score += 30
    if "yes" in text or "interested" in text:
        score += 40
    if "soon" in text or "urgent" in text:
        score += 30
    return {**state,
        "score": score,
        "qualified": score >= 70,
        "current_node": "qualify",
    }


# ----------------------------
# 7️⃣ DECIDE NEXT NODE (CONDITIONAL)
# ----------------------------
def decide_next(state: dict) -> str:
    if state.get("qualified"):
        state["bot_text"] = "Your call is being processed. Our sales team will contact you."
        return "speak"
    state["bot_text"] = "Thank you for your time."
    return "end_call"


# ----------------------------
# 8️⃣ END CALL NODE
# ----------------------------
def end_call(state: dict) -> dict:
    return {**state,
        "call_status": "completed",
        "current_node": "end_call",
    }
