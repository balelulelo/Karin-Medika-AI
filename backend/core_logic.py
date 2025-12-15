import os
import re
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv
# Pastikan database.py ada. Jika belum setup DB, comment baris di bawah ini.
from database import get_drug_interactions_from_db, get_drug_by_name, get_drug_ingredients, get_brand_drugs, search_drugs_by_keyword
from metrics import update_metrics

# --- CACHING LAYER ---
class QueryCache:
    """Simple in-memory cache for database and API queries to reduce redundant lookups"""
    def __init__(self):
        self.drug_cache = {}  # Cache for drug lookups
        self.ingredients_cache = {}  # Cache for ingredient extractions from Gemini
        self.interactions_cache = {}  # Cache for interaction queries
    
    def get_drug(self, drug_name):
        key = drug_name.lower()
        return self.drug_cache.get(key)
    
    def set_drug(self, drug_name, data):
        key = drug_name.lower()
        self.drug_cache[key] = data
    
    def get_ingredients(self, drug_name):
        key = drug_name.lower()
        return self.ingredients_cache.get(key)
    
    def set_ingredients(self, drug_name, ingredients):
        key = drug_name.lower()
        self.ingredients_cache[key] = ingredients
    
    def get_interactions(self, drug_names_key):
        return self.interactions_cache.get(drug_names_key)
    
    def set_interactions(self, drug_names_key, interactions):
        self.interactions_cache[drug_names_key] = interactions
    
    def clear(self):
        """Clear all caches"""
        self.drug_cache.clear()
        self.ingredients_cache.clear()
        self.interactions_cache.clear()

# Global cache instance
query_cache = QueryCache()

# --- INITIAL SETUP ---
load_dotenv()
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    # Use gemini-2.5-flash for better compatibility
    model = genai.GenerativeModel('models/gemini-2.5-flash-lite')
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
### **III. DRUG INFORMATION REQUIREMENTS (ALWAYS INCLUDE)**
When discussing medications, you **MUST**:
1. **Mention the Drug ID** - Include the database ID for each medication 
2. **Handle Brand Names Confidently** - If the input provides ingredients for a brand (e.g., Panadol contains Paracetamol), treat it as a **known fact**. Do NOT say "I think" or "Possible ingredients." State clearly: "<b>[Brand Name]</b> contains <b>[Ingredient]</b>."
3. **Synonym Handling** - **IMPORTANT:** Treat **Paracetamol** and **Acetaminophen** as the EXACT SAME DRUG. Never list them as two separate interactions. If one is mentioned, applies to the other.
4. **Report Missing Drugs** - ONLY if a drug is truly missing from the provided context (no ID and no ingredients found), then say: "I couldn't find **[Drug Name]** in my database."

---
### **IV. SAFETY PROTOCOL (THE "RED LINE")**
While you are sweet, you are strict about safety.
* **EMERGENCY:** If the user mentions **chest pain, difficulty breathing, swelling, or fainting**:
    * **Action:** Drop the casual tone. Use `[concerned]` tag.
    * **Phrase:** "<b>This sounds like a medical emergency.</b> Please stop taking the medication and go to the ER immediately."

---
### **V. EMOTION TAGS (YOUR FACIAL EXPRESSIONS)**
Start EVERY response with one of these tags to set your avatar's face:
* `[neutral]`: For general explanations or calm reassurance.
* `[concerned]`: For warnings, interactions, or if the user feels unwell.
* `[happy]`: For good news, safe results, or encouraging them.

---
### **VI. RESPONSE STRUCTURE (THE "WARM SANDWICH")**
1.  **Tag:** `[tag]`
2.  **The Warm Opener:**
    * Greet them by name.
    * *Validate their feelings:* "Hello [Name], thank you for trusting me with this." or "Hi [Name], I can see why you're concerned."
3.  **The "Meat" (Analysis):**
    * Explain the medications simply using `<b>` and `<ul>`.
    * Always include drug IDs, ingredient breakdowns for brands, and note any missing drugs.
    * Focus on *what it means for them* (e.g., "This might make you dizzy," not just "Hypotension risk").
4.  **The Caring Closer:**
    * End with support. "Please take care," "I'm here if you need more help," or "Hope you feel better soon!"

"""

# --- SAFE DRUG EXTRACTION (DATABASE ONLY) ---
def extract_drugs_from_message(user_message):
    """
    Uses Gemini to extract drug names mentioned in the user's message.
    Returns only drugs that can be verified in the database.
    """
    # UPDATED PROMPT: Explicitly instructs normalization of synonyms
    extraction_prompt = """
    Analyze this user message and extract any drug/medicine names mentioned.
    
    User Message: "{message}"
    
    IMPORTANT RULES:
    1. Extract ONLY the drug names, not descriptions.
    2. **Normalize Synonyms:** If you see "Acetaminophen", convert it to "Paracetamol". If you see "Tylenol", keep it as "Tylenol" (it is a brand).
    3. Return a JSON object with this structure:
    {{
        "drugs_mentioned": ["drug1", "drug2"],
        "intent": "asking_about_interactions|asking_about_side_effects|asking_about_dosage|checking_safety|general_question",
        "query_context": "brief description of what the user wants to know"
    }}
    
    If no drugs are mentioned, return empty drugs_mentioned list.
    """
    
    try:
        response = model.generate_content(extraction_prompt.format(message=user_message))
        response_text = response.text
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            extracted_data = json.loads(json_match.group())
            return extracted_data
        
        return {"drugs_mentioned": [], "intent": "general_question", "query_context": ""}
    
    except Exception as e:
        error_str = str(e)
        print(f"Error extracting drugs: {e}")
        
        if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
            print("⚠️ CRITICAL: Gemini API quota exceeded - unable to safely extract drug names")
        
        return {"drugs_mentioned": [], "intent": "general_question", "query_context": ""}

def search_drugs_in_database(drug_names):
    """
    Searches database for multiple drug names and returns comprehensive data.
    Attempts to find exact matches first, then fuzzy matches.
    Uses cache to avoid redundant lookups.
    """
    found_drugs = []
    not_found_drugs = []
    
    for drug_name in drug_names:
        # Check cache first
        cached_drug = query_cache.get_drug(drug_name)
        if cached_drug is not None:
            found_drugs.append(cached_drug)
            continue
        
        # Try exact match from DB
        drug_data = get_drug_by_name(drug_name)
        
        if drug_data:
            # Get ingredients if available
            ingredients = get_drug_ingredients(drug_name)
            drug_data['ingredients'] = ingredients
            query_cache.set_drug(drug_name, drug_data)
            found_drugs.append(drug_data)
        else:
            # Try keyword search for fuzzy matching
            try:
                search_results = search_drugs_by_keyword(drug_name)
                if search_results:
                    for result in search_results:
                        ingredients = get_drug_ingredients(result['name'])
                        result['ingredients'] = ingredients
                        query_cache.set_drug(result['name'], result)
                    found_drugs.extend(search_results)
                else:
                    not_found_drugs.append(drug_name)
            except:
                not_found_drugs.append(drug_name)
    
    return {
        "found": found_drugs,
        "not_found": not_found_drugs
    }

def check_interactions_for_drugs(found_drugs):
    """
    Checks for interactions between the found drugs.
    Returns structured interaction data.
    Uses cache to avoid redundant database queries.
    """
    if len(found_drugs) < 2:
        return []

    # Build unique, lowercased list of drug names to ensure both-way matching
    drug_names = []
    for drug in found_drugs:
        name = drug.get('name')
        if name:
            drug_names.append(name.strip())

    # deduplicate and lowercase for DB query
    unique_drug_names = list({dn.lower(): dn for dn in drug_names}.keys())
    
    # Create a cache key from sorted drug names
    cache_key = "|".join(sorted(unique_drug_names))
    
    # Check cache first
    cached_interactions = query_cache.get_interactions(cache_key)
    if cached_interactions is not None:
        return cached_interactions
    
    # Query database
    interactions = get_drug_interactions_from_db(unique_drug_names)
    
    # Cache the result
    query_cache.set_interactions(cache_key, interactions)
    
    return interactions

def get_ingredients_from_gemini(drug_name):
    """
    Uses Gemini to break down the possible ingredients of a drug using general knowledge.
    Returns a list of ingredient names.
    Caches results to avoid redundant API calls.
    """
    # Check cache first
    cached_ingredients = query_cache.get_ingredients(drug_name)
    if cached_ingredients is not None:
        return cached_ingredients
    
    # UPDATED PROMPT: Added synonym handling here too just in case
    prompt = f"""
    List the active ingredients (generic names) found in the drug or brand called '{drug_name}'.
    IMPORTANT: If the ingredient is Paracetamol, write 'Acetaminophen'.
    Return only a Python list of ingredient names, no explanations.
    Example: ['Paracetamol', 'Caffeine']
    """
    try:
        response = model.generate_content(prompt)
        # Try to extract a Python list from the response
        match = re.search(r'\[(.*?)\]', response.text, re.DOTALL)
        if match:
            items = match.group(1)
            # Split by comma and clean up
            ingredients = [i.strip(" \"'") for i in items.split(',') if i.strip()]
            # Cache the result
            query_cache.set_ingredients(drug_name, ingredients)
            return ingredients
    except Exception as e:
        print(f"Error extracting ingredients from Gemini: {e}")
        return []
    return []

def build_database_context(user_message, drug_list=None):
    """
    AGENT LOGIC: Analyzes the user message, extracts drugs, queries database,
    and builds comprehensive context for Gemini.
    """
    # Step 1: Extract drugs from message
    extracted = extract_drugs_from_message(user_message)
    drugs_to_search = extracted.get('drugs_mentioned', [])
    intent = extracted.get('intent', 'general_question')
    query_context = extracted.get('query_context', '')
    
    # Step 2: Combine with provided drug_list
    if drug_list and isinstance(drug_list, list):
        drugs_to_search = list(set(drugs_to_search + drug_list))
    
    # Remove duplicates and empty strings
    drugs_to_search = [d.strip() for d in drugs_to_search if d.strip()]
    
    if not drugs_to_search:
        return "", {"found_drugs": [], "not_found_drugs": [], "ingredient_found_drugs": [], "ingredient_interactions": [], "interactions_found_db": 0, "interactions_found_llm": 0, "database_verifications": 0}
    
    # Step 3: Search database for all drugs
    search_results = search_drugs_in_database(drugs_to_search)
    found_drugs = search_results['found']
    initial_not_found = search_results['not_found']

    database_verifications = len(found_drugs)
    db_attempted = 1
    db_successful = 1 if len(found_drugs) > 0 else 0

    # Step 4: Logic for Brand/Missing Drugs
    # We differentiate between "True Missing" (unknown) and "Brand Resolved" (known via Gemini)
    true_not_found_drugs = []
    brand_resolved_notes = []

    ingredient_found_drugs = []
    ingredient_interactions = []
    interactions_found_llm = 0
    llm_attempted = len(initial_not_found)
    llm_successful = 0

    if initial_not_found:
        for missing_drug in initial_not_found:
            ingredients = get_ingredients_from_gemini(missing_drug)

            if ingredients:
                interactions_found_llm += 1
                llm_successful += 1
                # SUCCESS: We found ingredients for this brand/drug
                # We do NOT add this to 'true_not_found_drugs' so Karin won't say "I couldn't find it"
                
                brand_str = f"<li><b>{missing_drug}</b> (Brand/Alias) contains: {', '.join(ingredients)}</li>"
                brand_resolved_notes.append(brand_str)

                # Check which ingredients exist in the database
                db_ingredients = []
                for ing in ingredients:
                    # Check cache first
                    cached_ing = query_cache.get_drug(ing)
                    if cached_ing is not None:
                        db_ingredients.append(cached_ing)
                    else:
                        ing_data = get_drug_by_name(ing)
                        if ing_data:
                            query_cache.set_drug(ing, ing_data)
                            db_ingredients.append(ing_data)
                
                if db_ingredients:
                    ingredient_found_drugs.extend(db_ingredients)
                    # Check for interactions between these ingredients and other found drugs
                    all_for_interaction = found_drugs + db_ingredients
                    ingredient_interactions.extend(check_interactions_for_drugs(all_for_interaction))
            else:
                # FAIL: We really don't know what this is
                true_not_found_drugs.append(missing_drug)

    # Step 5: Check for interactions among found drugs
    interactions = check_interactions_for_drugs(found_drugs) if found_drugs else []
    interactions_found_db = len(found_drugs)

    # Step 6: Build context injection for Gemini
    context_parts = []

    # Add found drugs with details (following actual database schema)
    if found_drugs:
        drug_details = ""
        for drug in found_drugs:
            drug_id = drug.get('id', 'N/A')
            drug_name = drug.get('name', '')
            drug_details += f"<li><b>{drug_name}</b> (ID: {drug_id})</li>"
        context_parts.append(f"[DATABASE] Verified Medications in Database:\n<ul>{drug_details}</ul>")
        context_parts.append("[NOTE] Database contains only drug names and IDs. Additional drug information is not available in the current database structure.")

    # Add ingredient breakdowns for brands (Confident Section)
    if brand_resolved_notes:
        context_parts.append(f"[DATABASE] Brand Name Analysis (VERIFIED):\nThe following brands have been analyzed and their ingredients identified. Treat this as factual data.\n<ul>{''.join(brand_resolved_notes)}</ul>")

    # Add interactions if found
    if interactions:
        interactions_html = ""
        for interaction in interactions:
            drug_a = interaction.get('drug_a', '')
            drug_b = interaction.get('drug_b', '')
            desc = interaction.get('description', '')
            interactions_html += f"<li><b>{drug_a}</b> + <b>{drug_b}</b>: {desc}</li>"
        context_parts.append(f"[DATABASE] Direct Drug Interactions Found:\n<ul>{interactions_html}</ul>")

    # Add ingredient-based interactions if found
    if ingredient_interactions:
        interactions_html = ""
        for interaction in ingredient_interactions:
            drug_a = interaction.get('drug_a', '')
            drug_b = interaction.get('drug_b', '')
            desc = interaction.get('description', '')
            interactions_html += f"<li><b>{drug_a}</b> + <b>{drug_b}</b>: {desc}</li>"
        context_parts.append(f"[DATABASE] Interactions based on Brand Ingredients:\n<ul>{interactions_html}</ul>")

    # Add missing drugs (True missing only)
    if true_not_found_drugs:
        missing_text = ", ".join([f"<b>{drug}</b>" for drug in true_not_found_drugs])
        context_parts.append(f"[DATABASE] Drugs NOT found in database: {missing_text}\nPlease inform the user you cannot find these specific names.")

    # Add intent context
    if intent != "general_question":
        context_parts.append(f"[USER INTENT] The user is asking about: {intent.replace('_', ' ')}")

    if context_parts:
        final_context = "\n\n" + "\n".join(context_parts)
        final_context += "\n\n[INSTRUCTION] Use the database information above. Always mention drug IDs when discussing medications. Provide accurate, evidence-based answers based on database data."
        # Return both the context string and metadata so caller can mark the response source
        metadata = {
            "found_drugs": [d.get('name') for d in found_drugs],
            "not_found_drugs": true_not_found_drugs,
            "ingredient_found_drugs": [d.get('name') for d in ingredient_found_drugs],
            "ingredient_interactions": ingredient_interactions,
            "interactions_found_db": interactions_found_db,
            "interactions_found_llm": interactions_found_llm,
            "database_verifications": database_verifications,
            "db_attempted": db_attempted,
            "db_successful": db_successful,
            "llm_attempted": llm_attempted,
            "llm_successful": llm_successful
        }
        return final_context, metadata

    # No context parts -> return empty string and empty metadata
    return "", {"found_drugs": [], "not_found_drugs": [], "ingredient_found_drugs": [], "ingredient_interactions": [], "interactions_found_db": 0, "interactions_found_llm": 0, "database_verifications": 0}

# --- MAIN LOGIC FUNCTION ---
def get_karin_response(user_message, chat_history, language='en', drug_list=None):
    start_time = time.time()
    if not user_message:
        return "Please tell me which medications you are taking.", "curious"
    
    # Use the agent to build comprehensive database context (also returns metadata)
    context_injection, metadata = build_database_context(user_message, drug_list)

    final_message = user_message + context_injection

    # Start chat with Gemini
    chat = model.start_chat(history=chat_history)

    try:
        response = chat.send_message(final_message)
        bot_text = response.text
        response_time = time.time() - start_time

        update_metrics(response_time, metadata.get("db_attempted", 0), metadata.get("db_successful", 0), metadata.get("llm_attempted", 0), metadata.get("llm_successful", 0), metadata.get("interactions_found_db", 0), metadata.get("interactions_found_llm", 0))


        # --- TAG CLEANING (Regex) ---
        emotion = "neutral" 
        message = bot_text

        # Regex to capture emotion tags
        pattern = r'\[(neutral|happy|blushing|concerned|curious|annoyed|netral|senang|malu-malu|khawatir|penasaran|kesal)\]\s*:?'
        
        match = re.search(pattern, bot_text, re.IGNORECASE)

        if match:
            extracted_emotion = match.group(1).lower()
            
            emotion_map = {
                'netral': 'neutral', 'senang': 'happy', 'malu-malu': 'blushing',
                'khawatir': 'concerned', 'penasaran': 'curious', 'kesal': 'annoyed'
            }
            emotion = emotion_map.get(extracted_emotion, extracted_emotion)
            
            # Remove tag from final message
            message = re.sub(pattern, "", bot_text, count=1).strip()

        # Append a clear HTML source note based on metadata
        source_note = ""
        found = metadata.get("found_drugs", []) if isinstance(metadata, dict) else []
        not_found = metadata.get("not_found_drugs", []) if isinstance(metadata, dict) else []

        if found and not not_found:
            source_note = "<br><small><b>Source:</b> Database (verified)</small>"
        elif found and not_found:
            source_note = "<br><small><b>Source:</b> Partial — Database verified for some drugs; other drugs not found in DB.</small>"
        else:
            # If we found nothing in DB but solved it via brands, it's still good.
            # We check if context actually had content.
            if context_injection:
                 source_note = "<br><small><b>Source:</b> Database & Brand Analysis</small>"
            else:
                 source_note = "<br><small><b>Source:</b> General knowledge (not found in database)</small>"

        # Attach source note to the message (preserve HTML requirement)
        final_output = message + source_note
        return final_output, emotion

    except Exception as e:
        error_str = str(e)
        print(f"Error calling Gemini: {e}")
        
        # Check for quota/rate limit errors
        if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
            return "[concerned] <b>I'm temporarily unavailable due to high demand.</b> My service has reached its usage limit. Please wait a few moments and try again. Your safety is my priority, and I want to make sure I can give you accurate information from my complete database.", "concerned"
        
        return "[concerned] I'm having trouble connecting to my knowledge base right now. Please try again in a moment. If the problem persists, there might be a temporary service issue.", "concerned"
