# 🌱 CropSense — AI Crop Recommendation System

An AI-powered web application that recommends the best crop to grow based on soil and climate data.

##  Live 
 [https://cropsense-39bz.onrender.com](https://cropsense-39bz.onrender.com)

## 🧠 How It Works
1. User enters soil data — Nitrogen, Phosphorus, Potassium, Temperature, Humidity, pH, Rainfall
2. Flask backend receives the data
3. Random Forest ML model predicts the best crop
4. Result is displayed instantly

## 🛠️ Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| ML Model | Scikit-learn, Random Forest |
| Data | Pandas, NumPy |
| Deployment | Render |

## 📊 Model Performance
- Algorithm: Random Forest Classifier
- Dataset: 2200 soil samples, 22 crop types
- Accuracy: **99.32%**

## 📁 Project Structure
cropsense/
├── app.py
├── train_model.py
├── Procfile
├── requirements.txt
├── model/
│   ├── Crop_recommendation.csv
│   └── model.pkl
├── static/
│   ├── style.css
│   └── script.js
└── templates/
└── index.html
## ⚙️ Run Locally
```bash
git clone https://github.com/kamal-lochan-sahu/cropsense.git
cd cropsense
pip install -r requirements.txt
python train_model.py
python app.py
👨‍💻 Author
Kamal Lochan Sahu
GitHub: @kamal-lochan-sahu
LinkedIn: kamal-lochan-sahu
---