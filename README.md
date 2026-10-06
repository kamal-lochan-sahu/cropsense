# CropSense

[![CI](https://github.com/kamal-lochan-sahu/cropsense/actions/workflows/ci.yml/badge.svg)](https://github.com/kamal-lochan-sahu/cropsense/actions/workflows/ci.yml)

AI-assisted crop recommendation for farmers. Enter soil nutrients (N, P, K),
pH and local climate, and get the best-suited crops plus a growing guide in your
own language.

**Live demo:** https://cropsense-39bz.onrender.com

## Features

- Crop recommendation from 7 inputs (N, P, K, temperature, humidity, pH, rainfall), 22 crops
- Top-3 suggestions with confidence bars, and a warning when inputs fall outside the range the model was trained on
- Soil advice for the recommended crop: N, P, K and pH marked low / good / high against the crop's typical values, with fertilizer hints (computed locally from the training data, no external API)
- Accessible form: visible labels, decimal input, inline per-field errors, clear error states
- Growing guides (season, soil, water, fertilizer, pests, harvest, tip): curated content for every crop, shipped with the app (English now, more languages being added); languages without curated content fall back to AI generation via Groq
- Multilingual UI in 21 languages with RTL support (Arabic): opens in English; the user can choose a language or follow their region (the region lookup only runs after tapping Auto)
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
| `GROQ_API_KEY` | Only for guides in languages without curated content | Free key from https://console.groq.com |
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
         {"crop": "pomegranate", "confidence": 0.0}],
 "advice": {"crop": "rice",
            "items": [{"field": "nitrogen", "status": "ok", "value": 90,
                       "low": 62.9, "median": 80.0, "high": 95.0}, "..."]}}
~~~

`advice` compares nitrogen, phosphorus, potassium and pH with the typical range (10th to 90th
percentile) of the recommended crop in the training data. `status` is `low`, `ok` or `high`.
The ranges live in `models/crop_profiles.json`, built by `scripts/build_crop_profiles.py`.

Invalid input returns `422` with per-field errors. Values that are valid but outside the
training range still return `200` with a `warnings` list.

`POST /crop-guide` takes `{"crop": "rice", "lang": "hi"}` and returns `{"guide": "<json>", "cached": false, "source": "curated"}`. `source` is `curated` for the guides in `app/content/guides/<lang>.json` (no external call, works without an API key) and `ai` for guides generated through Groq.
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
│   ├── ml/advice.py       Soil advice from the crop profiles
│   ├── services/guides.py Curated guides, Groq fallback chain, cache
│   ├── content/guides/    Curated growing guides, one <lang>.json per language
│   ├── static/
│   │   ├── css/           Styles
│   │   ├── js/            app.js (logic), translations.js (21 languages)
│   │   ├── icons/         PWA icons, favicon
│   │   ├── img/           Social preview image
│   │   └── manifest.json
│   └── templates/         index.html, sw.js (service worker, rendered with a version hash)
├── data/                  Training dataset
├── models/                Trained model, crop soil profiles (crop_profiles.json)
├── scripts/
│   ├── train_model.py     Reproducible training and metrics
│   ├── build_crop_profiles.py  Typical N, P, K and pH per crop, from the dataset
│   └── make_icons.py      Generates icons and the social image
├── tests/                 pytest suite (API, guides, static assets, CSP)
│   └── js/                jsdom frontend tests (node --test)
├── wsgi.py                Production entry point
├── package.json           Dev-only: jsdom for the frontend tests (no build step)
└── requirements*.txt
~~~

## Development

~~~bash
pytest                     # backend tests
npm ci && npm test         # frontend tests (jsdom, needs Node 20.19+)
ruff check . && ruff format --check .
python scripts/train_model.py --out-dir /tmp/model-test   # retrain without touching models/
python scripts/build_crop_profiles.py                     # rebuild models/crop_profiles.json (after a dataset change)
python scripts/make_icons.py                              # regenerate icons and social image
~~~

CI runs lint, format check, backend tests and frontend tests on every push and pull request.

## Deployment

Deployed on Render. Build command `pip install -r requirements.txt`, start command
`gunicorn wsgi:app` (`gunicorn app:app` also works). Set `GROQ_API_KEY` as an
environment variable in the Render dashboard.

## Roadmap

- [x] Input validation and hardened API responses
- [x] Automated tests and CI
- [x] Frontend fixes (decimal inputs, labels, error states, service worker scope, icons, top-3 UI)
- [x] Translate the new UI strings into all 21 languages
- [x] Frontend tests (jsdom) in CI
- [ ] Curated, reviewed growing guides (no runtime LLM dependency)
- [ ] "Why this crop": compare inputs with each crop's ideal ranges
- [x] Soil advice: N, P, K and pH checked against the crop's typical ranges (local data, no external API)
- [ ] Offline predictions
- [ ] Working soil-report reader and real sensor integration

## License

MIT, see [LICENSE](LICENSE).

## Author

Kamal Lochan Sahu, [@kamal-lochan-sahu](https://github.com/kamal-lochan-sahu)
