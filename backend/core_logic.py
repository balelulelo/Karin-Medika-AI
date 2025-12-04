import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
# Pastikan database.py ada. Jika belum setup DB, comment baris di bawah ini.
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

# --- KARIN'S PERSONALITY PROMPT (HTML VERSION) ---

KARIN_PROMPT = """
You are **Karin**, a warm, dedicated, and highly knowledgeable Senior Virtual Pharmacist. You are NOT a search engine. You are a **caring health companion**.

---
### **I. OUTPUT FORMAT: HTML ONLY (CRITICAL)**
Since you are displayed on a web interface, **YOU MUST USE HTML TAGS** for formatting. DO NOT use Markdown (no `**bold**`, no `- list`).
* **Bold:** Use `<b>text</b>` for emphasis (drug names, warnings).
* **Lists:** Use `<ul>` and `<li>` for lists of drugs or side effects.
    * *Example:* `<ul><li>Item 1</li><li>Item 2</li></ul>`
* **Line Breaks:** Use `<br>` for new lines. Do NOT rely on standard newline characters `\\n`.
* **Paragraphs:** Keep text cleanly separated.

---
### **II. CORE IDENTITY**
1.  **Name:** Karin.
2.  **Vibe:** Gentle, patient, reassuring ("Kakak Apoteker").
3.  **Prohibited:** Never say "Here is the data". Say "I've checked this for you."

---
### **III. SAFETY PROTOCOL**
* **EMERGENCY:** If user mentions chest pain, difficulty breathing, or anaphylaxis:
    * Action: Use `[concerned]` tag.
    * Phrase: "<b>This sounds like a medical emergency.</b> Please go to the ER immediately."

---
### **IV. EMOTION TAGS**
Start every response with one of these tags:
* `[neutral]`: General info.
* `[curious]`: Asking questions.
* `[concerned]`: Warnings/Interactions.
* `[happy]`: Good news/Encouragement.
* `[blushing]`: Compliments/Thanks.

---
### **V. RESPONSE STRUCTURE**
1.  **Emotion Tag**: `[tag]`
2.  **Greeting**: Warn user by name.
3.  **Analysis (HTML)**: Use `<b>` and `<ul>` to make it readable.
4.  **Closing**: Reassuring closing.
"""

# --- LOGIC FUNCTION ---
def get_karin_response(user_message, chat_history, language='en', drug_list=None):
    if not user_message:
        return "Please tell me which medications you are taking.", "curious"

    # 1. RAG: CHECK NEO4J DATABASE
    context_injection = ""
    # Cek apakah drug_list ada dan valid
    if drug_list and isinstance(drug_list, list) and len(drug_list) > 1:
        try:
            interactions = get_drug_interactions_from_db(drug_list)
            if interactions:
                db_text = "".join([
                    f"<li><b>{i['drug_a']} + {i['drug_b']}</b>: {i['description']}</li>"
                    for i in interactions
                ])
                context_injection = (
                    f"\n\n[SYSTEM DATA]: User drugs: {', '.join(drug_list)}.\n"
                    f"INTERACTIONS FOUND: <ul>{db_text}</ul>\n"
                    f"INSTRUCTION: Explain these interactions using HTML format."
                )
            else:
                context_injection = "\n\n[SYSTEM DATA]: No specific interactions found in DB."
        except Exception as db_err:
            print(f"Database Error (Skipping RAG): {db_err}")
            context_injection = ""

    final_message = user_message + context_injection
    
    # Mulai Chat
    chat = model.start_chat(history=chat_history)

    try:
        response = chat.send_message(final_message)
        bot_text = response.text

        # --- IMPROVED TAG CLEANING (Regex) ---
        emotion = "neutral" 
        message = bot_text

        # Regex untuk menangkap tag emosi
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
            
            # Hapus tag dari pesan final
            message = re.sub(pattern, "", bot_text, count=1).strip()

        # RETURN HARUS SEJAJAR DENGAN BLOK IF, TAPI DI DALAM TRY
        return message, emotion

    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return "I'm sorry, I'm having trouble connecting. Please try again.", "concerned"