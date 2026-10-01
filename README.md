# CropSense

[![CI](https://github.com/kamal-lochan-sahu/cropsense/actions/workflows/ci.yml/badge.svg)](https://github.com/kamal-lochan-sahu/cropsense/actions/workflows/ci.yml)

AI-assisted crop recommendation for farmers. Enter soil nutrients (N, P, K),
pH and local climate, and get the best-suited crops plus a growing guide in your
own language.

**Live demo:** https://cropsense-39bz.onrender.com

## Features

- Crop recommendation from 7 inputs (N, P, K, temperature, humidity, pH, rainfall), 22 crops
- Top-3 suggestions with confidence bars, and a warning when inputs fall outside the range the model was trained on
- Accessible form: visible labels, decimal input, inline per-field errors, clear error states
- Growing guides (season, soil, water, fertilizer, pests, harvest, tip) in 21 languages
- Multilingual UI with automatic language detection and RTL support (Arabic)
- Installable PWA: root-scope service worker with a versioned cache (no stale files after a deploy), real icons
- Strict Content-Security-Policy; server and LLM text is never parsed as HTML
- Demo-only for now: **Soil Report upload** and **Live Sensor** tabs are placeholders

## Model

Random Forest (100 trees, scikit-learn) trained on the public Crop Recommendation
dataset: 2,200 samples, 22 crops, 100 samples per crop.

| Metric | Result |
| --- | --- |
| Hold-out accuracy (80/20 split, seed 42) | 99.32% |
| 5-fold stratified cross-validation | 99.5% +/- 0.22 |

The dataset is small, clean and perfectly balanced, so real-field accuracy will be
lower. Treat results as a decision aid, not as agronomic advice; confirm with your
local agriculture office.

## Quick start

~~~bash
git clone https://github.com/kamal-lochan-sahu/cropsense.git
cd cropsense
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                 # then add your GROQ_API_KEY
flask --app wsgi run --debug         # http://127.0.0.1:5000
~~~

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | For growing guides | Free key from https://console.groq.com |
| `GROQ_MODEL` | No | Primary model, defaults to `openai/gpt-oss-120b` |
| `GROQ_FALLBACK_MODELS` | No | Comma-separated fallbacks, defaults to `qwen/qwen3.8-27b` |

Groq retires models regularly. If the primary model disappears, the next one in the
chain is used automatically.

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| POST | `/predict` | Crop recommendation |
| POST | `/crop-guide` | Growing guide for a crop in a given language |

`POST /predict`

~~~json
{"nitrogen": 90, "phosphorus": 42, "potassium": 43, "temperature": 20.8,
 "humidity": 82, "pH": 6.5, "rainfall": 202}
~~~

~~~json
{"crop": "rice", "confidence": 0.98,
 "top": [{"crop": "rice", "confidence": 0.98}, {"crop": "jute", "confidence": 0.02},
         {"crop": "pomegranate", "confidence": 0.0}]}
~~~

Invalid input returns `422` with per-field errors. Values that are valid but outside the
training range still return `200` with a `warnings` list.

`POST /crop-guide` takes `{"crop": "rice", "lang": "hi"}` and returns `{"guide": "<json>", "cached": false}`.
Only the 22 known crops and the supported language codes are accepted.

## Project structure

~~~text
cropsense/
├── app/
│   ├── __init__.py        App factory, error handlers, security headers, asset versioning
│   ├── config.py          Environment-based configuration
│   ├── routes.py          HTTP endpoints (/, /predict, /crop-guide, /health, /sw.js)
│   ├── validation.py      Input ranges and validation
│   ├── ml/predictor.py    Model loading and prediction
│   ├── services/guides.py Groq guide generation, fallback chain, cache
│   ├── static/
│   │   ├── css/           Styles
│   │   ├── js/            app.js (logic), translations.js (21 languages)
│   │   ├── icons/         PWA icons, favicon
│   │   ├── img/           Social preview image
│   │   └── manifest.json
│   └── templates/         index.html, sw.js (service worker, rendered with a version hash)
├── data/                  Training dataset
├── models/                Trained model
├── scripts/
│   ├── train_model.py     Reproducible training and metrics
│   └── make_icons.py      Generates icons and the social image
├── tests/                 pytest suite (API, guides, static assets, CSP)
├── wsgi.py                Production entry point
└── requirements*.txt
~~~

## Development

~~~bash
pytest                     # run tests
ruff check . && ruff format --check .
python scripts/train_model.py --out-dir /tmp/model-test   # retrain without touching models/
python scripts/make_icons.py                              # regenerate icons and social image
~~~

CI runs lint, format check and tests on every push and pull request.

## Deployment

Deployed on Render. Build command `pip install -r requirements.txt`, start command
`gunicorn wsgi:app` (`gunicorn app:app` also works). Set `GROQ_API_KEY` as an
environment variable in the Render dashboard.

## Roadmap

- [x] Input validation and hardened API responses
- [x] Automated tests and CI
- [x] Frontend fixes (decimal inputs, labels, error states, service worker scope, icons, top-3 UI)
- [ ] Translate the new UI strings into all 21 languages (missing keys fall back to English)
- [ ] Browser-level tests for the frontend in CI
- [ ] Curated, reviewed growing guides (no runtime LLM dependency)
- [ ] "Why this crop": compare inputs with each crop's ideal ranges
- [ ] Weather auto-fill, fertilizer advice, offline predictions
- [ ] Working soil-report reader and real sensor integration

## License

MIT, see [LICENSE](LICENSE).

## Author

Kamal Lochan Sahu, [@kamal-lochan-sahu](https://github.com/kamal-lochan-sahu)
