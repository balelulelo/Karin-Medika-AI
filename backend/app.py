import os
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
from core_logic import get_yunita_response, PROMPTS

# Muat environment variables dari file .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Endpoint untuk chat teks (tidak berubah)
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    history_from_frontend = data.get('history', []) 
    language = data.get('language', 'en')
    user_name = data.get('userName', 'User')

    if not user_message.strip():
        if language == 'id':
            user_message = "..."
        else:
            user_message = "..."

    system_prompt_template = PROMPTS[language]
    system_prompt_text = f"Your user's name is {user_name}. {system_prompt_template}"
    
    system_prompt = {'role': 'user', 'parts': [system_prompt_text]}
    full_history = [system_prompt] + history_from_frontend

    message, emotion = get_yunita_response(user_message, full_history, language)
    messages = [m.strip() for m in message.split('||')]
    response = {"messages": messages, "emotion": emotion}
    return jsonify(response)

# --- ENDPOINT BARU UNTUK TEXT-TO-SPEECH ---
@app.route('/generate-audio', methods=['POST'])
def generate_audio():
    # Ambil teks dari request yang dikirim frontend
    data = request.json
    text_to_speak = data.get('text')

    if not text_to_speak:
        return jsonify({"error": "No text provided"}), 400

    # Ambil API Key & Voice ID dari environment variables yang aman
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    payload = {
        "text": text_to_speak,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        # Lakukan panggilan ke API ElevenLabs dari backend
        response = requests.post(tts_url, json=payload, headers=headers, stream=True)
        response.raise_for_status() # Akan error jika status code bukan 2xx

        # Stream audio kembali ke frontend
        return Response(response.iter_content(chunk_size=1024), content_type='audio/mpeg')

    except requests.exceptions.RequestException as e:
        print(f"Error calling ElevenLabs API: {e}")
        return jsonify({"error": "Failed to generate audio"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=8000)