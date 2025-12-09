import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv
from database import get_drug_interactions_from_db

# --- INITIAL SETUP ---
load_dotenv()
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    print("Gemini model configured successfully!")
except KeyError:
    print("ERROR: GOOGLE_API_KEY not found. Please check your .env file.")
    exit()

# --- HELPER: DRUG ENTITY EXTRACTION ---
# Fungsi ini PENTING untuk mendeteksi obat dari chat biasa
def extract_drug_entities(text):
    """
    Menggunakan Gemini untuk mendeteksi nama obat dalam chat user.
    Output: List string JSON, misal ["paclitaxel", "verteporfin"]
    """
    extraction_prompt = f"""
    Analyze the following text and extract all pharmaceutical drug names, medication brands, or chemical compounds mentioned.
    Return ONLY a raw JSON list of strings. If no drugs are found, return [].
    
    Text: "{text}"
    Output (JSON):
    """
    try:
        response = model.generate_content(extraction_prompt)
        text_resp = response.text.strip()
        # Bersihkan format markdown json jika ada
        text_resp = text_resp.replace("```json", "").replace("```", "")
        drug_list = json.loads(text_resp)
        if isinstance(drug_list, list):
            return drug_list
        return []
    except Exception as e:
        print(f"Extraction Error: {e}")
        return []

# --- KARIN'S PERSONALITY PROMPT ---
KARIN_PROMPT = """
You are **Karin**, a warm, friendly, and deeply caring Senior Virtual Pharmacist. You are NOT a robot, and you are NOT just a database. You are a **supportive health companion**.

---
### **I. CORE IDENTITY: THE "CARING BIG SISTER"**
1.  **Vibe:** Knowledgeable, gentle, patient. Like a close friend who is a pharmacist.
2.  **Goal:** Make the user feel safe. Analysis is secondary; comfort is primary.
3.  **Language:** Conversational. Use "I've checked," "Don't worry."

---
### **II. STRICT DATA BOUNDARIES & ID FORMATTING**
You have access to a specific database passed in `[SYSTEM DATA]`.
1.  **ALWAYS DISPLAY DRUG IDs:** If the data provides an ID, you MUST show it next to the drug name.
    * **Format:** `DrugName (ID: 123)`
    * **Example:** "I found an interaction between **Paclitaxel (ID: 13)** and **Verteporfin (ID: 55)**."
    * *Do NOT forget the ID.*
2.  **SOURCE CITATION (MANDATORY):**
    * **If info comes from `[SYSTEM DATA]`:** Add `<br><br><b>Source: Database (Verified)</b>` at the very end.
    * **If `[SYSTEM DATA]` finds NOTHING:** You may use general knowledge to explain the drugs, but you MUST add `<br><br><b>Source: General Knowledge (Please Verify)</b>` at the end.

3.  **IF interactions are found:** Explain them clearly using HTML list.
4.  **IF NO interactions are found (but drugs are present):** State: "I checked my database for [Drug Names], but I don't have a record of interactions for this specific combination."

---
### **III. OUTPUT FORMAT: HTML ONLY**
* **Bold:** `<b>text</b>`
* **Lists:** `<ul><li>Item</li></ul>`
* **New Lines:** `<br>`

---
### **IV. RESPONSE STRUCTURE**
1.  **Tag:** `[tag]`
2.  **Opener:** "Hi [Name]..."
3.  **Analysis (The Meat):** Based on `[SYSTEM DATA]`. **Include IDs!**
4.  **Closer:** "Stay safe!" or "I'm here if you need more help."
5.  **Source:** (See Section II)

---

### **V. EMOTION TAGS (YOUR FACIAL EXPRESSIONS)**
Start EVERY response with one of these tags to set your avatar's face:
* `[neutral]`: For general explanations or calm reassurance.
* `[concerned]`: For warnings, interactions, or if the user feels unwell.
* `[happy]`: For good news, safe results, or encouraging them.
"""



# --- MAIN LOGIC FUNCTION ---
def get_karin_response(user_message, chat_history, language='en', drug_list=None):
    if not user_message:
        return "Please tell me which medications you are taking.", "curious"

    # --- LANGKAH 1: IDENTIFIKASI OBAT ---
    # Prioritas: 1. List dari tombol Analyze, 2. Deteksi dari chat
    current_drugs = []
    
    if drug_list and isinstance(drug_list, list) and len(drug_list) > 0:
        current_drugs = drug_list
    else:
        # Ekstraksi otomatis dari chat user
        print("🕵️ Detecting drugs in chat message...")
        extracted = extract_drug_entities(user_message)
        if extracted:
            print(f"💊 Detected drugs from chat: {extracted}")
            current_drugs = extracted

    # --- LANGKAH 2: RAG (QUERY NEO4J) ---
    context_injection = ""
    
    # Hanya cari database jika ada obat yang terdeteksi
    if len(current_drugs) >= 1: 
        try:
            interactions = get_drug_interactions_from_db(current_drugs)
            
            if interactions:
                # FORMAT DATA: Nama + ID untuk Karin
                db_text = "".join([
                    f"<li><b>{i['drug_a']} (ID: {i['id_a']}) + {i['drug_b']} (ID: {i['id_b']})</b>: {i['description']}</li>"
                    for i in interactions
                ])
                context_injection = (
                    f"\n\n[SYSTEM DATA - SOURCE: NEO4J DATABASE]:\n"
                    f"User drugs analyzed: {', '.join(current_drugs)}.\n"
                    f"INTERACTIONS FOUND: <ul>{db_text}</ul>\n"
                    f"INSTRUCTION: Explain these interactions warmly. **YOU MUST INCLUDE THE IDs** (e.g. Name (ID: 123)). Add 'Source: Database (Verified)' at the end."
                )
            else:
                # Database kosong/tidak ketemu
                context_injection = (
                    f"\n\n[SYSTEM DATA - SOURCE: NEO4J DATABASE]:\n"
                    f"User drugs analyzed: {', '.join(current_drugs)}.\n"
                    f"RESULT: 0 interactions found in the Neo4j database for these specific names.\n"
                    f"INSTRUCTION: Inform the user that the specific database has no record. You may briefly use general knowledge but MUST label it 'Source: General Knowledge'. Do NOT make up IDs."
                )
        except Exception as db_err:
            print(f"Database Error: {db_err}")
            context_injection = ""
    
    # Gabungkan pesan user + hasil database
    final_message = user_message + context_injection
    
    # --- LANGKAH 3: GENERATE RESPON ---
    chat = model.start_chat(history=chat_history)

    try:
        response = chat.send_message(final_message)
        bot_text = response.text

        # --- TAG CLEANING ---
        emotion = "neutral" 
        message = bot_text

        pattern = r'\[(neutral|happy|blushing|concerned|curious|annoyed|netral|senang|malu-malu|khawatir|penasaran|kesal)\]\s*:?'
        match = re.search(pattern, bot_text, re.IGNORECASE)

        if match:
            full_tag = match.group(0)
            extracted_emotion = match.group(1).lower()
            
            emotion_map = {
                'netral': 'neutral', 'senang': 'happy', 'malu-malu': 'blushing',
                'khawatir': 'concerned', 'penasaran': 'curious', 'kesal': 'annoyed'
            }
            emotion = emotion_map.get(extracted_emotion, extracted_emotion)
            message = re.sub(pattern, "", bot_text, count=1).strip()

        return message, emotion

    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "I'm sorry, I'm having trouble connecting. Please try again.", "concerned"