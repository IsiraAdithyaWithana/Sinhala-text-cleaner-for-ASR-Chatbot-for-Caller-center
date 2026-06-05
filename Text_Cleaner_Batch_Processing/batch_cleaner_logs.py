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

# ── How many .txt files to send together in one API call ──────────
# Sending multiple files per call saves cost by reusing the prompt
# once instead of repeating it for every file.
# Recommended: 3 to 5. Max: 10 (higher risks Gemini mixing outputs).
Number_of_TXT_Files_to_Send = 3

# Directory Structure — all relative to this script's location
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR   = os.path.join(BASE_DIR, "input_audios")
OUTPUT_DIR  = os.path.join(BASE_DIR, "cleaned_outputs")
ARCHIVE_DIR = os.path.join(BASE_DIR, "processed_archive")

# ─────────────────────────────────────────────────────────────────
# PROMPT
# ─────────────────────────────────────────────────────────────────
# Each file is labeled [FILE_1], [FILE_2] etc. in the prompt.
# Gemini returns cleaned output using the same labels.
BATCH_PROMPT = """You are a Sinhala language expert processing ASR transcripts from telecommunication call centers.

Your objective is to reconstruct clean, coherent Sinhala conversations while strictly filtering out ASR hallucinations.

Rules for Cleaning:
1. Merge split words and fix corrupted Unicode characters.
2. Contextual Pruning: DELETE hallucinated words that clearly do not match the telecommunications/billing context.
3. Noise Removal: DELETE isolated 1-2 letter fragments ONLY IF they lack semantic or grammatical meaning in the sentence. DO NOT delete valid functional words (e.g., 'නෑ', 'පේ', 'ට', 'ගේ').
4. Keep numbers, English terms (bill, payment, connection, online, account, reference), and caller details exactly as they appear.
5. Output ONE continuous plain paragraph per file in correct Sinhala script. No extra formatting.

You will receive {count} noisy ASR texts labeled [FILE_1], [FILE_2], etc.
Return your cleaned output using the EXACT same labels in this format:

[FILE_1]
<cleaned text here>

[FILE_2]
<cleaned text here>

Do NOT merge files. Do NOT skip any file. One label per file, one paragraph per file.

{texts}"""

# ─────────────────────────────────────────────────────────────────
# CORE BATCH CLEANING FUNCTION
# ─────────────────────────────────────────────────────────────────
def clean_batch_of_texts(texts_dict, model, api_key):
    """
    texts_dict: { "FILE_1": "noisy text...", "FILE_2": "noisy text...", ... }
    Returns:    { "FILE_1": "cleaned text...", "FILE_2": "cleaned text...", ... }
    """
    client = genai.Client(api_key=api_key)

    # Build the labeled input block
    labeled_input = ""
    for label, text in texts_dict.items():
        labeled_input += f"[{label}]\n{text}\n\n"

    prompt = BATCH_PROMPT.format(
        count=len(texts_dict),
        texts=labeled_input.strip()
    )

    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            raw_output = response.text.strip()

            # ── Parse labeled output back into a dict ────────────
            results = {}
            current_label = None
            current_lines = []

            for line in raw_output.splitlines():
                stripped = line.strip()
                # Check if this line is a label like [FILE_1]
                if stripped.startswith("[FILE_") and stripped.endswith("]"):
                    # Save previous block
                    if current_label:
                        results[current_label] = " ".join(current_lines).strip()
                    current_label = stripped[1:-1]  # remove [ and ]
                    current_lines = []
                else:
                    if current_label and stripped:
                        current_lines.append(stripped)

            # Save last block
            if current_label:
                results[current_label] = " ".join(current_lines).strip()

            return results

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
    logging.info(f"STARTING BATCH RUN | Model: {SELECT_MODEL} | Files per API call: {Number_of_TXT_Files_to_Send}")
    print()

    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    input_files = glob.glob(os.path.join(INPUT_DIR, "*.txt"))

    if not input_files:
        logging.warning("No .txt files found in 'input_audios/'. Please add files and run again.")
        return

    logging.info(f"Found {len(input_files)} file(s) to process.")

    success_count = 0
    fail_count = 0

    # ── Split all files into chunks of Number_of_TXT_Files_to_Send ──
    chunks = [
        input_files[i : i + Number_of_TXT_Files_to_Send]
        for i in range(0, len(input_files), Number_of_TXT_Files_to_Send)
    ]

    logging.info(f"Grouped into {len(chunks)} API call(s) of up to {Number_of_TXT_Files_to_Send} file(s) each.")
    print()

    for chunk_index, chunk in enumerate(chunks, start=1):
        logging.info(f"── API Call {chunk_index}/{len(chunks)} | Sending {len(chunk)} file(s) ──")

        # Build labeled dict for this chunk
        texts_dict = {}
        file_map   = {}  # label -> file_path
        for i, file_path in enumerate(chunk, start=1):
            label = f"FILE_{i}"
            filename = os.path.basename(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if not content:
                    logging.warning(f"Skipped {filename} — file is empty.")
                    archive_path = os.path.join(ARCHIVE_DIR, filename)
                    shutil.move(file_path, archive_path)
                    continue
                texts_dict[label] = content
                file_map[label]   = file_path
            except Exception as e:
                logging.error(f"Could not read {filename} — {e}")
                fail_count += 1

        if not texts_dict:
            continue

        t0 = time.time()
        try:
            cleaned_results = clean_batch_of_texts(texts_dict, SELECT_MODEL, GEMINI_API_KEY)

            for label, file_path in file_map.items():
                filename = os.path.basename(file_path)
                name_only, extension = os.path.splitext(filename)
                output_filename = f"{name_only}_cleaned{extension}"
                output_path  = os.path.join(OUTPUT_DIR, output_filename)
                archive_path = os.path.join(ARCHIVE_DIR, filename)

                cleaned_text = cleaned_results.get(label, "").strip()

                if not cleaned_text:
                    logging.error(f"FAILED: {filename} — Gemini returned empty output for {label}.")
                    fail_count += 1
                    continue

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_text)

                shutil.move(file_path, archive_path)

                elapsed = round(time.time() - t0, 1)
                logging.info(f"SUCCESS: {filename} -> {output_filename} ({elapsed}s)")
                success_count += 1

        except Exception as e:
            logging.error(f"API call {chunk_index} FAILED — {e}")
            fail_count += len(texts_dict)

        print()

    logging.info("-" * 55)
    logging.info(f"BATCH COMPLETE | Successful: {success_count} | Failed: {fail_count}")

if __name__ == "__main__":
    process_batch()