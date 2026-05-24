import sys
import os
import time
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Installing google genai if missing
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Installing google-genai...")
    os.system(f"{sys.executable} -m pip install -q google-genai")
    from google import genai
    from google.genai import types

# Fix Windows terminal UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.system("chcp 65001 > nul")

# ─────────────────────────────────────────────────────────────────
# LOGGING & APP SETUP
# ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.FileHandler("api_process.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)

app = FastAPI(
    title="SLT Mobitel ASR Cleaner API",
    description="Headless microservice for cleaning noisy Sinhala ASR transcripts.",
    version="1.1.0"
)

# ─────────────────────────────────────────────────────────────────
# SETTINGS & PROMPT
# ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIza....................." # REPLACE with your actual API key 
SELECT_MODEL = "gemini-3-flash-preview"

CLEAN_PROMPT = """You are a Sinhala language expert processing ASR transcripts from telecommunication call centers. 

Your objective is to reconstruct a clean, coherent Sinhala conversation while strictly filtering out ASR hallucinations. 

Rules for Cleaning:
1. Merge split words and fix corrupted Unicode characters.
2. Contextual Pruning: DELETE hallucinated words that clearly do not match the telecommunications/billing context. 
3. Noise Removal: DELETE isolated 1-2 letter fragments ONLY IF they lack semantic or grammatical meaning in the sentence. DO NOT delete valid functional words (e.g., 'නෑ', 'පේ', 'ට', 'ගේ').
4. Keep numbers, English terms (bill, payment, connection, online, account, reference), and caller details exactly as they appear.
5. Output ONE continuous plain paragraph in correct Sinhala script. No formatting.

NOISY ASR TEXT:
{text}"""

# ─────────────────────────────────────────────────────────────────
# DATA MODELS (JSON Structure)
# ─────────────────────────────────────────────────────────────────
class TranscriptRequest(BaseModel):
    raw_text: str

class TranscriptResponse(BaseModel):
    cleaned_text: str
    processing_time_seconds: float
    model_used: str

# ─────────────────────────────────────────────────────────────────
# CORE CLEANING FUNCTION
# ─────────────────────────────────────────────────────────────────
def clean_text(noisy_text: str, model: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    last_error = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=CLEAN_PROMPT.format(text=noisy_text),
                config=types.GenerateContentConfig(
                    temperature=0.0, # Enforces strict determinism to prevent hallucinations
                )
            )
            return response.text.strip()
        except Exception as e:
            last_error = e
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait = (attempt + 1) * 5
                logging.warning(f"503 error — retrying in {wait}s...")
                time.sleep(wait)
            else:
                break 

    raise RuntimeError(f"Gemini API failure: {last_error}")

# ─────────────────────────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"message": "SLT Mobitel ASR Text Cleaner API is running. Visit /docs for the manual testing interface."}

@app.post("/clean-transcript/", response_model=TranscriptResponse)
def clean_transcript_endpoint(request: TranscriptRequest):
    logging.info(f"Received API request. Text length: {len(request.raw_text)} chars.")
    
    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
        
    t0 = time.time()
    
    try:
        # Pass the exact requested text into the cleaning function
        cleaned = clean_text(request.raw_text, SELECT_MODEL, GEMINI_API_KEY)
        elapsed = round(time.time() - t0, 2)
        
        logging.info(f"Successfully processed request in {elapsed}s.")
        
        # Return the structured JSON response
        return TranscriptResponse(
            cleaned_text=cleaned,
            processing_time_seconds=elapsed,
            model_used=SELECT_MODEL
        )
        
    except Exception as e:
        logging.error(f"API Processing Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Allows you to run the script directly via `python api.py`
    uvicorn.run(app, host="0.0.0.0", port=8000)