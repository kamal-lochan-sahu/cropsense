# CropSense

AI-assisted crop recommendation for farmers. Enter soil nutrients (N, P, K),
pH and local climate, and get the best-suited crop plus a growing guide in your
own language.

**Live demo:** https://cropsense-39bz.onrender.com

## Features

- Crop recommendation from 7 inputs (N, P, K, temperature, humidity, pH, rainfall), 22 crops
- Growing guides (season, soil, water, fertilizer, pests, harvest, tip) in 20+ languages
- Multilingual UI with automatic language detection and RTL support (Arabic)
- Installable PWA shell with an offline banner
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
pip install -r requirements.txt
cp .env.example .env        # then add your GROQ_API_KEY
python app.py               # http://127.0.0.1:5000
~~~

To retrain the model: `python train_model.py`

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | For growing guides | Free key from https://console.groq.com |
| `GROQ_MODEL` | No | Defaults to `openai/gpt-oss-120b` |

## Project structure

~~~text
cropsense/
├── app.py              Flask app (routes, model loading, guide endpoint)
├── train_model.py      Model training script
├── model/              Dataset and trained model
├── static/             CSS, JS, PWA manifest, service worker, icons
├── templates/          HTML templates
├── requirements.txt
└── Procfile
~~~

## Deployment

Deployed on Render with `gunicorn app:app`. Set `GROQ_API_KEY` as an environment
variable in the Render dashboard.

## Roadmap

- [ ] Input validation and hardened API responses
- [ ] Automated tests and CI
- [ ] Curated, reviewed growing guides (no runtime LLM dependency)
- [ ] Top-3 recommendations with confidence and "why this crop"
- [ ] Weather auto-fill, fertilizer advice, offline predictions
- [ ] Working soil-report reader and real sensor integration

## License

MIT, see [LICENSE](LICENSE).

## Author

Kamal Lochan Sahu, [@kamal-lochan-sahu](https://github.com/kamal-lochan-sahu)
