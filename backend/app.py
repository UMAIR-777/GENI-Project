# File: main.py
from fastapi import FastAPI, Request
from fastapi.responses import Response
from pathlib import Path
import requests
import uuid
from backend.json_to_langgraph import graph_builder
from backend.runner import run_workflow
from db.repository import save_lead, save_workflow, load_workflow
from backend. workflow_functions import resume_listen  # Whisper STT node
import json
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException
from pathlib import Path
config_path = Path(r"C:\ai_voice_bot\backend\graph_Ai.json")
with open(config_path, "r", encoding="utf-8") as f:
    app_json = json.load(f)

print(app_json["ai_voice_bot"]["nodes"])


app = FastAPI()

# Build the LangGraph workflow
graph, _, _ = graph_builder(app_json)

# ----------------------------
# 1️⃣ Lead Submission (from Streamlit)
# ----------------------------
@app.post("/lead")
async def create_lead(payload: dict):
    lead_id = save_lead({
        "id": uuid.uuid4(),
        "name": payload["name"],
        "phone": payload["phone"],
        "interest": payload["interest"]
    })
    return {"lead_id": lead_id}



BASE_DIR = Path(__file__).resolve().parent
AUDIO_FOLDER = BASE_DIR / "audio_files"
AUDIO_FOLDER.mkdir(exist_ok=True)

# Mount the audio folder so it is accessible at /audio/<filename>
app.mount("/audio", StaticFiles(directory=str(AUDIO_FOLDER)), name="audio")

BASE_URL = "https://uncategorised-jamal-proanarchy.ngrok-free.dev"


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = AUDIO_FOLDER / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    return FileResponse(path=file_path, media_type="audio/mpeg", filename=filename)
# ----------------------------
# 2️⃣ Start AI Voice Workflow
# ----------------------------
@app.post("/webhook/start-call")
async def start_call(payload: dict):
    """
    Triggered from Streamlit form.
    Prepares initial state and runs workflow.
    """
    state = {
        "lead_id": payload["lead_id"],
        "lead_name": payload["name"],
        "phone": payload["phone"],
        "interest": payload["interest"],
        "user_response": "",
        "score": 0,
        "qualified": False,
        "is_paused": False,
    }
    await run_workflow(graph, state)
    return {"status": "started"}


# ----------------------------
# 3️⃣ Twilio Voice Endpoint


from twilio.twiml.voice_response import VoiceResponse

@app.post("/twilio/voice")
@app.get("/twilio/voice")
async def twilio_voice(request: Request):
    response = VoiceResponse()

    # ALWAYS speak something immediately
    response.say(
        "Hello. Please wait while we connect you.",
        voice="alice",
        language="en-US"
    )

    # thora sa wait
    response.pause(length=1)

    # ab next step pe jao
    response.redirect(f"{BASE_URL}/twilio/speak", method="POST")

    return Response(str(response), media_type="application/xml")

 
@app.post("/twilio/speak")
@app.get("/twilio/speak")
async def twilio_speak(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid")

    print("📞 /twilio/speak HIT")
    print("➡️ CallSid from Twilio:", call_sid)

    response = VoiceResponse()

    if not call_sid:
        print("❌ CallSid missing")
        response.say("Error. Call ID missing.")
        return Response(str(response), media_type="application/xml")

    wf = load_workflow(call_sid)

    if not wf:
        print("❌ Workflow not found for CallSid:", call_sid)
        response.say("Workflow not found.")
        return Response(str(response), media_type="application/xml")

    state = wf.state
    audio_url = state.get("audio_url")

    print("🧠 Loaded workflow state:", state)
    print("🎵 Audio URL:", audio_url)

    if audio_url:
        print("▶️ Sending Play command to Twilio")
        response.play(audio_url)
        response.redirect("/twilio/listen", method="POST")
    else:
        print("⏳ Audio URL missing, retrying")
        response.say("Please wait.")
        response.pause(length=1)
        response.redirect("/twilio/speak", method="POST")

    return Response(str(response), media_type="application/xml")


@app.post("/twilio/listen")
@app.get("/twilio/listen")
async def twilio_listen():
    response = VoiceResponse()

    response.gather(
        input="speech",
        action="/twilio/recording",
        timeout=8,
        speech_timeout="auto"
    )

    return Response(str(response), media_type="application/xml")



# ----------------------------
# 4️⃣ Twilio Recording Webhook
# ----------------------------
@app.post("/twilio/recording")
async def twilio_recording(request: Request):
    """
    Twilio POSTs here after user speaks.
    Downloads audio, performs STT, resumes workflow.
    """
    form = await request.form()
    call_id = form.get("CallSid")
    recording_url = form.get("RecordingUrl") 
    

    # Download audio locally
    audio_path = Path(f"./audio_files/{call_id}.wav")
    audio_path.parent.mkdir(exist_ok=True)
    audio_bytes = requests.get(recording_url).content
    audio_path.write_bytes(audio_bytes)

    # Load workflow state from DB
    wf = load_workflow(call_id)
    state = wf.state

    # STT via Whisper
    state_update = await resume_listen(state, str(audio_path))
    state.update(state_update)

    # Resume LangGraph workflow
    await run_workflow(graph, state)

    return {"ok": True}

# ----------------------------
# 5️⃣ Optional: Manual Resume (if needed)
# ----------------------------
@app.post("/webhook/user-speech")
async def user_speech(payload: dict):
    """
    Alternative resume endpoint if you have audio from another source.
    """
    wf = load_workflow(payload["call_id"])
    state = wf.state
    state["user_response"] = payload["transcript"]
    state["is_paused"] = False
    await run_workflow(graph, state)
    return {"status": "resumed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
