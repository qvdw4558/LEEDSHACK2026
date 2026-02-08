import json
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google import genai
from cleaner import clean_shipment

from analysis_pipeline import run_analysis


# Load environment variables (expects GEMINI_API_KEY in .env)
load_dotenv()

app = FastAPI()

# Dev-only CORS (lets Live Server / local frontend call the API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini client uses GEMINI_API_KEY from env
client = genai.Client()

# Cheap + fast model
MODEL = "gemini-2.5-flash"


class Msg(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatPayload(BaseModel):
    messages: list[Msg]


def flatten(messages: list[Msg]) -> str:
    """Flatten role/content messages into a simple transcript string."""
    return "\n".join(f"{m.role.upper()}: {m.content}" for m in messages)


def parse_json_loose(text: str) -> dict:
    """
    Parses JSON even if wrapped in ```json fences.
    Returns {} if parsing fails.
    """
    t = (text or "").strip()

    if t.startswith("```"):
        # remove triple backticks
        t = t.strip("`")
        # drop optional "json" line
        if "\n" in t:
            t = t.split("\n", 1)[1].strip()

    try:
        return json.loads(t)
    except Exception:
        return {}


@app.post("/chat")
def chat(payload: ChatPayload):
    transcript = flatten(payload.messages)

    prompt = f"""
You are a shipping assistant.

You must do TWO things:
1) Write a short helpful reply to the user, asking ONLY for missing details among:
   - ship_from_city
   - ship_to_city
   - ship_date
2) Extract shipment details from the conversation.

Return ONLY valid JSON in EXACTLY this format (no markdown, no extra text):
{{
  "reply": "string",
  "shipment": {{
    "ship_from_city": "string or null",
    "ship_to_city": "string or null",
    "ship_date": "YYYY-MM-DD or null"
  }}
}}

Rules:
- If unknown, use null.
- If the user gave a date like 'Saturday 7th Feb 2026', convert it to YYYY-MM-DD if you can.
- Do not ask for package weight/dimensions; only focus on from/to/date.

Conversation:
{transcript}
""".strip()

    try:
        resp = client.models.generate_content(model=MODEL, contents=prompt)
    except Exception as e:
        # If Gemini call fails, don't crash the app
        print("Gemini error:", repr(e))
        return {
            "reply": "Temporary connection issue to the AI service. Please send that again.",
            "shipment": {"ship_from_city": None, "ship_to_city": None, "ship_date": None},
            "error": str(e),
        }

    data = parse_json_loose(resp.text or "")

    reply = (data.get("reply") or "").strip()

    shipment_raw = data.get("shipment") if isinstance(data.get("shipment"), dict) else {}
    shipment_clean = clean_shipment(shipment_raw)

    analysis = None
    if shipment_clean["ship_from_city"] and shipment_clean["ship_to_city"] and shipment_clean["ship_date"]:
        try:
            analysis = run_analysis(
                shipment_clean["ship_from_city"],
                shipment_clean["ship_to_city"],
                shipment_clean["ship_date"],
            )

            # Simple: append analysis into the reply (no extra Gemini call)
            reply = (
                reply
                + f"\n\nRoute risk: {analysis['risk_score']}/100 ({analysis['risk_level']})."
            )

        except Exception as e:
            # Don't crash the chatbot if analysis fails
            analysis = {"error": str(e)}
            reply = reply + "\n\nI couldn’t run route analysis right now (service error)."


    # Persist JSON for other scripts
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "latest_shipment.json").write_text(
        json.dumps(shipment_clean, indent=2),
        encoding="utf-8",
    )

    return {"reply": reply, "shipment": shipment_clean, "analysis": analysis}

