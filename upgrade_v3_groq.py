#!/usr/bin/env python3
"""
CropSense v3 — Groq AI Crop Guide + Multi-Mode Input
======================================================
Kya karta hai yeh script:
  1. app.py upgrade — naya /crop-guide route (Groq API call + caching)
  2. .env.example — GROQ_API_KEY ke liye template
  3. requirements.txt — python-dotenv add
  4. templates/index.html — 3-mode input tabs (Manual / Soil Report / Sensor Demo)
  5. static/script.js — naya learn panel jo Groq se live guide laata hai
  6. static/style.css — naye styles (tabs, loading states, AI guide card)

Run karo:
  cd ~/projects/cropsense
  python3 upgrade_v3_groq.py
"""

import os
from pathlib import Path

BASE     = Path(__file__).parent
STATIC   = BASE / "static"
TEMPLATE = BASE / "templates"

# ══════════════════════════════════════════════════════════════════════════════
# 1.  APP.PY  — naya /crop-guide route add karna hai (existing code preserve karke)
# ══════════════════════════════════════════════════════════════════════════════
NEW_APP_PY = '''from flask import Flask, request, jsonify, render_template
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
'''

# ══════════════════════════════════════════════════════════════════════════════
# 2.  .env.example
# ══════════════════════════════════════════════════════════════════════════════
ENV_EXAMPLE = """# Groq API key — console.groq.com se free mein milti hai
# 1. console.groq.com pe jao
# 2. Google/GitHub se sign up karo (no credit card)
# 3. Left sidebar "API Keys" -> "Create API Key"
# 4. Yahan paste karo
GROQ_API_KEY=your_groq_api_key_here
"""

# ══════════════════════════════════════════════════════════════════════════════
# 3.  Naya SCRIPT.JS extension — Groq-based learn panel + 3-mode input
# ══════════════════════════════════════════════════════════════════════════════
SCRIPT_JS_ADDITION = r"""

/* ══════════════════════════════════════════════════════════════════════
   GROQ AI CROP GUIDE  (replaces static CROP_INFO lookup)
   ══════════════════════════════════════════════════════════════════════ */

const GUIDE_LABELS = {
  en: {season:"Season", soil:"Soil", water:"Water", fertilizer:"Fertilizer", pests:"Pests", harvest:"Harvest", tip:"Tip", loading:"Generating your growing guide...", error:"Could not load guide. Try again."},
  hi: {season:"मौसम", soil:"मिट्टी", water:"पानी", fertilizer:"खाद", pests:"कीट", harvest:"कटाई", tip:"सुझाव", loading:"गाइड तैयार हो रही है...", error:"गाइड लोड नहीं हुई। फिर कोशिश करें।"},
  or: {season:"ମୌସୁମ", soil:"ମାଟି", water:"ପାଣି", fertilizer:"ଖତ", pests:"କୀଟ", harvest:"ଅମଳ", tip:"ପରାମର୍ଶ", loading:"ଗାଇଡ ତିଆରି ହେଉଛି...", error:"ଗାଇଡ ଲୋଡ ହେଲା ନାହିଁ।"},
};
function getGuideLabels(lang) { return GUIDE_LABELS[lang] || GUIDE_LABELS.en; }

async function showLearnPanel(crop) {
  const t = TRANSLATIONS[currentLang] || TRANSLATIONS.en;
  const gl = getGuideLabels(currentLang);
  const panel = document.getElementById('learn-panel');

  panel.innerHTML = `
    <div class="learn-header">
      <div>
        <h2>${t.learn_title}: ${crop}</h2>
      </div>
      <button class="close-btn" onclick="document.getElementById('learn-panel').style.display='none'">✕</button>
    </div>
    <div class="ai-loading">
      <div class="spinner"></div>
      <span>${gl.loading}</span>
    </div>
  `;
  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  try {
    const res = await fetch('/crop-guide', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ crop: crop, lang: currentLang })
    });
    const data = await res.json();

    if (!res.ok || data.error) throw new Error(data.error || 'failed');

    const guide = JSON.parse(data.guide);
    renderGuide(crop, guide, gl, t);

  } catch (err) {
    panel.innerHTML = `
      <div class="learn-header">
        <h2>${t.learn_title}: ${crop}</h2>
        <button class="close-btn" onclick="document.getElementById('learn-panel').style.display='none'">✕</button>
      </div>
      <div class="ai-error">⚠ ${gl.error}</div>
      <div class="learn-links">
        <a href="https://www.google.com/search?q=how+to+grow+${encodeURIComponent(crop)}+farming" target="_blank" rel="noopener">🔍 Google Guide</a>
        <a href="https://www.youtube.com/results?search_query=how+to+grow+${encodeURIComponent(crop)}" target="_blank" rel="noopener">▶ YouTube Videos</a>
      </div>
    `;
  }
}

function renderGuide(crop, guide, gl, t) {
  const panel = document.getElementById('learn-panel');
  const rows = [
    ['season', '🗓️'], ['soil', '🌱'], ['water', '💧'],
    ['fertilizer', '🧪'], ['pests', '🐛'], ['harvest', '🌾']
  ];

  let rowsHtml = rows.map(([key, icon]) => {
    if (!guide[key]) return '';
    return `<div class="guide-row">
      <span class="guide-icon">${icon}</span>
      <div class="guide-row-text">
        <strong>${gl[key]}</strong>
        <p>${guide[key]}</p>
      </div>
    </div>`;
  }).join('');

  panel.innerHTML = `
    <div class="learn-header">
      <h2>${t.learn_title}: ${crop}</h2>
      <button class="close-btn" onclick="document.getElementById('learn-panel').style.display='none'">✕</button>
    </div>
    <div class="guide-grid">${rowsHtml}</div>
    ${guide.tip ? `<div class="learn-tip">💡 <strong>${gl.tip}:</strong> ${guide.tip}</div>` : ''}
    <div class="ai-credit">✨ AI-generated guide</div>
  `;
}

/* ══════════════════════════════════════════════════════════════════════
   3-MODE INPUT  (Manual / Soil Report / Sensor Demo)
   ══════════════════════════════════════════════════════════════════════ */

function setInputMode(mode) {
  document.querySelectorAll('.mode-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('mode-' + mode).classList.add('active');

  document.getElementById('mode-panel-manual').style.display = mode === 'manual' ? 'block' : 'none';
  document.getElementById('mode-panel-report').style.display = mode === 'report' ? 'block' : 'none';
  document.getElementById('mode-panel-sensor').style.display = mode === 'sensor' ? 'block' : 'none';
}

/* Soil report — basic client-side parse hint (full OCR is a future upgrade) */
document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('soil-report-file');
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const fileName = e.target.files[0]?.name || '';
      const label = document.getElementById('report-filename');
      if (label) label.textContent = fileName;
      const note = document.getElementById('report-note');
      if (note) note.style.display = fileName ? 'block' : 'none';
    });
  }
});

/* Sensor demo — simulated live values, cycles every 2s to feel "live" */
let sensorInterval = null;
function startSensorDemo() {
  const fields = ['nitrogen','phosphorus','potassium','temperature','humidity','pH','rainfall'];
  const ranges = {
    nitrogen:[20,100], phosphorus:[15,80], potassium:[20,90],
    temperature:[18,35], humidity:[40,90], pH:[5.5,7.5], rainfall:[50,250]
  };
  const display = document.getElementById('sensor-readout');
  if (!display) return;

  if (sensorInterval) { clearInterval(sensorInterval); sensorInterval = null; }

  function tick() {
    const vals = {};
    fields.forEach(f => {
      const [lo, hi] = ranges[f];
      const v = (Math.random() * (hi - lo) + lo);
      vals[f] = f === 'pH' ? v.toFixed(1) : Math.round(v);
    });
    display.innerHTML = fields.map(f =>
      `<div class="sensor-cell"><span class="sensor-label">${f}</span><span class="sensor-value">${vals[f]}</span></div>`
    ).join('');
    display.dataset.values = JSON.stringify(vals);
  }
  tick();
  sensorInterval = setInterval(tick, 2000);
}

function useSensorReading() {
  const display = document.getElementById('sensor-readout');
  if (!display || !display.dataset.values) return;
  const vals = JSON.parse(display.dataset.values);
  if (sensorInterval) { clearInterval(sensorInterval); sensorInterval = null; }

  Object.keys(vals).forEach(key => {
    const el = document.getElementById(key);
    if (el) el.value = vals[key];
  });
  setInputMode('manual');
  document.getElementById('cropForm').scrollIntoView({ behavior: 'smooth' });
}
"""

# ══════════════════════════════════════════════════════════════════════════════
# 4.  CSS additions
# ══════════════════════════════════════════════════════════════════════════════
STYLE_CSS_ADDITION = """

/* ══════════ Mode tabs ══════════ */
.mode-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 18px;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0;
}
.mode-tab {
  flex: 1;
  width: auto;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  padding: 10px 8px;
  font-size: .85rem;
  font-weight: 600;
  color: #888;
  cursor: pointer;
  transition: all .2s;
}
.mode-tab.active { color: #2d6a4f; border-bottom-color: #2d6a4f; }
.mode-tab:hover  { color: #1b4332; }

.mode-panel { display: none; }

/* Soil report upload */
.report-upload {
  border: 2px dashed #b7e4c7;
  border-radius: 10px;
  padding: 28px 16px;
  text-align: center;
  background: #f7fdf9;
  margin-bottom: 16px;
}
.report-upload input[type="file"] { display: none; }
.report-upload label {
  display: inline-block;
  padding: 10px 20px;
  background: #2d6a4f;
  color: #fff;
  border-radius: 6px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  width: auto;
}
#report-filename { display: block; margin-top: 10px; font-size: .82rem; color: #555; }
#report-note {
  display: none;
  margin-top: 14px;
  padding: 10px 14px;
  background: #fff3cd;
  border-left: 3px solid #ffc107;
  border-radius: 6px;
  font-size: .82rem;
  color: #7a5c00;
  text-align: left;
}

/* Sensor demo */
.sensor-box {
  background: #f7fdf9;
  border: 1.5px solid #b7e4c7;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}
.sensor-note {
  font-size: .78rem;
  color: #888;
  margin-bottom: 12px;
  text-align: center;
}
#sensor-readout {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 14px;
  min-height: 40px;
}
.sensor-cell {
  display: flex;
  justify-content: space-between;
  background: #fff;
  border: 1px solid #d8f3dc;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: .82rem;
}
.sensor-label { color: #888; text-transform: capitalize; }
.sensor-value { font-weight: 700; color: #2d6a4f; }
.sensor-btn-row { display: flex; gap: 8px; }
.sensor-btn-row button {
  flex: 1;
  width: auto;
  padding: 10px;
  font-size: .85rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-weight: 600;
}
.btn-start { background: #2d6a4f; color: #fff; }
.btn-start:hover { background: #1b4332; }
.btn-use   { background: #95d5b2; color: #1b4332; }
.btn-use:hover { background: #74c69d; }
.sensor-disclaimer {
  font-size: .72rem;
  color: #aaa;
  text-align: center;
  margin-top: 10px;
}

/* ══════════ AI guide panel ══════════ */
.ai-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px;
  justify-content: center;
  color: #2d6a4f;
  font-size: .9rem;
}
.spinner {
  width: 20px; height: 20px;
  border: 3px solid #d8f3dc;
  border-top-color: #2d6a4f;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.ai-error {
  padding: 14px;
  background: #fdecea;
  border-left: 3px solid #e74c3c;
  border-radius: 6px;
  font-size: .85rem;
  color: #c0392b;
  margin-bottom: 14px;
}

.guide-grid { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }
.guide-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: #fff;
  border: 1px solid #e8f5e9;
  border-radius: 8px;
  padding: 10px 12px;
}
.guide-icon { font-size: 1.3rem; flex-shrink: 0; }
.guide-row-text strong { display: block; font-size: .82rem; color: #1b4332; margin-bottom: 2px; }
.guide-row-text p { font-size: .85rem; color: #444; line-height: 1.4; }

.ai-credit {
  text-align: center;
  font-size: .72rem;
  color: #95d5b2;
  margin-top: 8px;
}
"""

# ══════════════════════════════════════════════════════════════════════════════
# 5.  INDEX.HTML — 3-mode tabs insert (replace form section)
# ══════════════════════════════════════════════════════════════════════════════
NEW_FORM_SECTION = """    <div class="mode-tabs">
      <button class="mode-tab active" id="mode-manual" onclick="setInputMode('manual')">✍️ Manual</button>
      <button class="mode-tab"        id="mode-report" onclick="setInputMode('report')">📄 Soil Report</button>
      <button class="mode-tab"        id="mode-sensor" onclick="setInputMode('sensor')">📡 Live Sensor</button>
    </div>

    <div id="mode-panel-manual" class="mode-panel" style="display:block">
      <form id="cropForm">
        <input type="number" name="nitrogen"    placeholder="Nitrogen (N)"       id="nitrogen"    required>
        <input type="number" name="phosphorus"  placeholder="Phosphorus (P)"     id="phosphorus"  required>
        <input type="number" name="potassium"   placeholder="Potassium (K)"      id="potassium"   required>
        <input type="number" name="temperature" placeholder="Temperature (°C)"   id="temperature" required>
        <input type="number" name="humidity"    placeholder="Humidity (%)"       id="humidity"    required>
        <input type="number" name="pH"          placeholder="pH Value"           id="pH"          step="0.1" min="0" max="14" required>
        <input type="number" name="rainfall"    placeholder="Rainfall (mm)"      id="rainfall"    required>
        <button type="submit" id="submitBtn">Get Recommendation</button>
      </form>
    </div>

    <div id="mode-panel-report" class="mode-panel">
      <div class="report-upload">
        <label for="soil-report-file">📄 Upload Soil Test Report (PDF/Image)</label>
        <input type="file" id="soil-report-file" accept=".pdf,.jpg,.jpeg,.png">
        <span id="report-filename"></span>
        <div id="report-note">
          🚧 Soil report auto-extraction coming soon. For now, please read the NPK and pH values from your report and enter them manually in the "Manual" tab.
        </div>
      </div>
    </div>

    <div id="mode-panel-sensor" class="mode-panel">
      <div class="sensor-box">
        <p class="sensor-note">📡 Demo mode — simulates live IoT sensor readings. Real hardware integration coming soon.</p>
        <div id="sensor-readout"></div>
        <div class="sensor-btn-row">
          <button class="btn-start" onclick="startSensorDemo()" type="button">▶ Start Live Feed</button>
          <button class="btn-use"   onclick="useSensorReading()" type="button">✓ Use This Reading</button>
        </div>
        <p class="sensor-disclaimer">Connect an ESP32 + soil sensor kit for real data (guide coming soon)</p>
      </div>
    </div>"""

OLD_FORM_SECTION = """    <form id="cropForm">
      <input type="number" name="nitrogen"    placeholder="Nitrogen (N)"       id="nitrogen"    required>
      <input type="number" name="phosphorus"  placeholder="Phosphorus (P)"     id="phosphorus"  required>
      <input type="number" name="potassium"   placeholder="Potassium (K)"      id="potassium"   required>
      <input type="number" name="temperature" placeholder="Temperature (°C)"   id="temperature" required>
      <input type="number" name="humidity"    placeholder="Humidity (%)"       id="humidity"    required>
      <input type="number" name="pH"          placeholder="pH Value"           id="pH"          step="0.1" min="0" max="14" required>
      <input type="number" name="rainfall"    placeholder="Rainfall (mm)"      id="rainfall"    required>
      <button type="submit" id="submitBtn">Get Recommendation</button>
    </form>"""

# ══════════════════════════════════════════════════════════════════════════════
# REQUIREMENTS.TXT addition
# ══════════════════════════════════════════════════════════════════════════════
def update_requirements():
    req_path = BASE / "requirements.txt"
    content = req_path.read_text(encoding="utf-8", errors="ignore") if req_path.exists() else ""
    needed = ["requests", "python-dotenv"]
    added = []
    for pkg in needed:
        if pkg.lower() not in content.lower():
            with open(req_path, "a") as f:
                f.write(f"\n{pkg}\n")
            added.append(pkg)
    if added:
        print(f"✅ requirements.txt — added: {', '.join(added)}")
    else:
        print("ℹ  requirements.txt — all packages already present")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def write(path: Path, content: str, label: str):
    path.write_text(content, encoding="utf-8")
    print(f"✅ Written: {label}")

def backup(path: Path):
    if path.exists():
        backup_path = path.with_suffix(path.suffix + ".bak")
        backup_path.write_text(path.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
        print(f"📦 Backed up: {path.name} → {backup_path.name}")

def main():
    print("\n🌱 CropSense v3 — Groq AI Guide + Multi-Mode Input\n")

    # 1. app.py
    backup(BASE / "app.py")
    write(BASE / "app.py", NEW_APP_PY, "app.py (added /crop-guide route)")

    # 2. .env.example
    write(BASE / ".env.example", ENV_EXAMPLE, ".env.example")

    # 3. script.js — append new functionality
    script_path = STATIC / "script.js"
    if script_path.exists():
        backup(script_path)
        existing = script_path.read_text(encoding="utf-8")
        # Remove old showLearnPanel + CROP_INFO references if present (avoid duplicate function)
        if "function showLearnPanel" in existing:
            print("⚠  Old showLearnPanel found — new version will override it (function redefinition is fine in JS)")
        new_script = existing + SCRIPT_JS_ADDITION
        write(script_path, new_script, "static/script.js (Groq guide + 3-mode input added)")
    else:
        print("⚠  static/script.js not found — run the v2 upgrade script first!")

    # 4. style.css — append new styles
    style_path = STATIC / "style.css"
    if style_path.exists():
        backup(style_path)
        existing = style_path.read_text(encoding="utf-8")
        new_style = existing + STYLE_CSS_ADDITION
        write(style_path, new_style, "static/style.css (mode tabs + AI guide styles added)")
    else:
        print("⚠  static/style.css not found — run the v2 upgrade script first!")

    # 5. index.html — replace form section with mode tabs
    html_path = TEMPLATE / "index.html"
    if html_path.exists():
        backup(html_path)
        existing = html_path.read_text(encoding="utf-8")
        if OLD_FORM_SECTION in existing:
            new_html = existing.replace(OLD_FORM_SECTION, NEW_FORM_SECTION)
            write(html_path, new_html, "templates/index.html (3-mode tabs added)")
        else:
            print("⚠  Could not find exact form section to replace in index.html.")
            print("   Your index.html may have been modified manually.")
            print("   Manual fix needed — see MANUAL_PATCH.html in this folder.")
            write(BASE / "MANUAL_PATCH.html", NEW_FORM_SECTION, "MANUAL_PATCH.html (paste this in manually)")
    else:
        print("⚠  templates/index.html not found!")

    # 6. requirements.txt
    update_requirements()

    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  CropSense v3 Upgrade Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS (important!):

1. Groq API key lo:
   → console.groq.com pe jao
   → Sign up (Google/GitHub, no card needed)
   → API Keys → Create API Key → copy karo

2. .env file banao (ye git mein push NAHI hoga):
   cp .env.example .env
   nano .env    (ya apna editor — GROQ_API_KEY=tumhari_key_yaha)

3. .gitignore mein .env add karo (agar already nahi hai):
   echo ".env" >> .gitignore

4. Install karo nayi dependency:
   pip install -r requirements.txt

5. Test karo locally:
   python3 app.py

6. Render pe deploy karne se pehle:
   → Render dashboard → apni service → Environment
   → Add Environment Variable: GROQ_API_KEY = tumhari_key
   (Render pe .env file nahi jaati, environment variable set karna padta hai)

7. Git push:
   git add -A
   git commit -m "feat: Groq AI crop guide + 3-mode input (manual/report/sensor)"
   git push origin main

Backup files (.bak) bana di gayi hain agar kuch galat ho jaye to rollback kar sakte ho.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

if __name__ == "__main__":
    main()
