# Sinhala ASR Text Cleaner API

FastAPI + Uvicorn REST API that cleans noisy/corrupted Sinhala ASR text
from SLT call center recordings using Gemini 2.5 Flash-Lite.

---

## Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Gemini API key
export GEMINI_API_KEY=your_key_here      # Linux/Mac
set GEMINI_API_KEY=your_key_here         # Windows

# 3. Start the server
uvicorn main:app --reload --port 8000
```

Server runs at: http://localhost:8000
API docs at:    http://localhost:8000/docs

---

## Deploy to Render (Free)

1. Push this folder to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Set environment variable: GEMINI_API_KEY = your_key
5. Click Deploy — done!

---

## API Endpoints

### POST /clean
Clean a single noisy text.

**Request:**
```json
{
  "text": "ආයිබෝවන් මම රේනුක ට පුළුවනිෝබට..."
}
```

**Response:**
```json
{
  "original": "ආයිබෝවන් මම රේනුක ට...",
  "cleaned": "ආයුබෝවන්, මම රේණුකා...",
  "time_seconds": 2.4
}
```

### POST /clean/batch
Clean up to 50 texts at once.

**Request:**
```json
{
  "texts": [
    "first noisy text...",
    "second noisy text..."
  ]
}
```

**Response:**
```json
{
  "results": [
    {"index": 0, "original": "...", "cleaned": "...", "error": null},
    {"index": 1, "original": "...", "cleaned": "...", "error": null}
  ],
  "total_time_seconds": 4.8
}
```

### GET /health
```json
{"status": "ok", "model": "gemini-2.5-flash-lite"}
```

---

## Test with curl

```bash
# Single text
curl -X POST http://localhost:8000/clean \
  -H "Content-Type: application/json" \
  -d '{"text": "ආයිබෝවන් මම රේනුක ට පුළුවනිෝබට සහයවන්න"}'

# Batch
curl -X POST http://localhost:8000/clean/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["first noisy text", "second noisy text"]}'

# Health check
curl http://localhost:8000/health
```
