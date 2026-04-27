from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai
import os, time

app = FastAPI(
    title="Sinhala ASR Text Cleaner API",
    description="Cleans noisy/corrupted Sinhala ASR output from call center recordings",
    version="1.0.0",
    docs_url=None,   # disable default swagger — we have our own UI
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = "AI..............." # replace with your actual Gemini API key
client = genai.Client(api_key=GEMINI_API_KEY)

CLEAN_PROMPT = """You are a Sinhala language expert specializing in cleaning corrupted speech recognition output from Sri Lankan call center recordings.

The text below is noisy/corrupted ASR output from a call center call. You do NOT know in advance what the call is about — it could be about bills, complaints, technical issues, deliveries, banking, insurance, government services, or anything else.

Your job is to reconstruct the original clean Sinhala conversation from the noisy input using your Sinhala language knowledge alone.

How to clean:
- Merge broken or split words back into correct Sinhala words
- Remove random noise characters that are not part of real words
- Fix corrupted Unicode characters and broken Sinhala script
- Fix spelling errors while preserving the original meaning
- Reconstruct words that are partially garbled based on phonetic similarity
- Keep numbers exactly as they appear
- Keep English/mixed words as-is (connection, bill, payment, online, account, reference, update, active, details, complaint, email, SMS, etc.)

Rules:
- Output ONE continuous plain paragraph in correct Sinhala script
- No speaker labels, no formatting, no line breaks
- Do NOT translate anything to English
- Do NOT add information that was not in the original text
- Do NOT summarize or shorten — preserve everything
- Do NOT explain what you did

NOISY ASR TEXT:
{text}"""


# ── Models ────────────────────────────────────────────────
class CleanRequest(BaseModel):
    text: str

class CleanResponse(BaseModel):
    original: str
    cleaned: str
    time_seconds: float

class BatchCleanRequest(BaseModel):
    texts: list[str]

class BatchCleanResponse(BaseModel):
    results: list[dict]
    total_time_seconds: float


# ── API Routes ────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "model": "gemini-2.5-flash-lite"}

@app.post("/clean", response_model=CleanResponse)
def clean_text(req: CleanRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text field cannot be empty")
    t0 = time.time()
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=CLEAN_PROMPT.format(text=req.text)
        )
        cleaned = response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")
    return CleanResponse(original=req.text, cleaned=cleaned, time_seconds=round(time.time()-t0,2))

@app.post("/clean/batch", response_model=BatchCleanResponse)
def clean_batch(req: BatchCleanRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")
    if len(req.texts) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 texts per batch request")
    t0 = time.time()
    results = []
    for i, text in enumerate(req.texts):
        if not text.strip():
            results.append({"index": i, "original": text, "cleaned": "", "error": "empty text"})
            continue
        import time
    last_error = None
    for attempt in range(3):   # retry up to 3 times
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=CLEAN_PROMPT.format(text=req.text)
            )
            cleaned = response.text.strip()
            last_error = None
            break
        except Exception as e:
            last_error = e
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                print(f"Attempt {attempt+1} failed, retrying in 5s...")
                time.sleep(5)
            else:
                break   # don't retry for other errors

    if last_error:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(last_error)}")
    return BatchCleanResponse(results=results, total_time_seconds=round(time.time()-t0,2))


# ── Beautiful UI ──────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def ui():
    return HTMLResponse(content=HTML_UI)

HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sinhala Text Cleaner — SLT</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Sinhala:wght@300;400;600&family=DM+Mono:wght@400;500&family=Fraunces:opsz,wght@9..144,300;9..144,600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #21262d;
    --border: #30363d;
    --accent: #f78166;
    --accent2: #79c0ff;
    --green: #56d364;
    --text: #e6edf3;
    --muted: #8b949e;
    --radius: 12px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
    padding: 0;
  }

  /* ── Header ── */
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 20px 40px;
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky; top: 0; z-index: 100;
  }
  .logo {
    width: 38px; height: 38px;
    background: var(--accent);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  header h1 {
    font-family: 'Fraunces', serif;
    font-size: 20px; font-weight: 600;
    color: var(--text);
    letter-spacing: -0.3px;
  }
  header span {
    font-size: 12px; color: var(--muted);
    margin-left: auto;
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 4px 10px;
    border-radius: 20px;
  }
  .status-dot {
    width: 8px; height: 8px;
    background: var(--green);
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%,100% { opacity: 1; } 50% { opacity: 0.4; }
  }

  /* ── Main layout ── */
  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 40px 24px;
  }

  /* ── Tabs ── */
  .tabs {
    display: flex; gap: 4px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 4px;
    margin-bottom: 28px;
    width: fit-content;
  }
  .tab {
    padding: 9px 22px;
    border-radius: 9px;
    cursor: pointer;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    color: var(--muted);
    border: none; background: none;
    transition: all 0.18s;
  }
  .tab.active {
    background: var(--surface2);
    color: var(--text);
    border: 1px solid var(--border);
  }
  .tab:hover:not(.active) { color: var(--text); }

  /* ── Panel ── */
  .panel { display: none; }
  .panel.active { display: block; }

  /* ── Card ── */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 20px;
  }
  .card-title {
    font-family: 'Fraunces', serif;
    font-size: 15px; font-weight: 600;
    color: var(--accent2);
    margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
  }

  /* ── Textarea ── */
  textarea {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 9px;
    color: var(--text);
    font-family: 'Noto Sans Sinhala', 'DM Mono', monospace;
    font-size: 15px;
    line-height: 1.8;
    padding: 16px;
    resize: vertical;
    min-height: 140px;
    transition: border-color 0.2s;
    outline: none;
  }
  textarea:focus { border-color: var(--accent2); }
  textarea::placeholder { color: var(--muted); font-family: 'DM Mono', monospace; font-size: 13px; }

  /* ── Button ── */
  .btn {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 11px 24px;
    border-radius: 9px;
    border: none; cursor: pointer;
    font-family: 'DM Mono', monospace;
    font-size: 13px; font-weight: 500;
    transition: all 0.18s;
    margin-top: 14px;
  }
  .btn-primary {
    background: var(--accent);
    color: #0d1117;
  }
  .btn-primary:hover { background: #ff9580; transform: translateY(-1px); }
  .btn-primary:active { transform: translateY(0); }
  .btn-primary:disabled {
    background: var(--surface2);
    color: var(--muted);
    cursor: not-allowed;
    transform: none;
  }

  /* ── Result box ── */
  .result-box {
    display: none;
    margin-top: 20px;
    animation: fadeIn 0.3s ease;
  }
  .result-box.show { display: block; }
  @keyframes fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }

  .result-label {
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }
  .result-text {
    background: var(--bg);
    border: 1px solid var(--green);
    border-radius: 9px;
    padding: 16px;
    font-family: 'Noto Sans Sinhala', monospace;
    font-size: 15px;
    line-height: 1.9;
    color: var(--text);
    white-space: pre-wrap;
    word-break: break-word;
  }
  .result-meta {
    display: flex; gap: 16px;
    margin-top: 10px;
    font-size: 12px; color: var(--muted);
  }
  .result-meta span { display: flex; align-items: center; gap: 5px; }

  /* ── Copy button ── */
  .copy-btn {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 5px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-family: 'DM Mono', monospace;
    margin-left: auto;
    transition: all 0.2s;
  }
  .copy-btn:hover { color: var(--text); border-color: var(--accent2); }

  /* ── Spinner ── */
  .spinner {
    width: 16px; height: 16px;
    border: 2px solid rgba(0,0,0,0.3);
    border-top-color: #0d1117;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: none;
  }
  .spinner.show { display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Error ── */
  .error-box {
    display: none;
    background: rgba(247,129,102,0.1);
    border: 1px solid var(--accent);
    border-radius: 9px;
    padding: 14px 16px;
    font-size: 13px;
    color: var(--accent);
    margin-top: 14px;
  }
  .error-box.show { display: block; }

  /* ── Batch specific ── */
  .batch-add {
    background: none;
    border: 1px dashed var(--border);
    border-radius: 9px;
    color: var(--muted);
    width: 100%;
    padding: 12px;
    cursor: pointer;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    margin-top: 10px;
    transition: all 0.2s;
  }
  .batch-add:hover { border-color: var(--accent2); color: var(--accent2); }

  .batch-item {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 14px;
    margin-bottom: 10px;
    position: relative;
  }
  .batch-item textarea { min-height: 90px; }
  .remove-btn {
    position: absolute; top: 10px; right: 10px;
    background: none; border: none;
    color: var(--muted); cursor: pointer;
    font-size: 16px; line-height: 1;
    padding: 2px 6px; border-radius: 4px;
    transition: all 0.2s;
  }
  .remove-btn:hover { color: var(--accent); }
  .batch-idx {
    font-size: 11px; color: var(--muted);
    margin-bottom: 8px;
    text-transform: uppercase; letter-spacing: 1px;
  }

  .batch-result-item {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 16px;
    margin-bottom: 12px;
  }
  .batch-result-item.success { border-color: var(--green); }
  .batch-result-item.failed { border-color: var(--accent); }

  /* ── API Docs section ── */
  .endpoint-card {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 16px;
  }
  .endpoint-header {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 20px;
    background: var(--surface);
    cursor: pointer;
    user-select: none;
  }
  .method-badge {
    font-size: 11px; font-weight: 600;
    padding: 3px 9px; border-radius: 5px;
    letter-spacing: 0.5px;
  }
  .method-post { background: rgba(121,192,255,0.15); color: var(--accent2); }
  .method-get  { background: rgba(86,211,100,0.15);  color: var(--green); }
  .endpoint-path {
    font-size: 14px; color: var(--text);
    font-family: 'DM Mono', monospace;
  }
  .endpoint-desc { font-size: 13px; color: var(--muted); margin-left: auto; }
  .endpoint-body {
    display: none;
    padding: 20px;
    background: var(--bg);
    border-top: 1px solid var(--border);
  }
  .endpoint-body.open { display: block; }
  pre {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.7;
    color: var(--text);
    white-space: pre;
  }
  .code-label {
    font-size: 11px; color: var(--muted);
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 8px; margin-top: 16px;
  }
  .code-label:first-child { margin-top: 0; }
</style>
</head>
<body>

<header>
  <div class="logo">🧹</div>
  <h1>Sinhala Text Cleaner</h1>
  <span><span class="status-dot"></span>API Online · gemini-2.5-flash-lite</span>
</header>

<main>
  <div class="tabs">
    <button class="tab active" onclick="switchTab('single')">Single Clean</button>
    <button class="tab" onclick="switchTab('batch')">Batch Clean</button>
    <button class="tab" onclick="switchTab('docs')">API Docs</button>
  </div>

  <!-- ── SINGLE ── -->
  <div class="panel active" id="panel-single">
    <div class="card">
      <div class="card-title">📝 Paste Noisy Sinhala Text</div>
      <textarea id="single-input" placeholder="Paste your noisy/corrupted Sinhala ASR text here...
Example: ආයිබෝවන් මම රේනුක ට පුළුවනිෝබට සහයවන්න ගේබලත්ම ශකකලබලල..." rows="7"></textarea>
      <button class="btn btn-primary" id="single-btn" onclick="runSingle()">
        <div class="spinner" id="single-spin"></div>
        <span id="single-btn-text">✨ Clean Text</span>
      </button>
    </div>

    <div class="error-box" id="single-error"></div>

    <div class="result-box" id="single-result">
      <div class="card">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">
          <div class="card-title" style="margin:0;">✅ Cleaned Output</div>
          <button class="copy-btn" onclick="copyText('single-output-text')">Copy</button>
        </div>
        <div class="result-text" id="single-output-text"></div>
        <div class="result-meta">
          <span>⏱ <span id="single-time"></span>s</span>
          <span>📊 <span id="single-chars"></span> chars</span>
        </div>
      </div>
    </div>
  </div>

  <!-- ── BATCH ── -->
  <div class="panel" id="panel-batch">
    <div class="card">
      <div class="card-title">📋 Batch Clean — Up to 50 texts at once</div>
      <div id="batch-inputs">
        <div class="batch-item" id="batch-0">
          <div class="batch-idx">Text #1</div>
          <textarea placeholder="Paste noisy Sinhala text here..." rows="4"></textarea>
        </div>
      </div>
      <button class="batch-add" onclick="addBatchItem()">+ Add another text</button>
      <button class="btn btn-primary" id="batch-btn" onclick="runBatch()">
        <div class="spinner" id="batch-spin"></div>
        <span id="batch-btn-text">✨ Clean All</span>
      </button>
    </div>

    <div class="error-box" id="batch-error"></div>
    <div id="batch-results"></div>
  </div>

  <!-- ── DOCS ── -->
  <div class="panel" id="panel-docs">
    <div class="card">
      <div class="card-title">📡 Base URL</div>
      <pre id="base-url">http://localhost:8000</pre>
      <p style="font-size:13px; color:var(--muted); margin-top:10px;">All endpoints below are relative to this URL.</p>
    </div>

    <!-- /clean -->
    <div class="endpoint-card">
      <div class="endpoint-header" onclick="toggleEndpoint(this)">
        <span class="method-badge method-post">POST</span>
        <span class="endpoint-path">/clean</span>
        <span class="endpoint-desc">Clean a single noisy text</span>
      </div>
      <div class="endpoint-body">
        <div class="code-label">Request Body (JSON)</div>
        <pre>{
  "text": "ආයිබෝවන් මම රේනුක ට..."
}</pre>
        <div class="code-label">Response (JSON)</div>
        <pre>{
  "original": "ආයිබෝවන් මම රේනුක ට...",
  "cleaned":  "ආයුබෝවන්, මම රේණුකා...",
  "time_seconds": 2.4
}</pre>
        <div class="code-label">curl example</div>
        <pre>curl -X POST http://localhost:8000/clean \
  -H "Content-Type: application/json" \
  -d '{"text": "ආයිබෝවන් මම රේනුක ට..."}'</pre>
        <div class="code-label">Python example</div>
        <pre>import requests
res = requests.post("http://localhost:8000/clean",
    json={"text": "ආයිබෝවන් මම රේනුක ට..."})
print(res.json()["cleaned"])</pre>
      </div>
    </div>

    <!-- /clean/batch -->
    <div class="endpoint-card">
      <div class="endpoint-header" onclick="toggleEndpoint(this)">
        <span class="method-badge method-post">POST</span>
        <span class="endpoint-path">/clean/batch</span>
        <span class="endpoint-desc">Clean up to 50 texts at once</span>
      </div>
      <div class="endpoint-body">
        <div class="code-label">Request Body (JSON)</div>
        <pre>{
  "texts": [
    "first noisy text...",
    "second noisy text..."
  ]
}</pre>
        <div class="code-label">Response (JSON)</div>
        <pre>{
  "results": [
    {"index": 0, "original": "...", "cleaned": "...", "error": null},
    {"index": 1, "original": "...", "cleaned": "...", "error": null}
  ],
  "total_time_seconds": 4.8
}</pre>
        <div class="code-label">Python example</div>
        <pre>import requests
res = requests.post("http://localhost:8000/clean/batch",
    json={"texts": ["text1...", "text2..."]})
for r in res.json()["results"]:
    print(r["cleaned"])</pre>
      </div>
    </div>

    <!-- /health -->
    <div class="endpoint-card">
      <div class="endpoint-header" onclick="toggleEndpoint(this)">
        <span class="method-badge method-get">GET</span>
        <span class="endpoint-path">/health</span>
        <span class="endpoint-desc">Check if server is running</span>
      </div>
      <div class="endpoint-body">
        <div class="code-label">Response</div>
        <pre>{"status": "ok", "model": "gemini-2.5-flash-lite"}</pre>
      </div>
    </div>
  </div>
</main>

<script>
const API = window.location.origin;

// ── Tab switching ──────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
}

// ── Endpoint accordion ─────────────────────────────────
function toggleEndpoint(header) {
  const body = header.nextElementSibling;
  body.classList.toggle('open');
}

// ── Copy text ──────────────────────────────────────────
function copyText(id) {
  const text = document.getElementById(id).innerText;
  navigator.clipboard.writeText(text).then(() => {
    event.target.textContent = 'Copied!';
    setTimeout(() => event.target.textContent = 'Copy', 1500);
  });
}

// ── Single clean ───────────────────────────────────────
async function runSingle() {
  const text = document.getElementById('single-input').value.trim();
  if (!text) return;

  const btn = document.getElementById('single-btn');
  const spin = document.getElementById('single-spin');
  const btnText = document.getElementById('single-btn-text');
  const errorBox = document.getElementById('single-error');
  const resultBox = document.getElementById('single-result');

  btn.disabled = true;
  spin.classList.add('show');
  btnText.textContent = 'Cleaning...';
  errorBox.classList.remove('show');
  resultBox.classList.remove('show');

  try {
    const res = await fetch(API + '/clean', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Server error');

    document.getElementById('single-output-text').textContent = data.cleaned;
    document.getElementById('single-time').textContent = data.time_seconds;
    document.getElementById('single-chars').textContent = data.cleaned.length;
    resultBox.classList.add('show');
  } catch(e) {
    errorBox.textContent = '❌ Error: ' + e.message;
    errorBox.classList.add('show');
  } finally {
    btn.disabled = false;
    spin.classList.remove('show');
    btnText.textContent = '✨ Clean Text';
  }
}

// ── Batch clean ────────────────────────────────────────
let batchCount = 1;

function addBatchItem() {
  batchCount++;
  const container = document.getElementById('batch-inputs');
  const div = document.createElement('div');
  div.className = 'batch-item';
  div.id = 'batch-' + (batchCount-1);
  div.innerHTML = `
    <button class="remove-btn" onclick="removeBatchItem(this)">✕</button>
    <div class="batch-idx">Text #${batchCount}</div>
    <textarea placeholder="Paste noisy Sinhala text here..." rows="4"></textarea>
  `;
  container.appendChild(div);
}

function removeBatchItem(btn) {
  btn.closest('.batch-item').remove();
  // re-number
  document.querySelectorAll('.batch-item .batch-idx').forEach((el, i) => {
    el.textContent = 'Text #' + (i+1);
  });
}

async function runBatch() {
  const textareas = document.querySelectorAll('#batch-inputs textarea');
  const texts = Array.from(textareas).map(t => t.value.trim()).filter(t => t);
  if (!texts.length) return;

  const btn = document.getElementById('batch-btn');
  const spin = document.getElementById('batch-spin');
  const btnText = document.getElementById('batch-btn-text');
  const errorBox = document.getElementById('batch-error');
  const resultsDiv = document.getElementById('batch-results');

  btn.disabled = true;
  spin.classList.add('show');
  btnText.textContent = `Cleaning ${texts.length} texts...`;
  errorBox.classList.remove('show');
  resultsDiv.innerHTML = '';

  try {
    const res = await fetch(API + '/clean/batch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({texts})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Server error');

    data.results.forEach(r => {
      const div = document.createElement('div');
      div.className = 'batch-result-item ' + (r.error ? 'failed' : 'success');
      div.innerHTML = r.error
        ? `<div class="result-label">Text #${r.index+1} — Failed</div>
           <div style="color:var(--accent);font-size:13px;">${r.error}</div>`
        : `<div style="display:flex;justify-content:space-between;margin-bottom:10px;">
             <div class="result-label" style="margin:0;">Text #${r.index+1} — Cleaned</div>
             <button class="copy-btn" onclick="navigator.clipboard.writeText(this.closest('.batch-result-item').querySelector('.result-text').innerText);this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',1500)">Copy</button>
           </div>
           <div class="result-text">${r.cleaned}</div>`;
      resultsDiv.appendChild(div);
    });

    const summary = document.createElement('div');
    summary.style = 'text-align:center;color:var(--muted);font-size:12px;margin-top:8px;';
    summary.textContent = `✅ ${texts.length} texts cleaned in ${data.total_time_seconds}s`;
    resultsDiv.appendChild(summary);

  } catch(e) {
    errorBox.textContent = '❌ Error: ' + e.message;
    errorBox.classList.add('show');
  } finally {
    btn.disabled = false;
    spin.classList.remove('show');
    btnText.textContent = '✨ Clean All';
  }
}

// Enter key in single input
document.getElementById('single-input').addEventListener('keydown', e => {
  if (e.ctrlKey && e.key === 'Enter') runSingle();
});
</script>
</body>
</html>"""
