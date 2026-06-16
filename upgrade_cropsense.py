#!/usr/bin/env python3
"""
CropSense v2 Upgrade Script
============================
Kya karta hai yeh script:
  1. manifest,json  →  manifest.json  (comma bug fix)
  2. sw,js          →  sw.js          (comma bug fix)
  3. Naya index.html — i18n + OG tags + language toggle
  4. Naya style.css  — language toggle UI + responsive
  5. Naya script.js  — i18n engine + IP detection + crop learning
  6. og-image.png    — LinkedIn/Twitter preview (1200×630, Pillow se)
  7. requirements.txt — Pillow add (OG image ke liye)

Run karo:
  cd ~/projects/cropsense
  python3 upgrade_cropsense.py
"""

import os
import shutil
from pathlib import Path

# ── Pillow check ──────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_OK = True
except ImportError:
    PILLOW_OK = False
    print("⚠  Pillow nahi mila. OG image skip hogi.")
    print("   Install karo: pip install Pillow")

BASE = Path(__file__).parent          # ~/projects/cropsense
STATIC   = BASE / "static"
TEMPLATE = BASE / "templates"
STATIC.mkdir(exist_ok=True)
TEMPLATE.mkdir(exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# 1.  COMMA BUG FIX
# ══════════════════════════════════════════════════════════════════════════════
def fix_comma_bugs():
    fixes = [
        (STATIC / "manifest,json", STATIC / "manifest.json"),
        (STATIC / "sw,js",         STATIC / "sw.js"),
    ]
    for old, new in fixes:
        if old.exists():
            shutil.move(str(old), str(new))
            print(f"✅ Renamed: {old.name}  →  {new.name}")
        elif new.exists():
            print(f"ℹ  {new.name} already exists — skipping rename")

# ══════════════════════════════════════════════════════════════════════════════
# 2.  MANIFEST.JSON  (updated)
# ══════════════════════════════════════════════════════════════════════════════
MANIFEST = """{
    "name": "CropSense - AI Crop Recommendation",
    "short_name": "CropSense",
    "description": "AI-powered crop recommendation system supporting 20+ languages",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#f0f4f0",
    "theme_color": "#2d6a4f",
    "icons": [
        {
            "src": "/static/icon-192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/static/icon-512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}"""

# ══════════════════════════════════════════════════════════════════════════════
# 3.  SERVICE WORKER  (sw.js)
# ══════════════════════════════════════════════════════════════════════════════
SW_JS = """// CropSense Service Worker v2
const CACHE = 'cropsense-v2';
const ASSETS = ['/', '/static/style.css', '/static/script.js',
                '/static/icon-192.png', '/static/icon-512.png',
                '/static/manifest.json'];

self.addEventListener('install', e =>
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS))));

self.addEventListener('activate', e =>
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))));

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(cached => {
      const net = fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      });
      return cached || net;
    })
  );
});"""

# ══════════════════════════════════════════════════════════════════════════════
# 4.  TRANSLATIONS  (20 languages)
# ══════════════════════════════════════════════════════════════════════════════
# Har language ke liye keys:
#   title, subtitle, nitrogen, phosphorus, potassium, temperature,
#   humidity, ph, rainfall, btn, result_prefix, result_tip,
#   learn_btn, learn_title, offline_msg
#
# Indian (10): hi, or, mr, bn, ta, te, kn, gu, pa, ml
# World  (10): de, it, ja, zh, ru, fr, es, ar, pt, ko

TRANSLATIONS_JS = r"""
const TRANSLATIONS = {
  en: {
    title:"☘ CropSense", subtitle:"AI-powered Crop Recommendation",
    nitrogen:"Nitrogen (N)", phosphorus:"Phosphorus (P)", potassium:"Potassium (K)",
    temperature:"Temperature (°C)", humidity:"Humidity (%)", ph:"pH Value",
    rainfall:"Rainfall (mm)", btn:"Get Recommendation",
    result_prefix:"Recommended Crop:", result_tip:"Tap the crop name to learn how to grow it.",
    learn_btn:"How to Grow →", learn_title:"Growing Guide",
    offline_msg:"You are offline. Predictions need internet.",
    toggle_en:"English", toggle_auto:"Auto", toggle_choose:"Choose Language",
    credits:"Made with ☘ for farmers worldwide"
  },

  /* ── Indian languages ── */
  hi: {
    title:"☘ क्रॉपसेंस", subtitle:"AI-आधारित फसल अनुशंसा प्रणाली",
    nitrogen:"नाइट्रोजन (N)", phosphorus:"फॉस्फोरस (P)", potassium:"पोटेशियम (K)",
    temperature:"तापमान (°C)", humidity:"आर्द्रता (%)", ph:"pH मान",
    rainfall:"वर्षा (mm)", btn:"फसल सुझाव पाएं",
    result_prefix:"अनुशंसित फसल:", result_tip:"फसल का नाम दबाएं — उगाने का तरीका जानें।",
    learn_btn:"उगाना सीखें →", learn_title:"खेती की पूरी जानकारी",
    offline_msg:"आप ऑफ़लाइन हैं। अनुमान के लिए इंटरनेट चाहिए।",
    toggle_en:"English", toggle_auto:"स्वतः", toggle_choose:"भाषा चुनें",
    credits:"☘ किसानों के लिए बनाया गया"
  },
  or: {
    title:"☘ କ୍ରପସେନ୍ସ", subtitle:"AI ଆଧାରିତ ଫସଲ ପରାମର୍ଶ",
    nitrogen:"ନାଇଟ୍ରୋଜେନ (N)", phosphorus:"ଫସଫରସ (P)", potassium:"ପୋଟାସିୟମ (K)",
    temperature:"ତାପମାତ୍ରା (°C)", humidity:"ଆର୍ଦ୍ରତା (%)", ph:"pH ମୂଲ୍ୟ",
    rainfall:"ବର୍ଷା (mm)", btn:"ଫସଲ ପରାମର୍ଶ ପାଆନ୍ତୁ",
    result_prefix:"ପ୍ରସ୍ତାବିତ ଫସଲ:", result_tip:"ଫସଲ ନାମ ଦବାନ୍ତୁ — ଚାଷ ପ଼ଦ୍ଧତି ଜାଣନ୍ତୁ।",
    learn_btn:"ଚାଷ ଶିଖନ୍ତୁ →", learn_title:"ଚାଷ ସଂପୂର୍ଣ ଗାଇଡ",
    offline_msg:"ଆପଣ ଅଫଲାଇନ ଅଛନ୍ତି।",
    toggle_en:"English", toggle_auto:"ସ୍ୱୟଂ", toggle_choose:"ଭାଷା ବାଛନ୍ତୁ",
    credits:"☘ ଚାଷୀଙ୍କ ପାଇଁ ତିଆରି"
  },
  mr: {
    title:"☘ क्रॉपसेन्स", subtitle:"AI-आधारित पीक शिफारस प्रणाली",
    nitrogen:"नायट्रोजन (N)", phosphorus:"फॉस्फरस (P)", potassium:"पोटॅशियम (K)",
    temperature:"तापमान (°C)", humidity:"आर्द्रता (%)", ph:"pH मूल्य",
    rainfall:"पाऊस (mm)", btn:"पीक शिफारस मिळवा",
    result_prefix:"शिफारस केलेले पीक:", result_tip:"पिकाचे नाव दाबा — लागवड कशी करावी ते शिका।",
    learn_btn:"लागवड शिका →", learn_title:"शेती संपूर्ण मार्गदर्शन",
    offline_msg:"तुम्ही ऑफलाइन आहात।",
    toggle_en:"English", toggle_auto:"स्वयं", toggle_choose:"भाषा निवडा",
    credits:"☘ शेतकऱ्यांसाठी बनवले"
  },
  bn: {
    title:"☘ ক্রপসেন্স", subtitle:"AI-চালিত ফসল সুপারিশ ব্যবস্থা",
    nitrogen:"নাইট্রোজেন (N)", phosphorus:"ফসফরাস (P)", potassium:"পটাশিয়াম (K)",
    temperature:"তাপমাত্রা (°C)", humidity:"আর্দ্রতা (%)", ph:"pH মান",
    rainfall:"বৃষ্টিপাত (mm)", btn:"ফসল সুপারিশ পান",
    result_prefix:"প্রস্তাবিত ফসল:", result_tip:"ফসলের নামে চাপুন — চাষের পদ্ধতি জানুন।",
    learn_btn:"চাষ শিখুন →", learn_title:"চাষাবাদ সম্পূর্ণ গাইড",
    offline_msg:"আপনি অফলাইন আছেন।",
    toggle_en:"English", toggle_auto:"স্বয়ং", toggle_choose:"ভাষা বেছে নিন",
    credits:"☘ কৃষকদের জন্য তৈরি"
  },
  ta: {
    title:"☘ கிராப்சென்ஸ்", subtitle:"AI சார்ந்த பயிர் பரிந்துரை",
    nitrogen:"நைட்ரஜன் (N)", phosphorus:"பாஸ்பரஸ் (P)", potassium:"பொட்டாசியம் (K)",
    temperature:"வெப்பநிலை (°C)", humidity:"ஈரப்பதம் (%)", ph:"pH மதிப்பு",
    rainfall:"மழைவீழ்ச்சி (mm)", btn:"பயிர் பரிந்துரை பெறுங்கள்",
    result_prefix:"பரிந்துரைக்கப்பட்ட பயிர்:", result_tip:"பயிரின் பெயரை அழுத்தவும் — வளர்ப்பு முறை அறியுங்கள்।",
    learn_btn:"வளர்ப்பு கற்றுக்கொள்ளுங்கள் →", learn_title:"விவசாய வழிகாட்டி",
    offline_msg:"நீங்கள் ஆஃப்லைனில் உள்ளீர்கள்।",
    toggle_en:"English", toggle_auto:"தானியங்கி", toggle_choose:"மொழி தேர்வு",
    credits:"☘ விவசாயிகளுக்காக உருவாக்கப்பட்டது"
  },
  te: {
    title:"☘ క్రాప్‌సెన్స్", subtitle:"AI ఆధారిత పంట సిఫార్సు",
    nitrogen:"నత్రజని (N)", phosphorus:"భాస్వరం (P)", potassium:"పొటాషియం (K)",
    temperature:"ఉష్ణోగ్రత (°C)", humidity:"తేమ (%)", ph:"pH విలువ",
    rainfall:"వర్షపాతం (mm)", btn:"పంట సిఫార్సు పొందండి",
    result_prefix:"సిఫార్సు చేయబడిన పంట:", result_tip:"పంట పేరు నొక్కండి — సాగు విధానం తెలుసుకోండి।",
    learn_btn:"సాగు నేర్చుకోండి →", learn_title:"వ్యవసాయ మార్గదర్శి",
    offline_msg:"మీరు ఆఫ్‌లైన్‌లో ఉన్నారు।",
    toggle_en:"English", toggle_auto:"స్వయంచాలక", toggle_choose:"భాష ఎంచుకోండి",
    credits:"☘ రైతుల కోసం తయారు చేయబడింది"
  },
  kn: {
    title:"☘ ಕ್ರಾಪ್‌ಸೆನ್ಸ್", subtitle:"AI ಆಧಾರಿತ ಬೆಳೆ ಶಿಫಾರಸು",
    nitrogen:"ಸಾರಜನಕ (N)", phosphorus:"ರಂಜಕ (P)", potassium:"ಪೊಟ್ಯಾಸಿಯಮ್ (K)",
    temperature:"ತಾಪಮಾನ (°C)", humidity:"ಆರ್ದ್ರತೆ (%)", ph:"pH ಮೌಲ್ಯ",
    rainfall:"ಮಳೆ (mm)", btn:"ಬೆಳೆ ಶಿಫಾರಸು ಪಡೆಯಿರಿ",
    result_prefix:"ಶಿಫಾರಸು ಮಾಡಿದ ಬೆಳೆ:", result_tip:"ಬೆಳೆಯ ಹೆಸರನ್ನು ಒತ್ತಿ — ಬೆಳೆಯುವ ವಿಧಾನ ತಿಳಿಯಿರಿ।",
    learn_btn:"ಬೆಳೆಯಲು ಕಲಿಯಿರಿ →", learn_title:"ಕೃಷಿ ಮಾರ್ಗದರ್ಶಿ",
    offline_msg:"ನೀವು ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿದ್ದೀರಿ।",
    toggle_en:"English", toggle_auto:"ಸ್ವಯಂಚಾಲಿತ", toggle_choose:"ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ",
    credits:"☘ ರೈತರಿಗಾಗಿ ತಯಾರಿಸಲಾಗಿದೆ"
  },
  gu: {
    title:"☘ ક્રોપસેન્સ", subtitle:"AI આધારિત પાક ભલામણ",
    nitrogen:"નાઇટ્રોજન (N)", phosphorus:"ફોસ્ફરસ (P)", potassium:"પોટેશિયમ (K)",
    temperature:"તાપમાન (°C)", humidity:"ભેજ (%)", ph:"pH મૂલ્ય",
    rainfall:"વરસાદ (mm)", btn:"પાક ભલામણ મેળવો",
    result_prefix:"ભલામણ કરેલ પાક:", result_tip:"પાકનું નામ દબાવો — ઉગાડવાની રીત જાણો।",
    learn_btn:"ઉગાડવાનું શીખો →", learn_title:"ખેતી સંપૂર્ણ માર્ગદર્શિકા",
    offline_msg:"તમે ઑફ‍લાઇન છો।",
    toggle_en:"English", toggle_auto:"સ્વતઃ", toggle_choose:"ભાષા પસંદ કરો",
    credits:"☘ ખેડૂતો માટે બનાવ્યું"
  },
  pa: {
    title:"☘ ਕ੍ਰੌਪਸੈਂਸ", subtitle:"AI ਅਧਾਰਿਤ ਫ਼ਸਲ ਸਿਫ਼ਾਰਸ਼",
    nitrogen:"ਨਾਈਟ੍ਰੋਜਨ (N)", phosphorus:"ਫਾਸਫੋਰਸ (P)", potassium:"ਪੋਟਾਸ਼ੀਅਮ (K)",
    temperature:"ਤਾਪਮਾਨ (°C)", humidity:"ਨਮੀ (%)", ph:"pH ਮੁੱਲ",
    rainfall:"ਬਾਰਸ਼ (mm)", btn:"ਫ਼ਸਲ ਸਿਫ਼ਾਰਸ਼ ਪਾਓ",
    result_prefix:"ਸਿਫ਼ਾਰਸ਼ ਕੀਤੀ ਫ਼ਸਲ:", result_tip:"ਫ਼ਸਲ ਦਾ ਨਾਮ ਦਬਾਓ — ਉਗਾਉਣ ਦਾ ਤਰੀਕਾ ਜਾਣੋ।",
    learn_btn:"ਉਗਾਉਣਾ ਸਿੱਖੋ →", learn_title:"ਖੇਤੀ ਗਾਈਡ",
    offline_msg:"ਤੁਸੀਂ ਔਫਲਾਈਨ ਹੋ।",
    toggle_en:"English", toggle_auto:"ਆਪਣੇ ਆਪ", toggle_choose:"ਭਾਸ਼ਾ ਚੁਣੋ",
    credits:"☘ ਕਿਸਾਨਾਂ ਲਈ ਬਣਾਇਆ"
  },
  ml: {
    title:"☘ ക്രോപ്‌സെൻസ്", subtitle:"AI അടിസ്ഥാനമായ വിള ശുപാർശ",
    nitrogen:"നൈട്രജൻ (N)", phosphorus:"ഫോസ്ഫറസ് (P)", potassium:"പൊട്ടാസ്യം (K)",
    temperature:"താപനില (°C)", humidity:"ഈർപ്പം (%)", ph:"pH മൂല്യം",
    rainfall:"മഴ (mm)", btn:"വിള ശുപാർശ നേടുക",
    result_prefix:"ശുപാർശ ചെയ്ത വിള:", result_tip:"വിളയുടെ പേരിൽ അമർത്തുക — കൃഷി രീതി അറിയുക।",
    learn_btn:"കൃഷി പഠിക്കൂ →", learn_title:"കൃഷി ഗൈഡ്",
    offline_msg:"നിങ്ങൾ ഓഫ്‌ലൈനിലാണ്।",
    toggle_en:"English", toggle_auto:"സ്വയം", toggle_choose:"ഭാഷ തിരഞ്ഞെടുക്കൂ",
    credits:"☘ കർഷകർക്കായി നിർമ്മിച്ചത്"
  },

  /* ── World languages ── */
  de: {
    title:"☘ CropSense", subtitle:"KI-gestützte Pflanzenempfehlung",
    nitrogen:"Stickstoff (N)", phosphorus:"Phosphor (P)", potassium:"Kalium (K)",
    temperature:"Temperatur (°C)", humidity:"Luftfeuchtigkeit (%)", ph:"pH-Wert",
    rainfall:"Niederschlag (mm)", btn:"Empfehlung erhalten",
    result_prefix:"Empfohlene Pflanze:", result_tip:"Klicken Sie auf den Pflanzennamen — Anbauanleitung ansehen.",
    learn_btn:"Anbau lernen →", learn_title:"Anbauführer",
    offline_msg:"Sie sind offline. Für Vorhersagen ist Internet erforderlich.",
    toggle_en:"Englisch", toggle_auto:"Auto", toggle_choose:"Sprache wählen",
    credits:"☘ Für Landwirte weltweit"
  },
  it: {
    title:"☘ CropSense", subtitle:"Raccomandazione colture basata su AI",
    nitrogen:"Azoto (N)", phosphorus:"Fosforo (P)", potassium:"Potassio (K)",
    temperature:"Temperatura (°C)", humidity:"Umidità (%)", ph:"Valore pH",
    rainfall:"Precipitazioni (mm)", btn:"Ottieni raccomandazione",
    result_prefix:"Coltura raccomandata:", result_tip:"Clicca sul nome della coltura — scopri come coltivarla.",
    learn_btn:"Impara a coltivare →", learn_title:"Guida alla coltivazione",
    offline_msg:"Sei offline. La previsione richiede internet.",
    toggle_en:"Inglese", toggle_auto:"Auto", toggle_choose:"Scegli lingua",
    credits:"☘ Creato per gli agricoltori"
  },
  ja: {
    title:"☘ クロップセンス", subtitle:"AI作物推奨システム",
    nitrogen:"窒素 (N)", phosphorus:"リン (P)", potassium:"カリウム (K)",
    temperature:"気温 (°C)", humidity:"湿度 (%)", ph:"pH値",
    rainfall:"降水量 (mm)", btn:"推奨作物を取得",
    result_prefix:"推奨作物:", result_tip:"作物名をタップして栽培方法を学びましょう。",
    learn_btn:"栽培を学ぶ →", learn_title:"栽培ガイド",
    offline_msg:"オフラインです。予測にはインターネットが必要です。",
    toggle_en:"英語", toggle_auto:"自動", toggle_choose:"言語を選択",
    credits:"☘ 世界中の農家のために"
  },
  zh: {
    title:"☘ 农感", subtitle:"AI驱动的作物推荐系统",
    nitrogen:"氮 (N)", phosphorus:"磷 (P)", potassium:"钾 (K)",
    temperature:"温度 (°C)", humidity:"湿度 (%)", ph:"pH值",
    rainfall:"降雨量 (mm)", btn:"获取推荐",
    result_prefix:"推荐作物:", result_tip:"点击作物名称了解种植方法。",
    learn_btn:"学习种植 →", learn_title:"种植指南",
    offline_msg:"您处于离线状态。预测需要互联网。",
    toggle_en:"英语", toggle_auto:"自动", toggle_choose:"选择语言",
    credits:"☘ 为全球农民而制"
  },
  ru: {
    title:"☘ КропСенс", subtitle:"Рекомендации по культурам на основе ИИ",
    nitrogen:"Азот (N)", phosphorus:"Фосфор (P)", potassium:"Калий (K)",
    temperature:"Температура (°C)", humidity:"Влажность (%)", ph:"Значение pH",
    rainfall:"Осадки (мм)", btn:"Получить рекомендацию",
    result_prefix:"Рекомендуемая культура:", result_tip:"Нажмите на название культуры — узнайте как выращивать.",
    learn_btn:"Учиться выращивать →", learn_title:"Руководство по выращиванию",
    offline_msg:"Вы офлайн. Для прогноза нужен интернет.",
    toggle_en:"Английский", toggle_auto:"Авто", toggle_choose:"Выберите язык",
    credits:"☘ Создано для фермеров мира"
  },
  fr: {
    title:"☘ CropSense", subtitle:"Recommandation de cultures basée sur l'IA",
    nitrogen:"Azote (N)", phosphorus:"Phosphore (P)", potassium:"Potassium (K)",
    temperature:"Température (°C)", humidity:"Humidité (%)", ph:"Valeur pH",
    rainfall:"Précipitations (mm)", btn:"Obtenir une recommandation",
    result_prefix:"Culture recommandée:", result_tip:"Cliquez sur le nom de la culture — apprenez comment la cultiver.",
    learn_btn:"Apprendre à cultiver →", learn_title:"Guide de culture",
    offline_msg:"Vous êtes hors ligne. La prédiction nécessite Internet.",
    toggle_en:"Anglais", toggle_auto:"Auto", toggle_choose:"Choisir la langue",
    credits:"☘ Créé pour les agriculteurs du monde"
  },
  es: {
    title:"☘ CropSense", subtitle:"Recomendación de cultivos basada en IA",
    nitrogen:"Nitrógeno (N)", phosphorus:"Fósforo (P)", potassium:"Potasio (K)",
    temperature:"Temperatura (°C)", humidity:"Humedad (%)", ph:"Valor pH",
    rainfall:"Lluvia (mm)", btn:"Obtener recomendación",
    result_prefix:"Cultivo recomendado:", result_tip:"Haz clic en el nombre del cultivo — aprende cómo cultivarlo.",
    learn_btn:"Aprender a cultivar →", learn_title:"Guía de cultivo",
    offline_msg:"Estás sin conexión. La predicción necesita internet.",
    toggle_en:"Inglés", toggle_auto:"Auto", toggle_choose:"Elegir idioma",
    credits:"☘ Creado para agricultores del mundo"
  },
  ar: {
    title:"☘ كروب‌سينس", subtitle:"توصية المحاصيل بالذكاء الاصطناعي",
    nitrogen:"النيتروجين (N)", phosphorus:"الفوسفور (P)", potassium:"البوتاسيوم (K)",
    temperature:"درجة الحرارة (°C)", humidity:"الرطوبة (%)", ph:"قيمة pH",
    rainfall:"هطول الأمطار (mm)", btn:"احصل على توصية",
    result_prefix:"المحصول الموصى به:", result_tip:"انقر على اسم المحصول — تعلم كيفية زراعته.",
    learn_btn:"تعلم الزراعة →", learn_title:"دليل الزراعة",
    offline_msg:"أنت غير متصل بالإنترنت. التنبؤ يحتاج إنترنت.",
    toggle_en:"الإنجليزية", toggle_auto:"تلقائي", toggle_choose:"اختر اللغة",
    credits:"☘ صُنع لمزارعي العالم"
  },
  pt: {
    title:"☘ CropSense", subtitle:"Recomendação de culturas baseada em IA",
    nitrogen:"Nitrogênio (N)", phosphorus:"Fósforo (P)", potassium:"Potássio (K)",
    temperature:"Temperatura (°C)", humidity:"Umidade (%)", ph:"Valor pH",
    rainfall:"Chuva (mm)", btn:"Obter recomendação",
    result_prefix:"Cultura recomendada:", result_tip:"Clique no nome da cultura — aprenda como cultivar.",
    learn_btn:"Aprender a cultivar →", learn_title:"Guia de cultivo",
    offline_msg:"Você está offline. A previsão precisa de internet.",
    toggle_en:"Inglês", toggle_auto:"Auto", toggle_choose:"Escolher idioma",
    credits:"☘ Feito para agricultores do mundo"
  },
  ko: {
    title:"☘ 크롭센스", subtitle:"AI 기반 작물 추천 시스템",
    nitrogen:"질소 (N)", phosphorus:"인 (P)", potassium:"칼륨 (K)",
    temperature:"온도 (°C)", humidity:"습도 (%)", ph:"pH 값",
    rainfall:"강수량 (mm)", btn:"추천 받기",
    result_prefix:"추천 작물:", result_tip:"작물 이름을 탭하여 재배 방법을 배우세요。",
    learn_btn:"재배 배우기 →", learn_title:"재배 가이드",
    offline_msg:"오프라인 상태입니다. 예측에는 인터넷이 필요합니다.",
    toggle_en:"영어", toggle_auto:"자동", toggle_choose:"언어 선택",
    credits:"☘ 세계 농부들을 위해 만들었습니다"
  }
};

/* Country → language code mapping */
const COUNTRY_LANG = {
  /* India — state-level via region field */
  IN_OR:"or", IN_MH:"mr", IN_WB:"bn", IN_TN:"ta", IN_AP:"te", IN_TS:"te",
  IN_KA:"kn", IN_GJ:"gu", IN_PB:"pa", IN_KL:"ml",
  IN:"hi",   /* default India */
  /* World */
  DE:"de", AT:"de", CH_DE:"de",
  IT:"it",
  JP:"ja",
  CN:"zh", TW:"zh", HK:"zh",
  RU:"ru",
  FR:"fr", BE:"fr",
  ES:"es", MX:"es", AR_ES:"es", CO:"es",
  PT:"pt", BR:"pt",
  KR:"ko",
  SA:"ar", EG:"ar", AE:"ar", IQ:"ar"
};

/* State → lang for Indian states */
const INDIA_STATE_LANG = {
  "Odisha":"or","Orissa":"or",
  "Maharashtra":"mr",
  "West Bengal":"bn",
  "Tamil Nadu":"ta",
  "Andhra Pradesh":"te","Telangana":"te",
  "Karnataka":"kn",
  "Gujarat":"gu",
  "Punjab":"pa",
  "Kerala":"ml"
};
"""

# ══════════════════════════════════════════════════════════════════════════════
# 5.  SCRIPT.JS  (i18n engine + crop learning)
# ══════════════════════════════════════════════════════════════════════════════
SCRIPT_JS = TRANSLATIONS_JS + r"""

/* ── Language state ── */
let currentLang = 'en';
let autoLang    = 'en';

/* ── Crop learning data (Gemini-style placeholder — extendable) ── */
const CROP_INFO = {
  rice:       { emoji:"🌾", season:"Jun–Nov", water:"High", tip:"Keep fields flooded 2–5cm initially." },
  wheat:      { emoji:"🌾", season:"Oct–Mar", water:"Medium", tip:"Sow after monsoon, irrigate 4–5 times." },
  maize:      { emoji:"🌽", season:"Jun–Sep", water:"Medium", tip:"Space rows 60–75 cm apart." },
  chickpea:   { emoji:"🫘", season:"Oct–Feb", water:"Low", tip:"Avoid waterlogging — well-drained soil needed." },
  kidneybeans:{ emoji:"🫘", season:"Jun–Sep", water:"Medium", tip:"Stake plants for better yield." },
  pigeonpeas: { emoji:"🫘", season:"Jun–Nov", water:"Low",  tip:"Drought tolerant — ideal for dry zones." },
  mothbeans:  { emoji:"🫘", season:"Jul–Sep", water:"Low",  tip:"Thrives in sandy soils of arid regions." },
  mungbean:   { emoji:"🫘", season:"Mar–Jun", water:"Low",  tip:"Short duration crop — 60–75 days." },
  blackgram:  { emoji:"🫘", season:"Jun–Sep", water:"Low",  tip:"Nitrogen-fixing — improves soil health." },
  lentil:     { emoji:"🫘", season:"Oct–Mar", water:"Low",  tip:"Cool weather crop — avoid heat stress." },
  pomegranate:{ emoji:"🍎", season:"Feb–Apr", water:"Low",  tip:"Tolerates drought — prune annually." },
  banana:     { emoji:"🍌", season:"Year-round", water:"High", tip:"Plant suckers 2m apart, mulch heavily." },
  mango:      { emoji:"🥭", season:"Mar–Jun (fruit)", water:"Low", tip:"Graft trees for early fruiting." },
  grapes:     { emoji:"🍇", season:"Jan–May", water:"Medium", tip:"Train vines on trellis, prune in winter." },
  watermelon: { emoji:"🍉", season:"Feb–May", water:"Medium", tip:"Sandy loam soil gives sweetest fruit." },
  muskmelon:  { emoji:"🍈", season:"Feb–May", water:"Medium", tip:"Stop watering 1 week before harvest." },
  apple:      { emoji:"🍎", season:"Sep–Nov", water:"Medium", tip:"Requires chilling hours — plant in hills." },
  orange:     { emoji:"🍊", season:"Nov–Jan", water:"Medium", tip:"Avoid water stress during fruit set." },
  papaya:     { emoji:"🍈", season:"Year-round", water:"Medium", tip:"Plant on raised beds to prevent rot." },
  coconut:    { emoji:"🥥", season:"Year-round", water:"High", tip:"Coastal sandy soil ideal." },
  cotton:     { emoji:"🌿", season:"May–Nov", water:"Medium", tip:"Deep black soil gives best results." },
  jute:       { emoji:"🌿", season:"Mar–Jul", water:"High", tip:"Needs alluvial soil and humid climate." },
  coffee:     { emoji:"☕", season:"Oct–Feb (harvest)", water:"Medium", tip:"Grow in shade of larger trees." },
};

function getCropInfo(crop) {
  const key = crop.toLowerCase().replace(/\s+/g,'');
  return CROP_INFO[key] || { emoji:"🌱", season:"Varies", water:"Varies", tip:"Consult local agricultural officer." };
}

/* ── Apply translations ── */
function applyLang(lang) {
  if (!TRANSLATIONS[lang]) lang = 'en';
  currentLang = lang;
  const t = TRANSLATIONS[lang];
  const setTxt = (id, key) => { const el = document.getElementById(id); if(el && t[key]) el.textContent = t[key]; };
  const setPlaceholder = (id, key) => { const el = document.getElementById(id); if(el && t[key]) el.placeholder = t[key]; };

  document.querySelector('h1').textContent          = t.title;
  document.querySelector('header p').textContent    = t.subtitle;
  setPlaceholder('nitrogen',    'nitrogen');
  setPlaceholder('phosphorus',  'phosphorus');
  setPlaceholder('potassium',   'potassium');
  setPlaceholder('temperature', 'temperature');
  setPlaceholder('humidity',    'humidity');
  setPlaceholder('pH',          'ph');
  setPlaceholder('rainfall',    'rainfall');
  setTxt('submitBtn', 'btn');
  setTxt('credits',   'credits');
  setTxt('opt-en',    'toggle_en');
  setTxt('opt-auto',  'toggle_auto');
  setTxt('opt-choose','toggle_choose');

  /* RTL for Arabic */
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';

  localStorage.setItem('cs_lang', lang);
}

/* ── IP detection → auto language ── */
async function detectAutoLang() {
  try {
    const res  = await fetch('https://ipapi.co/json/', { signal: AbortSignal.timeout(4000) });
    const data = await res.json();
    const cc   = data.country_code;
    const region = data.region || '';

    let lang = 'en';
    if (cc === 'IN') {
      lang = INDIA_STATE_LANG[region] || 'hi';
    } else {
      lang = COUNTRY_LANG[cc] || 'en';
    }
    autoLang = lang;
    return lang;
  } catch {
    return 'en';
  }
}

/* ── Toggle UI ── */
function setToggle(option) {
  document.querySelectorAll('.lang-opt').forEach(b => b.classList.remove('active'));
  document.getElementById('opt-' + option).classList.add('active');

  const dropdown = document.getElementById('lang-dropdown');
  if (option === 'choose') {
    dropdown.style.display = 'block';
  } else {
    dropdown.style.display = 'none';
    applyLang(option === 'en' ? 'en' : autoLang);
  }
}

/* ── Populate language dropdown ── */
function buildDropdown() {
  const select = document.getElementById('lang-select');
  const langs  = [
    {code:'en',  label:'🌍 English'},
    {code:'hi',  label:'🇮🇳 हिन्दी (Hindi)'},
    {code:'or',  label:'🇮🇳 ଓଡ଼ିଆ (Odia)'},
    {code:'mr',  label:'🇮🇳 मराठी (Marathi)'},
    {code:'bn',  label:'🇮🇳 বাংলা (Bengali)'},
    {code:'ta',  label:'🇮🇳 தமிழ் (Tamil)'},
    {code:'te',  label:'🇮🇳 తెలుగు (Telugu)'},
    {code:'kn',  label:'🇮🇳 ಕನ್ನಡ (Kannada)'},
    {code:'gu',  label:'🇮🇳 ગુજરાતી (Gujarati)'},
    {code:'pa',  label:'🇮🇳 ਪੰਜਾਬੀ (Punjabi)'},
    {code:'ml',  label:'🇮🇳 മലയാളം (Malayalam)'},
    {code:'de',  label:'🇩🇪 Deutsch (German)'},
    {code:'it',  label:'🇮🇹 Italiano (Italian)'},
    {code:'ja',  label:'🇯🇵 日本語 (Japanese)'},
    {code:'zh',  label:'🇨🇳 中文 (Chinese)'},
    {code:'ru',  label:'🇷🇺 Русский (Russian)'},
    {code:'fr',  label:'🇫🇷 Français (French)'},
    {code:'es',  label:'🇪🇸 Español (Spanish)'},
    {code:'ar',  label:'🇸🇦 العربية (Arabic)'},
    {code:'pt',  label:'🇧🇷 Português (Portuguese)'},
    {code:'ko',  label:'🇰🇷 한국어 (Korean)'},
  ];
  langs.forEach(l => {
    const opt = document.createElement('option');
    opt.value = l.code; opt.textContent = l.label;
    select.appendChild(opt);
  });
  select.addEventListener('change', () => applyLang(select.value));
}

/* ── Crop Learning Panel ── */
function showLearnPanel(crop) {
  const t    = TRANSLATIONS[currentLang] || TRANSLATIONS.en;
  const info = getCropInfo(crop);
  const panel = document.getElementById('learn-panel');
  panel.innerHTML = `
    <div class="learn-header">
      <span class="learn-emoji">${info.emoji}</span>
      <div>
        <h2>${t.learn_title}: ${crop}</h2>
        <p class="learn-sub">Season: ${info.season} &nbsp;|&nbsp; Water: ${info.water}</p>
      </div>
      <button class="close-btn" onclick="document.getElementById('learn-panel').style.display='none'">✕</button>
    </div>
    <div class="learn-tip">💡 ${info.tip}</div>
    <div class="learn-links">
      <a href="https://www.google.com/search?q=how+to+grow+${encodeURIComponent(crop)}+farming" target="_blank" rel="noopener">🔍 Google Guide</a>
      <a href="https://www.youtube.com/results?search_query=how+to+grow+${encodeURIComponent(crop)}" target="_blank" rel="noopener">▶ YouTube Videos</a>
      <a href="https://en.wikipedia.org/wiki/${encodeURIComponent(crop)}" target="_blank" rel="noopener">📖 Wikipedia</a>
    </div>
  `;
  panel.style.display = 'block';
}

/* ── Form submit ── */
document.getElementById('cropForm').addEventListener('submit', function(e) {
  e.preventDefault();
  const t = TRANSLATIONS[currentLang] || TRANSLATIONS.en;

  const data = {
    nitrogen:    document.getElementById('nitrogen').value,
    phosphorus:  document.getElementById('phosphorus').value,
    potassium:   document.getElementById('potassium').value,
    temperature: document.getElementById('temperature').value,
    humidity:    document.getElementById('humidity').value,
    pH:          document.getElementById('pH').value,
    rainfall:    document.getElementById('rainfall').value,
  };

  const btn = document.getElementById('submitBtn');
  btn.textContent = '⏳ ...';
  btn.disabled = true;

  fetch('/predict', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
  .then(r => r.json())
  .then(result => {
    btn.textContent = t.btn; btn.disabled = false;
    const crop = result.crop;
    const resultDiv = document.getElementById('result');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `
      <div class="result-crop">${t.result_prefix} <strong>${crop}</strong></div>
      <div class="result-tip">${t.result_tip}</div>
      <button class="learn-btn" onclick="showLearnPanel('${crop}')">${t.learn_btn}</button>
    `;
    document.getElementById('learn-panel').style.display = 'none';
  })
  .catch(() => {
    btn.textContent = t.btn; btn.disabled = false;
    document.getElementById('result').innerHTML = '<span style="color:#c0392b">⚠ Connection error</span>';
    document.getElementById('result').style.display = 'block';
  });
});

/* ── Offline banner ── */
function checkOnline() {
  const banner = document.getElementById('offline-banner');
  if (banner) banner.style.display = navigator.onLine ? 'none' : 'block';
}
window.addEventListener('online',  checkOnline);
window.addEventListener('offline', checkOnline);

/* ── Init ── */
window.addEventListener('DOMContentLoaded', async () => {
  buildDropdown();
  checkOnline();

  const saved = localStorage.getItem('cs_lang');
  if (saved) {
    applyLang(saved);
    if (saved === 'en') setToggle('en');
    else { setToggle('choose'); document.getElementById('lang-select').value = saved; }
  } else {
    const detected = await detectAutoLang();
    autoLang = detected;
    setToggle('auto');
  }
});

/* ── Service Worker ── */
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}
"""

# ══════════════════════════════════════════════════════════════════════════════
# 6.  INDEX.HTML
# ══════════════════════════════════════════════════════════════════════════════
INDEX_HTML = """<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CropSense — AI Crop Recommendation</title>

  <!-- ── Open Graph / LinkedIn / Twitter ── -->
  <meta property="og:type"        content="website">
  <meta property="og:url"         content="https://cropsense-39bz.onrender.com/">
  <meta property="og:title"       content="CropSense — AI Crop Recommendation">
  <meta property="og:description" content="Enter your soil & climate data and get the perfect crop recommendation instantly. Supports 20+ languages. Free & open source.">
  <meta property="og:image"       content="https://cropsense-39bz.onrender.com/static/og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height"content="630">
  <meta name="twitter:card"       content="summary_large_image">
  <meta name="twitter:title"      content="CropSense — AI Crop Recommendation">
  <meta name="twitter:description"content="AI-powered crop recommendation in 20+ languages. Free tool for farmers worldwide.">
  <meta name="twitter:image"      content="https://cropsense-39bz.onrender.com/static/og-image.png">

  <!-- ── SEO ── -->
  <meta name="description" content="AI-powered crop recommendation system. Enter soil NPK, pH, temperature and get instant crop suggestion. Supports Hindi, Odia, Marathi, Bengali, Tamil, Telugu, Kannada, Gujarati, Punjabi, Malayalam, German, Italian, Japanese, Chinese, Russian, French, Spanish, Arabic, Portuguese, Korean.">
  <meta name="keywords"    content="crop recommendation, AI farming, soil analysis, NPK, precision agriculture, किसान, ଚାଷ">
  <meta name="author"      content="Kamal Lochan Sahu">

  <link rel="stylesheet" href="/static/style.css">
  <link rel="manifest"   href="/static/manifest.json">
  <meta name="theme-color" content="#2d6a4f">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌱</text></svg>">
</head>
<body>

<!-- Offline banner -->
<div id="offline-banner" style="display:none;background:#e74c3c;color:#fff;text-align:center;padding:8px;font-size:.9rem;">
  📴 <span id="offline-text">You are offline. Predictions need internet.</span>
</div>

<!-- Language toggle bar -->
<div class="lang-bar">
  <button class="lang-opt active" id="opt-en"     onclick="setToggle('en')">English</button>
  <button class="lang-opt"        id="opt-auto"   onclick="setToggle('auto')">Auto</button>
  <button class="lang-opt"        id="opt-choose" onclick="setToggle('choose')">Choose Language</button>
  <select id="lang-select" style="display:none" class="lang-dropdown-select"></select>
</div>

<div id="lang-dropdown" style="display:none;text-align:center;padding:8px 0 0;">
  <!-- select gets shown here via JS -->
</div>

<main>
  <section class="container">
    <header>
      <h1>☘ CropSense</h1>
      <p>AI-powered Crop Recommendation</p>
    </header>

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

    <div id="result"      style="display:none"></div>
    <div id="learn-panel" style="display:none" class="learn-panel"></div>

    <footer>
      <p id="credits" class="credits">Made with ☘ for farmers worldwide</p>
    </footer>
  </section>
</main>

<script src="/static/script.js"></script>
</body>
</html>"""

# ══════════════════════════════════════════════════════════════════════════════
# 7.  STYLE.CSS
# ══════════════════════════════════════════════════════════════════════════════
STYLE_CSS = """/* ── Reset ── */
*, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #f0f4f0;
  color: #333;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* ── Language bar ── */
.lang-bar {
  width: 100%;
  background: #2d6a4f;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  flex-wrap: wrap;
}
.lang-opt {
  background: transparent;
  color: rgba(255,255,255,0.75);
  border: 1.5px solid rgba(255,255,255,0.3);
  border-radius: 20px;
  padding: 4px 14px;
  font-size: .82rem;
  cursor: pointer;
  transition: all .2s;
  width: auto;
  font-weight: 500;
}
.lang-opt:hover, .lang-opt.active {
  background: rgba(255,255,255,0.2);
  color: #fff;
  border-color: rgba(255,255,255,0.7);
}
.lang-dropdown-select {
  margin: 0 auto;
  display: block;
  padding: 8px 12px;
  border-radius: 8px;
  border: 2px solid #2d6a4f;
  font-size: .95rem;
  color: #333;
  background: #fff;
  cursor: pointer;
  max-width: 300px;
  width: 90%;
}

/* ── Main container ── */
main { width:100%; display:flex; justify-content:center; padding: 24px 16px 40px; }

.container {
  background: #fff;
  padding: 36px 32px;
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 500px;
}

/* ── Header ── */
header { text-align: center; margin-bottom: 28px; }
h1     { color: #2d6a4f; font-size: 2rem; margin-bottom: 6px; }
header p { color: #666; font-size: .95rem; }

/* ── Inputs ── */
input {
  width: 100%;
  padding: 12px 16px;
  margin-bottom: 14px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  color: #333;
  outline: none;
  transition: border-color .25s;
}
input:focus { border-color: #2d6a4f; }

/* ── Button ── */
button[type="submit"] {
  width: 100%;
  padding: 14px;
  background: #2d6a4f;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: background .25s;
}
button[type="submit"]:hover    { background: #1b4332; }
button[type="submit"]:disabled { background: #74a98a; cursor: not-allowed; }

/* ── Result ── */
#result {
  margin-top: 22px;
  padding: 20px;
  background: #d8f3dc;
  border-radius: 10px;
  text-align: center;
}
.result-crop { font-size: 1.15rem; font-weight: 700; color: #1b4332; margin-bottom: 6px; }
.result-tip  { font-size: .85rem; color: #4a4a4a; margin-bottom: 12px; }
.learn-btn {
  display: inline-block;
  width: auto;
  padding: 8px 20px;
  background: #2d6a4f;
  color: #fff;
  border-radius: 6px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: background .2s;
}
.learn-btn:hover { background: #1b4332; }

/* ── Learn panel ── */
.learn-panel {
  margin-top: 18px;
  padding: 20px;
  background: #f7fdf9;
  border: 1.5px solid #b7e4c7;
  border-radius: 12px;
}
.learn-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.learn-emoji { font-size: 2.2rem; }
.learn-header h2 { font-size: 1.05rem; color: #1b4332; margin-bottom: 4px; }
.learn-sub { font-size: .82rem; color: #555; }
.close-btn {
  margin-left: auto; background: transparent; border: none;
  font-size: 1.1rem; cursor: pointer; color: #888; width:auto; padding:4px 8px;
}
.learn-tip {
  background: #e8f5e9;
  border-left: 3px solid #2d6a4f;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: .9rem;
  color: #2d6a4f;
  margin-bottom: 14px;
}
.learn-links { display: flex; flex-wrap: wrap; gap: 8px; }
.learn-links a {
  padding: 7px 14px;
  background: #2d6a4f;
  color: #fff;
  border-radius: 6px;
  font-size: .82rem;
  text-decoration: none;
  transition: background .2s;
}
.learn-links a:hover { background: #1b4332; }

/* ── Footer ── */
.credits { text-align:center; margin-top:24px; font-size:.82rem; color:#aaa; }

/* ── Responsive ── */
@media (max-width: 480px) {
  .container { padding: 28px 18px; }
  h1 { font-size: 1.6rem; }
  .lang-opt { padding: 4px 10px; font-size: .78rem; }
}

/* ── RTL support (Arabic) ── */
[dir="rtl"] input, [dir="rtl"] button { text-align: right; }
[dir="rtl"] .learn-tip { border-left: none; border-right: 3px solid #2d6a4f; }
[dir="rtl"] .learn-header { flex-direction: row-reverse; }
"""

# ══════════════════════════════════════════════════════════════════════════════
# 8.  OG IMAGE  (1200 × 630 via Pillow)
# ══════════════════════════════════════════════════════════════════════════════
def generate_og_image():
    if not PILLOW_OK:
        return
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#0d2b1e")
    d   = ImageDraw.Draw(img)

    # Background gradient layers
    for i in range(40):
        green = 28 + i
        d.rectangle([i*8, i*5, W - i*8, H - i*5], fill=(13, green, 25))

    # Decorative circles top-right
    for r in [300, 220, 140]:
        d.ellipse([W - r, -r//2, W + r//2, r], outline="#1e4d38", width=2)

    # Decorative circles bottom-left
    for r in [250, 170]:
        d.ellipse([-r//2, H - r, r, H + r//2], outline="#1e4d38", width=2)

    # Top accent stripe
    d.rectangle([60, 50, W - 60, 57], fill="#52b788")

    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 82)
        font_sub   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 33)
        font_tag   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 21)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    except Exception:
        font_title = font_sub = font_tag = font_small = ImageFont.load_default()

    # Main title
    d.text((W//2, 185), "CropSense", font=font_title, fill="#d8f3dc", anchor="mm")

    # AI badge pill (manual rounded rect — Pillow <9 compatible)
    def pill(x1, y1, x2, y2, fill):
        r = (y2 - y1) // 2
        d.rectangle([x1+r, y1, x2-r, y2], fill=fill)
        d.ellipse([x1, y1, x1+2*r, y2], fill=fill)
        d.ellipse([x2-2*r, y1, x2, y2], fill=fill)

    pill(W//2 - 215, 122, W//2 - 128, 150, "#2d6a4f")
    d.text((W//2 - 172, 136), "☘  AI", font=font_tag, fill="#95d5b2", anchor="mm")

    # Subtitle
    d.text((W//2, 262), "AI-powered Crop Recommendation System", font=font_sub, fill="#95d5b2", anchor="mm")

    # Divider
    d.line([(200, 305), (W - 200, 305)], fill="#2d6a4f", width=1)

    # 4 stat cards
    stats = [("🌾", "22 Crops"), ("🌍", "20+ Languages"), ("🤖", "99.3% Acc."), ("📱", "PWA Ready")]
    pw, ph = 208, 68
    gap    = 20
    sx     = (W - (len(stats) * pw + (len(stats)-1) * gap)) // 2
    sy     = 325

    for i, (icon, label) in enumerate(stats):
        cx = sx + i * (pw + gap)
        pill(cx, sy, cx + pw, sy + ph, "#1b4332")
        # border lines
        d.line([(cx+14, sy), (cx+pw-14, sy)], fill="#2d6a4f", width=1)
        d.line([(cx+14, sy+ph), (cx+pw-14, sy+ph)], fill="#2d6a4f", width=1)
        d.text((cx + 36, sy + ph//2), icon, font=font_sub, fill="#d8f3dc", anchor="mm")
        d.text((cx + pw//2 + 18, sy + ph//2), label, font=font_tag, fill="#95d5b2", anchor="mm")

    # Built by
    d.text((W//2, 450), "Built by Kamal Lochan Sahu", font=font_tag, fill="#52b788", anchor="mm")

    # Language row
    d.text((W//2, 492),
           "HI  OR  MR  BN  TA  TE  KN  GU  PA  ML  DE  IT  JA  ZH  RU  FR  ES  AR  PT  KO",
           font=font_small, fill="#2d6a4f", anchor="mm")

    # Bottom bar
    d.rectangle([0, H - 56, W, H], fill="#061410")
    d.text((W//2, H - 28),
           "cropsense-39bz.onrender.com  •  Free & Open Source  •  github.com/kamal-lochan-sahu",
           font=font_small, fill="#52b788", anchor="mm")

    out = STATIC / "og-image.png"
    img.save(out, "PNG", optimize=True)
    print(f"✅ OG image generated: {out}  ({W}×{H}px)")

# ══════════════════════════════════════════════════════════════════════════════
# 9.  REQUIREMENTS.TXT  (add Pillow if missing)
# ══════════════════════════════════════════════════════════════════════════════
def update_requirements():
    req_path = BASE / "requirements.txt"
    content  = req_path.read_text(encoding="utf-8", errors="ignore") if req_path.exists() else ""
    if "Pillow" not in content and "pillow" not in content:
        with open(req_path, "a") as f:
            f.write("\nPillow>=10.0.0\n")
        print("✅ requirements.txt — Pillow added")
    else:
        print("ℹ  requirements.txt — Pillow already present")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def write(path: Path, content: str, label: str):
    path.write_text(content, encoding="utf-8")
    print(f"✅ Written: {label}")

def main():
    print("\n🌱 CropSense v2 Upgrade Starting...\n")

    fix_comma_bugs()
    write(STATIC   / "manifest.json", MANIFEST,   "static/manifest.json")
    write(STATIC   / "sw.js",         SW_JS,       "static/sw.js")
    write(STATIC   / "script.js",     SCRIPT_JS,   "static/script.js")
    write(STATIC   / "style.css",     STYLE_CSS,   "static/style.css")
    write(TEMPLATE / "index.html",    INDEX_HTML,  "templates/index.html")
    generate_og_image()
    update_requirements()

    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅  CropSense v2 Upgrade Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files updated:
  templates/index.html   ← OG tags + i18n toggle + learn panel
  static/style.css       ← Language bar + learn panel styles
  static/script.js       ← 20-language i18n engine + IP detection
  static/manifest.json   ← Fixed (was manifest,json)
  static/sw.js           ← Fixed + proper offline caching
  static/og-image.png    ← LinkedIn/Twitter preview (1200×630)

Next steps:
  1. python3 app.py          → test locally at http://localhost:5000
  2. git add -A
  3. git commit -m "feat: i18n 20 langs + OG image + PWA fix + crop learning"
  4. git push origin main    → Render auto-deploy starts

LinkedIn pe share karte waqt:
  URL paste karo → preview automatically aayega og-image se ☘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

if __name__ == "__main__":
    main()
