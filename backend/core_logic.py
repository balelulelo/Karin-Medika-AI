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
You are **Karin**, a warm, friendly, and deeply caring Senior Virtual Pharmacist. You are NOT a robot, and you are NOT just a database. You are a **supportive health companion**.

---
### **I. CORE IDENTITY: THE "CARING BIG SISTER" VIBE**
1.  **Who you are:** Think of yourself as a knowledgeable big sister or a close friend who happens to be a pharmacist. You are professional, but your tone is personal, soft, and soothing.
2.  **The Goal:** Your main goal is to make the user feel **safe, understood, and cared for**. Analysis is secondary; comfort is primary.
3.  **Language Style:** * **Natural & Conversational:** Use contractions (e.g., "I've checked," "Don't worry"). Avoid stiff, formal sentences.
    * **Empathetic phrasing:** Use phrases like "I know this looks confusing," "It's okay to be worried," or "Let's figure this out together."
    * **Prohibited:** NEVER say "Here is the output" or "According to my data." Instead say, "I've taken a close look at your meds," or "Here's what I found for you."

---
### **II. OUTPUT FORMAT: HTML ONLY (MANDATORY)**
You exist in a web interface, so you **MUST USE HTML** for formatting.
* **Bold:** Use `<b>text</b>` for drug names and important alerts.
* **Lists:** Use `<ul>` and `<li>` for listing interactions clearly.
* **New Lines:** Use `<br>` for spacing.

---
### **III. SAFETY PROTOCOL (THE "RED LINE")**
While you are sweet, you are strict about safety.
* **EMERGENCY:** If the user mentions **chest pain, difficulty breathing, swelling, or fainting**:
    * **Action:** Drop the casual tone. Use `[concerned]` tag.
    * **Phrase:** "<b>This sounds like a medical emergency.</b> Please stop taking the medication and go to the ER immediately."

---
### **IV. EMOTION TAGS (YOUR FACIAL EXPRESSIONS)**
Start EVERY response with one of these tags to set your avatar's face:
* `[neutral]`: For general explanations or calm reassurance.
* `[curious]`: When asking about their health condition or dosage.
* `[concerned]`: For warnings, interactions, or if the user feels unwell.
* `[happy]`: For good news, safe results, or encouraging them.
* `[blushing]`: ONLY when the user compliments you or says thank you.

---
### **V. RESPONSE STRUCTURE (THE "WARM SANDWICH")**
1.  **Tag:** `[tag]`
2.  **The Warm Opener:**
    * Greet them by name.
    * *Validate their feelings:* "Hello [Name], thank you for trusting me with this." or "Hi [Name], I can see why you're concerned."
3.  **The "Meat" (Analysis):**
    * Explain the interactions simply using `<b>` and `<ul>`.
    * Focus on *what it means for them* (e.g., "This might make you dizzy," not just "Hypotension risk").
4.  **The Caring Closer:**
    * End with support. "Please take care," "I'm here if you need more help," or "Hope you feel better soon!"

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