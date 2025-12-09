#!/usr/bin/env python3
"""Check available Gemini models"""

import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

print("Available Gemini models:")
for model in genai.list_models():
    print(f"  - {model.name}")
    if hasattr(model, 'supported_generation_methods'):
        print(f"    Methods: {model.supported_generation_methods}")
