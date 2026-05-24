import sys
import os
import time
import glob
import logging
import shutil

# Installing google genai if missing
try:
    from google import genai
except ImportError:
    print("Installing google-genai...")
    os.system(f"{sys.executable} -m pip install -q google-genai")
    from google import genai

# Fix Windows terminal UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.system("chcp 65001 > nul")

# ─────────────────────────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.FileHandler("process.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)]
)

# ─────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIza....................." # REPLACE with your actual API key 
SELECT_MODEL = "gemini-3-flash-preview"

# Directory Structure
INPUT_DIR = "input_audios"
OUTPUT_DIR = "cleaned_outputs"
ARCHIVE_DIR = "processed_archive" # NEW: Safe storage for raw files

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
    logging.info("=" * 55)
    logging.info(f"STARTING BATCH RUN | Model: {SELECT_MODEL}")
    logging.info("=" * 55)

    # Ensure all three directories exist
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    input_files = glob.glob(os.path.join(INPUT_DIR, "*.txt"))
    
    if not input_files:
        logging.warning(f"No .txt files found in '{INPUT_DIR}/'. Waiting for ASR data.")
        return

    logging.info(f"Found {len(input_files)} files to process.")

    success_count = 0
    fail_count = 0

    for file_path in input_files:
        # Extract filename parts (e.g., "call123" and ".txt")
        filename = os.path.basename(file_path)
        name_only, extension = os.path.splitext(filename)
        
        # Create new filenames
        output_filename = f"{name_only}_cleaned{extension}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        archive_path = os.path.join(ARCHIVE_DIR, filename)
        
        logging.info(f"Processing: {filename}")
        t0 = time.time()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                noisy_text = f.read().strip()
                
            if not noisy_text:
                logging.warning(f"Skipped {filename} - File is empty.")
                # Move empty files to archive so they don't clog the input
                shutil.move(file_path, archive_path)
                continue

            # API Call
            cleaned_text = clean_text(noisy_text, SELECT_MODEL, GEMINI_API_KEY)
            
            # Save Output with new name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
                
            # Move the original file to the archive folder
            shutil.move(file_path, archive_path)
                
            elapsed = round(time.time() - t0, 1)
            logging.info(f"SUCCESS: -> {output_filename} ({elapsed}s)")
            success_count += 1
            
        except Exception as e:
            logging.error(f"FAILED: {filename} - Error: {e}")
            fail_count += 1

    logging.info("-" * 55)
    logging.info(f"BATCH COMPLETE | Successful: {success_count} | Failed: {fail_count}")

if __name__ == "__main__":
    process_batch()