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
GEMINI_API_KEY = "AI......................" #<-- Enter you Gemini API key here

# Paste any noisy ASR text here
RAW_TEXT = """ආයිබෝවන් මම රේනුක ට පුළුවනිෝබට සහයවන්න ගේබලත්ම ශකකලබලල කියන්න මැඩ එන්ටකරපු නම් එක අදාලවත කනෙක්ෂණකි වස්කර බිඑකයිකයි විසි හතරයි දහ නම යයි අතසිය හ්ත එකනන් එකද මමඩම් කනේෂ එකට අදාව අයිතිකර්ෙ නම තැනකන්න පුළුවන්තනල මතිමෙරදී ඉන්නාමඩීලකෂ ල බකියන් කරාක ඇමතිමෙ රදීනමට රනදසර සෞදි් නත්දැනනෙක්ෂඑක වෙල්ප නිසා දක්කැන්ලතිය දැනතව ොවෙඹ කාලසනොවෙම්බ තිහ දක්වා රුපියල් දහුන් සාරසය  දෙක්තහැ දකකමදත්තයවා බල්පතීමිලරහසෙනරන්නේ දිසෙම්බ ිසිදෙක තමයි ජඩේක ටිලෙන නොවෙන්බ බහට පීමට් ික කර කනෙක්න් ටික ඔතෝ් තික ටික වෙලාවකින් ත්ූවෙනවා රදපමඩම් ේමන් ෙක් කරලා තියෙන්නේ ඕදිසේබ විසහ අට දිට පත්සයීමන් එිකක්ද තමනං අභ්ෙිලානපේකරපු මෞ්ික කියදකර දැනන්න පුළුවන්ද මට ට ඩීටල්ස් ික දෙන්නුල අනුලින්ද කෝම්ද පීම්ක කරබැකකවුට් එකෙන් මැඩ්ගේ මවුන් එකදඩ්ත ලනන්තාංශික්ෂණ ෙෆරනස් නම් එකත් මැඩම ලබාකත්ත ගේන කම්න කත් දානම ට කරපු වෙලාව කියන්න තයි හතිස් පහයුත්කරපු බැං එක මොකක්දමට නේමේෂන් ත්පැ්එකනහතහතලිස්පහනත වෙලාව මඩ  සංශක්ෂ් රෆ් නම් එක දේන පුළන්ද මට ලෝ මැනතලන්න කෙරෙන්න හනේ ෝඅභ්ට්ටලා නැහැමන මෙතකොට පි කර්නේ බිල්ම්තන ක් දාල කැන්ණ කත්තිය් ක ක බිලින් ප්ින් තමසැලට අ්තනෙත් රමට්ටිය කරන් නං කම්තර එකාන ටික වෙලාවකින් මකික්වයිමටසාංශික්ෂ නම් එකතෙන්න පුළුවන්ද ්්අතසීය හත්තතුනයිදෙසියානු පහතාකන යිතිකරුම ට කතා කරන්නේ මට කනට්මබල් නම් එක මඩ ම කල්කරන නම් කට ම ිල්කම් තැ එකක් ුොර මම යො ොකරපු කක්යන කට දාළ පකරන නම් එක මැඩට කල්කරන මබලි් න් එකට එ සලත් එකක් පන්රකනෙක්ෂ කත් ැත්තයු ක තක්ම ටික වෙලාකන් කකළ බලන්න රි එල්තී මොබිටර මොට සමෙම හරිමඩ වෙනත්ම දැනිරීමට අවශ්‍යද මාලබා දුන් සේවය ඇගම දහ දයු තන්න සතති මොභිටලමොට ස්තුතිය සපත"""

# Select the model to use for cleaning
SELECT_MODEL = "gemini-2.5-flash" 

# ─────────────────────────────────────────────────────────────────
# DO NOT EDIT BELOW THIS LINE
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