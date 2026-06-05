import subprocess
import sys
import os

# ─────────────────────────────────────────────────────────────────
# STEP 1 — Auto-install dependencies if missing
# ─────────────────────────────────────────────────────────────────
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])

try:
    from dotenv import load_dotenv
except ImportError:
    print("📦 Installing python-dotenv...")
    install("python-dotenv")
    from dotenv import load_dotenv

try:
    from google import genai
except ImportError:
    print("📦 Installing google-genai...")
    install("google-genai")
    from google import genai

# ─────────────────────────────────────────────────────────────────
# STEP 2 — Fix Windows terminal UTF-8 encoding
# ─────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.system("chcp 65001 > nul")

# ─────────────────────────────────────────────────────────────────
# STEP 3 — Auto-create .env if missing, validate API key
# ─────────────────────────────────────────────────────────────────
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
PLACEHOLDER = "YOUR_API_KEY_HERE"

if not os.path.exists(ENV_FILE):
    with open(ENV_FILE, "w") as f:
        f.write(f"GEMINI_API_KEY={PLACEHOLDER}\n")
    print("\n" + "=" * 55)
    print("  ✅ .env file created successfully!")
    print("=" * 55)
    print(f"\n  📂 Location: {ENV_FILE}")
    print("\n  👉 Open the .env file and replace:")
    print(f"     GEMINI_API_KEY={PLACEHOLDER}")
    print("     with your real Gemini API key.")
    print("\n  Then run this script again. ✅")
    print("=" * 55 + "\n")
    sys.exit(0)

# Load the .env file
load_dotenv(ENV_FILE)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if not GEMINI_API_KEY or GEMINI_API_KEY == PLACEHOLDER:
    print("\n" + "=" * 55)
    print("  ⚠️  API key not set!")
    print("=" * 55)
    print(f"\n  📂 Open this file: {ENV_FILE}")
    print("\n  👉 Replace:")
    print(f"     GEMINI_API_KEY={PLACEHOLDER}")
    print("     with your real Gemini API key.")
    print("\n  Then run this script again. ✅")
    print("=" * 55 + "\n")
    sys.exit(0)

# ─────────────────────────────────────────────────────────────────
# STEP 4 — Logging & Settings
# ─────────────────────────────────────────────────────────────────
import time
import glob
import logging
import shutil

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "process.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

SELECT_MODEL = "gemini-3-flash-preview"

# Directory Structure — all relative to this script's location
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR   = os.path.join(BASE_DIR, "input_audios")
OUTPUT_DIR  = os.path.join(BASE_DIR, "cleaned_outputs")
ARCHIVE_DIR = os.path.join(BASE_DIR, "processed_archive")

# ─────────────────────────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────────────────────────
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
# CORE CLEANING FUNCTION
# ─────────────────────────────────────────────────────────────────
def clean_text(noisy_text, model, api_key):
    client = genai.Client(api_key=api_key)
    last_error = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=CLEAN_PROMPT.format(text=noisy_text)
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

    raise RuntimeError(f"Gemini API failure after retries: {last_error}")

# ─────────────────────────────────────────────────────────────────
# BATCH PROCESSING LOOP
# ─────────────────────────────────────────────────────────────────
def process_batch():
    logging.info(f"STARTING BATCH RUN | Model: {SELECT_MODEL}")
    print()

    # Ensure all three directories exist
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    input_files = glob.glob(os.path.join(INPUT_DIR, "*.txt"))

    if not input_files:
        logging.warning(f"No .txt files found in 'input_audios/'. Please add files and run again.")
        return

    logging.info(f"Found {len(input_files)} file(s) to process.")

    success_count = 0
    fail_count = 0

    for file_path in input_files:
        filename = os.path.basename(file_path)
        name_only, extension = os.path.splitext(filename)

        output_filename = f"{name_only}_cleaned{extension}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        archive_path = os.path.join(ARCHIVE_DIR, filename)

        logging.info(f"Processing: {filename}")
        t0 = time.time()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                noisy_text = f.read().strip()

            if not noisy_text:
                logging.warning(f"Skipped {filename} — file is empty.")
                shutil.move(file_path, archive_path)
                continue

            cleaned_text = clean_text(noisy_text, SELECT_MODEL, GEMINI_API_KEY)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)

            shutil.move(file_path, archive_path)

            elapsed = round(time.time() - t0, 1)
            logging.info(f"SUCCESS: -> {output_filename} ({elapsed}s)")
            success_count += 1

        except Exception as e:
            logging.error(f"FAILED: {filename} — Error: {e}")
            fail_count += 1

    logging.info("-" * 55)
    logging.info(f"BATCH COMPLETE | Successful: {success_count} | Failed: {fail_count}")

if __name__ == "__main__":
    process_batch()