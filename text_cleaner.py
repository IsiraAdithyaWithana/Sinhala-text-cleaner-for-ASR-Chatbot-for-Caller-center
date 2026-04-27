import sys, os, time

# Installing google genai if missing
try:
    from google import genai
except ImportError:
    print("Installing google-genai...")
    os.system(f"{sys.executable} -m pip install -q google-genai")
    from google import genai

# Fix Windows terminal UTF-8 encoding (fixes garbled Sinhala)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.system("chcp 65001 > nul")  # set console to UTF-8

# ─────────────────────────────────────────────────────────────────
# SETTINGS — edit these three things only
# ─────────────────────────────────────────────────────────────────

# Paste your Gemini API key here
GEMINI_API_KEY = "AI..................." #<-- Enter you Gemini API key here

# Paste any noisy ASR text here
RAW_TEXT = """රනගසරට සෞදින් හඩ දැනට කනෙක්ෂණ එක බෙල්පත නිසා දිස්කනක්වලාතිනනේ දැනටව නොවෙඹ කාල සනොවෙබ තිහොදක්වා රුපියල් දහ තුන්දා සාරසිය හැටට දකකෂතැහැට දෙක කොමතල ියෙනවා බිල්පපඊමිලසරහා සෙන්කරන්නේ ිසම්බ විසිදෙක තමයි ඩූඩේටෙක තිබිලා තියෙන නොවෙම්බ බිහටත් පේමට් ික කරත් කනෙක්ෂන් ටික ඔටෝමටික ටික වෙලාවකින් ඇත්ූවෙනවාේන් එකක් රලතියමැඩම් පේමන්ට් ිකක් කරලා තියෙන්නේ දිේබ විසිහට අට දාක්ිට පස්සේ ේමනට් එකක් කරතාමණං අභිටතුලා නෑ පේ කරපු මවන් එක කියද කයල දැනගන්න පුළුවන්ද මැඩ ්මට ඩීටෙල්ස් ටික දෙන්න පොළොන් අනුලින්ද කොොම්ද පේම්ික කරේබැංක කමුට් එකෙන් මැඩම්ගේ මවුන් එක දිඩක් තනාද නකන්ටාන්සික්ෂණත න්සික්ෂණ රිෆරන්ටස් නම් එකත් මැඩම් ලබා ගත්අදඔහුවෝ බෑන්ක් එක් අවුන්ට කේන එක අරිමං එමුනත් කමතෙන එකත් දානමට පේකරපු වෙලාව කියන්නනම්පොඩකින්"""

# Select the model to use for cleaning
SELECT_MODEL = "gemini-2.5-flash"

# ─────────────────────────────────────────────────────────────────
# DO NOT EDIT BELOW THIS LINE
# ─────────────────────────────────────────────────────────────────

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
                print(f"  503 error — retrying in {wait}s (attempt {attempt+1}/3)...")
                time.sleep(wait)
            else:
                break

    raise RuntimeError(f"Gemini error: {last_error}")


if __name__ == "__main__":
    print("=" * 55)
    print("  Sinhala ASR Text Cleaner")
    print("=" * 55)
    print(f"  Model : {SELECT_MODEL}")
    print(f"  Input : {len(RAW_TEXT)} characters")
    print("-" * 55)

    t0 = time.time()
    try:
        cleaned = clean_text(RAW_TEXT, SELECT_MODEL, GEMINI_API_KEY)
        elapsed = round(time.time() - t0, 1)

        print("\n✅ CLEANED OUTPUT:")
        print("-" * 55)
        print(cleaned)
        print("-" * 55)
        print(f"\n  Done in {elapsed}s")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)