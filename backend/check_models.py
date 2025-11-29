import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- Standard Setup ---
load_dotenv()
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    print("API Key configured. Fetching models...\n")
except KeyError:
    print("ERROR: GOOGLE_API_KEY not found. Please check your .env file.")
    exit()

# --- List Models ---
print("Models available for 'generateContent':")
print("-" * 35)

try:
    for m in genai.list_models():
      # We are checking which models support the 'generateContent' method
      if 'generateContent' in m.supported_generation_methods:
          print(m.name)
except Exception as e:
    print(f"An error occurred while trying to list models: {e}")

print("-" * 35)
