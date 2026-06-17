from flask import Flask, request, jsonify, render_template
import pickle
import numpy as np
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, 'model', 'model.pkl')

with open(model_path, 'rb') as f:
    model = pickle.load(f)

print("✅ Model loaded!")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Simple in-memory cache: { "crop_lang": "guide text" }
# Restart hone par clear ho jata hai — production mein Redis use kar sakte ho
GUIDE_CACHE = {}

LANG_NAMES = {
    "en": "English", "hi": "Hindi", "or": "Odia", "mr": "Marathi", "bn": "Bengali",
    "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "gu": "Gujarati", "pa": "Punjabi",
    "ml": "Malayalam", "de": "German", "it": "Italian", "ja": "Japanese", "zh": "Chinese",
    "ru": "Russian", "fr": "French", "es": "Spanish", "ar": "Arabic", "pt": "Portuguese",
    "ko": "Korean"
}


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json(force=True, silent=True)
    print("Data received:", data)

    if not data:
        return jsonify({'error': 'No data received'}), 400

    try:
        features = np.array([[
            float(data['nitrogen']),
            float(data['phosphorus']),
            float(data['potassium']),
            float(data['temperature']),
            float(data['humidity']),
            float(data['pH']),
            float(data['rainfall'])
        ]])

        crop = model.predict(features)[0]
        return jsonify({'crop': crop})

    except KeyError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/crop-guide', methods=['POST'])
def crop_guide():
    """
    Groq AI se crop ki growing guide laata hai — user ki language mein.
    Cache karta hai taaki same crop+language dobara API call na kare.
    """
    data = request.get_json(force=True, silent=True) or {}
    crop = (data.get('crop') or '').strip()
    lang_code = (data.get('lang') or 'en').strip()

    if not crop:
        return jsonify({'error': 'crop name required'}), 400

    if not GROQ_API_KEY:
        return jsonify({'error': 'GROQ_API_KEY not configured on server'}), 500

    cache_key = f"{crop.lower()}_{lang_code}"
    if cache_key in GUIDE_CACHE:
        return jsonify({'guide': GUIDE_CACHE[cache_key], 'cached': True})

    lang_name = LANG_NAMES.get(lang_code, "English")

    prompt = f"""You are an agricultural expert helping a farmer. Write a practical growing guide for the crop "{crop}" in {lang_name} language.

Respond ONLY with valid JSON (no markdown, no preamble) in this exact structure:
{{
  "season": "best planting season/months",
  "soil": "ideal soil type and pH range",
  "water": "irrigation needs and frequency",
  "fertilizer": "key nutrients and timing",
  "pests": "common pests/diseases and basic prevention",
  "harvest": "harvest timing and signs of readiness",
  "tip": "one practical actionable tip for small farmers"
}}

Keep each field to 1-2 short sentences. Write everything in {lang_name}, including all field values. Respond with ONLY the JSON object, nothing else."""

    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 600,
                "response_format": {"type": "json_object"}
            },
            timeout=20
        )
        resp.raise_for_status()
        result = resp.json()
        guide_text = result["choices"][0]["message"]["content"]

        GUIDE_CACHE[cache_key] = guide_text
        return jsonify({'guide': guide_text, 'cached': False})

    except requests.exceptions.Timeout:
        return jsonify({'error': 'AI service timeout, try again'}), 504
    except requests.exceptions.RequestException as e:
        print("Groq API error:", e)
        return jsonify({'error': 'AI service unavailable'}), 502
    except (KeyError, IndexError) as e:
        print("Groq response parse error:", e)
        return jsonify({'error': 'Could not parse AI response'}), 502


if __name__ == '__main__':
    app.run(debug=True)
