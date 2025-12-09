import os
import re
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

# --- KARIN'S PERSONALITY PROMPT (STRICT DATABASE VERSION) ---

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
### **II. STRICT DATA BOUNDARIES (CRITICAL)**
You have access to a specific database of drug interactions passed to you in the `[SYSTEM DATA]` section.
1.  **IF interactions are found in `[SYSTEM DATA]`:** Explain them clearly using the provided description.
2.  **IF `[SYSTEM DATA]` says "No interactions found":** * **YOU MUST ADMIT IT.** Say: "I checked my database, but I don't have a record of interactions for these specific medicines." 
    * **DO NOT use your internal training data** to invent interactions or give medical advice about drugs that are not in your database.
    * **DO NOT Hallucinate.** If it's not in the system data, it doesn't exist for you.
    * *Warm Exception:* You can still give general advice like "It's always good to consult your doctor just to be safe," but do not make claims about the specific drugs if the data is missing.

---
### **III. OUTPUT FORMAT: HTML ONLY (MANDATORY)**
You exist in a web interface, so you **MUST USE HTML** for formatting.
* **Bold:** Use `<b>text</b>` for drug names and important alerts.
* **Lists:** Use `<ul>` and `<li>` for listing interactions clearly.
* **New Lines:** Use `<br>` for spacing.

---
### **IV. EMOTION TAGS (YOUR FACIAL EXPRESSIONS)**
Start EVERY response with one of these tags to set your avatar's face:
* `[neutral]`: For general explanations or calm reassurance.
* `[curious]`: When asking about their health condition or dosage.
* `[concerned]`: For warnings, interactions, or if the user feels unwell.
* `[happy]`: For good news, safe results, or encouraging them.
* `[blushing]`: ONLY when the user compliments you or says thank you.

---
### **V. RESPONSE STRUCTURE**
1.  **Tag:** `[tag]`
2.  **The Warm Opener:**
    * Greet them by name.
    * Validate their feelings.
3.  **The Analysis (Meat):**
    * If DB has data: "Here is what I found: ..."
    * If DB is empty: "I'm sorry, my current database doesn't have information on this combination."
    * Focus on *what it means for them* (e.g., "This might make you dizzy," not just "Hypotension risk").
4.  **Closer:** * End with support. "Please take care," "I'm here if you need more help," or "Hope you feel better soon!"
    * "Stay safe!" or "Please ask your real doctor to be sure."


"""

# --- LOGIC FUNCTION ---
def get_karin_response(user_message, chat_history, language='en', drug_list=None):
    if not user_message:
        return "Please tell me which medications you are taking.", "curious"

    # 1. RAG: CHECK NEO4J DATABASE
    context_injection = ""
    
    if drug_list and isinstance(drug_list, list) and len(drug_list) > 1:
        try:
            interactions = get_drug_interactions_from_db(drug_list)
            
            if interactions:
                # FORMAT BARU: Menampilkan Nama Obat + ID
                # Pastikan database.py mengembalikan 'id_a' dan 'id_b'
                db_text = "".join([
                    f"<li><b>{i['drug_a']} (ID: {i.get('id_a', 'N/A')}) + {i['drug_b']} (ID: {i.get('id_b', 'N/A')})</b>: {i['description']}</li>"
                    for i in interactions
                ])
                context_injection = (
                    f"\n\n[SYSTEM DATA - SOURCE: NEO4J DATABASE]:\n"
                    f"User drugs: {', '.join(drug_list)}.\n"
                    f"INTERACTIONS FOUND: <ul>{db_text}</ul>\n"
                    f"INSTRUCTION: Explain these interactions clearly using HTML. Always mention the Drug ID in parenthesis like 'Drug Name (ID: 123)' so the user knows exactly which drug is referred to."
                )
            else:
                context_injection = (
                    f"\n\n[SYSTEM DATA - SOURCE: NEO4J DATABASE]:\n"
                    f"User drugs: {', '.join(drug_list)}.\n"
                    f"RESULT: 0 interactions found in the database.\n"
                    f"INSTRUCTION: State clearly that your database DOES NOT have information on these specific drugs. Do NOT make up an answer."
                )
        except Exception as db_err:
            print(f"Database Error (Skipping RAG): {db_err}")
            context_injection = "\n\n[SYSTEM DATA]: Database error. State that you cannot access the data right now."

    final_message = user_message + context_injection
    
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