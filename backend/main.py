import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

load_dotenv()

app = FastAPI()

# Dev CORS: lets your VS Code Live Server hit the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini client (picks up GEMINI_API_KEY from env)
client = genai.Client()

MODEL_CHAT = "gemini-2.5-flash"   # stable + fast :contentReference[oaicite:6]{index=6}
MODEL_EXTRACT = "gemini-2.5-flash"

class Msg(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class ChatPayload(BaseModel):
    messages: list[Msg]
    state: dict | None = None

def flatten(messages: list[Msg]) -> str:
    """Simple text transcript. Good enough for v1."""
    out = []
    for m in messages:
        out.append(f"{m.role.upper()}: {m.content}")
    return "\n".join(out)

def parse_json_loose(text: str) -> dict:
    """Handles plain JSON or JSON fenced in ```json ... ```."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        # if it begins with 'json\n{...'
        t = t.split("\n", 1)[-1].strip()
    try:
        return json.loads(t)
    except Exception:
        return {"ship_from_city": None, "ship_to_city": None, "ship_time": None}

@app.post("/chat")
def chat(payload: ChatPayload):
    transcript = flatten(payload.messages)

    # 1) Natural chatbot reply
    reply_resp = client.models.generate_content(
        model=MODEL_CHAT,
        contents=(
            "You are a shipping assistant. Be concise and ask for missing details.\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            "Respond to the user."
        ),
    )
    reply_text = (reply_resp.text or "").strip()

    # 2) Structured extraction (JSON)
    # Gemini supports structured outputs; for now we keep it simple: force JSON-only. :contentReference[oaicite:7]{index=7}
    extract_resp = client.models.generate_content(
        model=MODEL_EXTRACT,
        contents=(
            "Return ONLY valid JSON. No markdown. No extra text.\n"
            "Extract these fields from the conversation:\n"
            "- ship_from_city (string or null)\n"
            "- ship_to_city (string or null)\n"
            "- ship_time (string or null)  # store raw if unclear (e.g. 'Wednesday 14th March')\n\n"
            f"Conversation:\n{transcript}\n"
        ),
    )
    extracted = parse_json_loose(extract_resp.text or "")

    return {"reply": reply_text, "state": extracted}
