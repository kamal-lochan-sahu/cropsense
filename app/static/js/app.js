'use strict';

/* CropSense frontend. Needs translations.js (TRANSLATIONS, GUIDE_LABELS) loaded first.
   Text from the server or an LLM is never parsed as HTML and there are no inline handlers:
   everything is built with DOM APIs, which keeps the page compatible with a strict
   Content-Security-Policy. */

const API = { predict: '/predict', guide: '/crop-guide' };
const FIELDS = ['nitrogen', 'phosphorus', 'potassium', 'temperature', 'humidity', 'pH', 'rainfall'];
const DEFAULT_LANG = 'en';
const PREDICT_TIMEOUT_MS = 60000; // a sleeping free-tier server can need ~50s to wake up
const GUIDE_TIMEOUT_MS = 45000;
const WAKE_HINT_MS = 6000;
const LOW_CONFIDENCE = 0.5;

const COUNTRY_LANG = {
  IN: 'hi', DE: 'de', AT: 'de', IT: 'it', JP: 'ja', CN: 'zh', TW: 'zh', HK: 'zh', RU: 'ru',
  FR: 'fr', BE: 'fr', ES: 'es', MX: 'es', AR: 'es', CO: 'es', PT: 'pt', BR: 'pt', KR: 'ko',
  SA: 'ar', EG: 'ar', AE: 'ar', IQ: 'ar',
};
const INDIA_STATE_LANG = {
  Odisha: 'or', Orissa: 'or', Maharashtra: 'mr', 'West Bengal': 'bn', 'Tamil Nadu': 'ta',
  'Andhra Pradesh': 'te', Telangana: 'te', Karnataka: 'kn', Gujarat: 'gu', Punjab: 'pa', Kerala: 'ml',
};

const LANGUAGE_OPTIONS = [
  ['en', '🌍 English'], ['hi', '🇮🇳 हिन्दी (Hindi)'], ['or', '🇮🇳 ଓଡ଼ିଆ (Odia)'],
  ['mr', '🇮🇳 मराठी (Marathi)'], ['bn', '🇮🇳 বাংলা (Bengali)'], ['ta', '🇮🇳 தமிழ் (Tamil)'],
  ['te', '🇮🇳 తెలుగు (Telugu)'], ['kn', '🇮🇳 ಕನ್ನಡ (Kannada)'], ['gu', '🇮🇳 ગુજરાતી (Gujarati)'],
  ['pa', '🇮🇳 ਪੰਜਾਬੀ (Punjabi)'], ['ml', '🇮🇳 മലയാളം (Malayalam)'], ['de', '🇩🇪 Deutsch (German)'],
  ['it', '🇮🇹 Italiano (Italian)'], ['ja', '🇯🇵 日本語 (Japanese)'], ['zh', '🇨🇳 中文 (Chinese)'],
  ['ru', '🇷🇺 Русский (Russian)'], ['fr', '🇫🇷 Français (French)'], ['es', '🇪🇸 Español (Spanish)'],
  ['ar', '🇸🇦 العربية (Arabic)'], ['pt', '🇧🇷 Português (Portuguese)'], ['ko', '🇰🇷 한국어 (Korean)'],
];

const CROP_NAMES = {
  kidneybeans: 'Kidney beans', pigeonpeas: 'Pigeon peas', mothbeans: 'Moth beans',
  mungbean: 'Mung bean', blackgram: 'Black gram',
};
const CROP_EMOJI = {
  rice: '🌾', wheat: '🌾', maize: '🌽', chickpea: '🫘', kidneybeans: '🫘', pigeonpeas: '🫘',
  mothbeans: '🫘', mungbean: '🫘', blackgram: '🫘', lentil: '🫘', pomegranate: '🍎', banana: '🍌',
  mango: '🥭', grapes: '🍇', watermelon: '🍉', muskmelon: '🍈', apple: '🍎', orange: '🍊',
  papaya: '🍈', coconut: '🥥', cotton: '🌿', jute: '🌿', coffee: '☕',
};

// Soil advice (the server compares N, P, K and pH with the typical values of the crop).
const ADVICE_LABEL = { nitrogen: 'nitrogen', phosphorus: 'phosphorus', potassium: 'potassium', pH: 'ph' };
const ADVICE_LOW_HINT = { nitrogen: 'fert_n', phosphorus: 'fert_p', potassium: 'fert_k', pH: 'ph_low' };

const SENSOR_RANGES = {
  nitrogen: [20, 100], phosphorus: [15, 80], potassium: [20, 90], temperature: [18, 35],
  humidity: [40, 90], pH: [5.5, 7.5], rainfall: [50, 250],
};

let currentLang = DEFAULT_LANG;
let autoLang = DEFAULT_LANG;
let lastResult = null;
let guideRequestId = 0;
let sensorTimer = null;

/* ── Helpers ─────────────────────────────────────────────────────────── */

const $ = (id) => document.getElementById(id);

function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : String(value));
  }
  for (const child of children.flat()) {
    if (child !== null && child !== undefined && child !== false) node.append(child);
  }
  return node;
}

const storage = {
  get(key) { try { return localStorage.getItem(key); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* private mode */ } },
};

function t(key) {
  const dict = TRANSLATIONS[currentLang];
  return (dict && dict[key]) || TRANSLATIONS[DEFAULT_LANG][key] || key;
}

function guideLabels() {
  return GUIDE_LABELS[currentLang] || GUIDE_LABELS[DEFAULT_LANG];
}

function cropName(crop) {
  return CROP_NAMES[crop] || crop.charAt(0).toUpperCase() + crop.slice(1);
}

function percent(value) {
  const pct = Math.round(value * 100);
  return pct < 1 && value > 0 ? '<1%' : `${pct}%`;
}

async function postJson(url, data, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    });
    let body = null;
    try { body = await response.json(); } catch { body = null; }
    return { ok: response.ok, status: response.status, body: body || {} };
  } finally {
    clearTimeout(timer);
  }
}

/* ── Language ────────────────────────────────────────────────────────── */

function applyLang(lang) {
  if (!TRANSLATIONS[lang]) lang = DEFAULT_LANG;
  currentLang = lang;
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  document.querySelectorAll('[data-i18n]').forEach((node) => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll('[data-i18n-aria]').forEach((node) => {
    node.setAttribute('aria-label', t(node.dataset.i18nAria));
  });
  if (lastResult) renderResult(lastResult);
  hideGuide();
}

function detectBrowserLang() {
  const tags = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language];
  for (const tag of tags) {
    const base = String(tag || '').toLowerCase().split('-')[0];
    if (base !== 'en' && TRANSLATIONS[base]) return base;
  }
  return null;
}

async function detectAutoLang() {
  const fromBrowser = detectBrowserLang();
  if (fromBrowser) return fromBrowser;
  try {
    const response = await fetch('https://ipapi.co/json/', { signal: AbortSignal.timeout(4000) });
    const data = await response.json();
    if (data.country_code === 'IN') return INDIA_STATE_LANG[data.region] || 'hi';
    return COUNTRY_LANG[data.country_code] || DEFAULT_LANG;
  } catch {
    return DEFAULT_LANG;
  }
}

let langModeRequest = 0;

async function setLangMode(mode, save = true) {
  const request = ++langModeRequest;
  document.querySelectorAll('.lang-opt').forEach((button) => {
    const active = button.dataset.langMode === mode;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
  $('lang-dropdown').hidden = mode !== 'choose';
  if (save) storage.set('cs_lang_pick', mode); // only a mode the user tapped is remembered

  if (mode === 'en') {
    applyLang('en');
  } else if (mode === 'auto') {
    const detected = await detectAutoLang();
    if (request !== langModeRequest) return; // the user picked another mode meanwhile
    autoLang = detected;
    applyLang(autoLang);
  } else {
    const select = $('lang-select');
    const chosen = storage.get('cs_lang') || select.value || DEFAULT_LANG;
    select.value = TRANSLATIONS[chosen] ? chosen : DEFAULT_LANG;
    applyLang(select.value);
  }
}

function buildLanguageSelect() {
  const select = $('lang-select');
  select.replaceChildren(...LANGUAGE_OPTIONS.map(([code, label]) => h('option', { value: code, text: label })));
  select.addEventListener('change', () => {
    storage.set('cs_lang', select.value);
    applyLang(select.value);
  });
}

/* ── Input tabs ──────────────────────────────────────────────────────── */

function setInputMode(mode) {
  document.querySelectorAll('.mode-tab').forEach((tab) => {
    const active = tab.dataset.mode === mode;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('.mode-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `mode-panel-${mode}`);
  });
  if (mode !== 'sensor') stopSensorDemo();
}

/* ── Prediction ──────────────────────────────────────────────────────── */

function setFieldError(name, message) {
  const input = $(name);
  const error = $(`err-${name}`);
  if (!input || !error) return;
  error.textContent = message || '';
  error.hidden = !message;
  input.setAttribute('aria-invalid', message ? 'true' : 'false');
}

function clearFieldErrors() {
  FIELDS.forEach((name) => setFieldError(name, ''));
}

function translateFieldError(message) {
  if (message === 'required') return t('err_required');
  const range = /^must be between (\S+) and (\S+)$/.exec(message);
  if (range) return t('err_range').replace('{min}', range[1]).replace('{max}', range[2]);
  return t('err_number');
}

function showFieldErrors(fields) {
  let first = null;
  for (const name of FIELDS) { // form order, so focus lands on the top-most invalid field
    if (!(name in fields)) continue;
    setFieldError(name, translateFieldError(fields[name]));
    first = first || name;
  }
  if (first) $(first).focus();
}

function showStatus(message, kind = 'info') {
  lastResult = null;
  const box = $('result');
  box.className = `result status-${kind}`;
  box.replaceChildren(h('div', { class: 'status-text', text: message }));
  box.hidden = false;
}

function adviceNumber(value) {
  return String(Math.round(value * 10) / 10);
}

function adviceHint(item) {
  if (item.status === 'low') return t(ADVICE_LOW_HINT[item.field]);
  if (item.status === 'high') return t(item.field === 'pH' ? 'ph_high' : 'advice_high');
  return null;
}

function renderAdvice(advice) {
  const items = (Array.isArray(advice.items) ? advice.items : []).filter((item) => (
    item.field in ADVICE_LABEL && ['low', 'ok', 'high'].includes(item.status)
    && [item.low, item.high].every(Number.isFinite)));
  if (!items.length) return null;

  const rows = items.map((item) => h('li', { class: `advice-row advice-${item.status}` },
    h('div', { class: 'advice-head' },
      h('span', { class: 'advice-name', text: t(ADVICE_LABEL[item.field]) }),
      h('span', { class: 'advice-badge', text: t(`status_${item.status}`) })),
    h('div', { class: 'advice-range', text: t('advice_typical')
      .replace('{min}', adviceNumber(item.low)).replace('{max}', adviceNumber(item.high)) }),
    adviceHint(item) ? h('div', { class: 'advice-hint', text: adviceHint(item) }) : null));

  return h('div', { class: 'advice' },
    h('div', { class: 'advice-title', text: t('advice_title') }),
    h('ul', { class: 'advice-list' }, rows),
    items.every((item) => item.status === 'ok') ? h('div', { class: 'advice-all-ok', text: t('advice_ok') }) : null,
    h('div', { class: 'advice-note', text: t('advice_note') }));
}

function renderResult(result) {
  const top = Array.isArray(result.top) && result.top.length
    ? result.top
    : [{ crop: result.crop, confidence: result.confidence }];
  const best = top[0];
  const box = $('result');
  box.className = 'result';

  const parts = [
    h('div', { class: 'result-crop' }, `${t('result_prefix')} `,
      h('strong', { text: `${CROP_EMOJI[best.crop] || '🌱'} ${cropName(best.crop)}` })),
  ];
  if (typeof best.confidence === 'number') {
    parts.push(h('div', { class: 'result-confidence', text: `${t('confidence')}: ${percent(best.confidence)}` }));
    if (best.confidence < LOW_CONFIDENCE) {
      parts.push(h('div', { class: 'result-warning', role: 'note', text: t('low_confidence') }));
    }
  }

  if (Array.isArray(result.warnings) && result.warnings.length) {
    parts.push(h('div', { class: 'result-warning', role: 'note' },
      h('strong', { text: t('warn_title') }),
      h('ul', {}, result.warnings.map((w) => h('li', { text: w.message })))));
  }

  if (result.advice) parts.push(renderAdvice(result.advice));

  parts.push(h('div', { class: 'result-tip', text: t('result_tip') }));
  parts.push(h('button', { type: 'button', class: 'learn-btn', onclick: () => showGuide(best.crop), text: t('learn_btn') }));

  if (top.length > 1 && typeof best.confidence === 'number') {
    parts.push(h('div', { class: 'top-heading', text: t('other_options') }));
    parts.push(h('ul', { class: 'top-list' }, top.map((item) => {
      const fill = h('span', { class: 'bar-fill' });
      fill.style.width = `${Math.max(2, Math.round(item.confidence * 100))}%`;
      return h('li', {},
        h('button', { type: 'button', class: 'crop-chip', onclick: () => showGuide(item.crop), text: cropName(item.crop) }),
        h('span', { class: 'bar', 'aria-hidden': 'true' }, fill),
        h('span', { class: 'pct', text: percent(item.confidence) }));
    })));
  }

  box.replaceChildren(...parts);
  box.hidden = false;
  lastResult = result;
}

function setBusy(busy) {
  const button = $('submitBtn');
  button.disabled = busy;
  button.setAttribute('aria-busy', String(busy));
  button.textContent = busy ? '⏳ …' : t('btn');
}

async function onSubmit(event) {
  event.preventDefault();
  clearFieldErrors();
  hideGuide();
  const payload = Object.fromEntries(FIELDS.map((name) => [name, $(name).value]));

  setBusy(true);
  const wakeTimer = setTimeout(() => showStatus(t('waking')), WAKE_HINT_MS);
  try {
    const { ok, status, body } = await postJson(API.predict, payload, PREDICT_TIMEOUT_MS);
    clearTimeout(wakeTimer);
    if (ok) {
      renderResult(body);
    } else if (status === 422 && body.fields) {
      showFieldErrors(body.fields);
      showStatus(t('error_fix_inputs'), 'error');
    } else {
      showStatus(t('error_generic'), 'error');
    }
  } catch (error) {
    clearTimeout(wakeTimer);
    showStatus(error.name === 'AbortError' ? t('error_timeout') : t('error_network'), 'error');
  } finally {
    setBusy(false);
  }
}

/* ── Growing guide ───────────────────────────────────────────────────── */

const GUIDE_ROWS = [
  ['season', '🗓️'], ['soil', '🌱'], ['water', '💧'],
  ['fertilizer', '🧪'], ['pests', '🐛'], ['harvest', '🌾'],
];

function hideGuide() {
  guideRequestId += 1; // ignore any response still in flight
  const panel = $('learn-panel');
  panel.hidden = true;
  panel.replaceChildren();
}

function guideHeader(crop) {
  return h('div', { class: 'learn-header' },
    h('h2', { text: `${t('learn_title')}: ${cropName(crop)}` }),
    h('button', { type: 'button', class: 'close-btn', 'aria-label': t('close'), onclick: hideGuide, text: '✕' }));
}

function fallbackLinks(crop) {
  const query = encodeURIComponent(crop);
  const link = (href, text) => h('a', { href, target: '_blank', rel: 'noopener noreferrer', text });
  return h('div', { class: 'learn-links' },
    link(`https://www.google.com/search?q=how+to+grow+${query}+farming`, '🔍 Google Guide'),
    link(`https://www.youtube.com/results?search_query=how+to+grow+${query}`, '▶ YouTube Videos'),
    link(`https://en.wikipedia.org/wiki/${query}`, '📖 Wikipedia'));
}

function renderGuide(crop, guide) {
  const labels = guideLabels();
  const rows = GUIDE_ROWS.filter(([key]) => typeof guide[key] === 'string' && guide[key]).map(([key, icon]) =>
    h('div', { class: 'guide-row' },
      h('span', { class: 'guide-icon', 'aria-hidden': 'true', text: icon }),
      h('div', { class: 'guide-row-text' },
        h('strong', { text: labels[key] || key }),
        h('p', { text: guide[key] }))));
  const panel = $('learn-panel');
  panel.replaceChildren(
    guideHeader(crop),
    h('div', { class: 'guide-grid' }, rows),
    typeof guide.tip === 'string' && guide.tip
      ? h('div', { class: 'learn-tip' }, '💡 ', h('strong', { text: `${labels.tip}:` }), ` ${guide.tip}`)
      : null,
    h('div', { class: 'ai-credit', text: t('ai_credit') }));
}

async function showGuide(crop) {
  const requestId = ++guideRequestId;
  const labels = guideLabels();
  const panel = $('learn-panel');
  panel.replaceChildren(
    guideHeader(crop),
    h('div', { class: 'ai-loading', role: 'status' }, h('div', { class: 'spinner' }), h('span', { text: labels.loading })));
  panel.hidden = false;
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  try {
    const { ok, body } = await postJson(API.guide, { crop, lang: currentLang }, GUIDE_TIMEOUT_MS);
    if (requestId !== guideRequestId) return;
    if (!ok || body.error) throw new Error(body.error || 'failed');
    renderGuide(crop, JSON.parse(body.guide));
  } catch {
    if (requestId !== guideRequestId) return;
    panel.replaceChildren(
      guideHeader(crop),
      h('div', { class: 'ai-error', role: 'alert', text: `⚠ ${labels.error}` }),
      fallbackLinks(crop));
  }
}

/* ── Soil report + sensor demo (placeholders) ────────────────────────── */

function onReportFileChange(event) {
  const name = (event.target.files && event.target.files[0] && event.target.files[0].name) || '';
  $('report-filename').textContent = name;
  $('report-note').style.display = name ? 'block' : 'none';
}

function stopSensorDemo() {
  if (sensorTimer) { clearInterval(sensorTimer); sensorTimer = null; }
}

function startSensorDemo() {
  stopSensorDemo();
  const display = $('sensor-readout');
  const tick = () => {
    const values = {};
    for (const name of FIELDS) {
      const [low, high] = SENSOR_RANGES[name];
      const value = Math.random() * (high - low) + low;
      values[name] = name === 'pH' ? value.toFixed(1) : String(Math.round(value));
    }
    display.replaceChildren(...FIELDS.map((name) => h('div', { class: 'sensor-cell' },
      h('span', { class: 'sensor-label', text: name }),
      h('span', { class: 'sensor-value', text: values[name] }))));
    display.dataset.values = JSON.stringify(values);
  };
  tick();
  sensorTimer = setInterval(tick, 2000);
}

function useSensorReading() {
  const display = $('sensor-readout');
  if (!display.dataset.values) return;
  const values = JSON.parse(display.dataset.values);
  stopSensorDemo();
  for (const name of FIELDS) $(name).value = values[name];
  setInputMode('manual');
  $('cropForm').scrollIntoView({ behavior: 'smooth' });
}

/* ── Online state + service worker ───────────────────────────────────── */

function checkOnline() {
  $('offline-banner').hidden = navigator.onLine;
}

function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  // Earlier versions registered the worker under /static/, where it could not control the page.
  navigator.serviceWorker.getRegistrations()
    .then((registrations) => registrations
      .filter((registration) => registration.scope.endsWith('/static/'))
      .forEach((registration) => registration.unregister()))
    .catch(() => {});
  navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
}

/* ── Init ────────────────────────────────────────────────────────────── */

function bindEvents() {
  $('cropForm').addEventListener('submit', onSubmit);
  document.querySelectorAll('.lang-opt').forEach((button) => {
    button.addEventListener('click', () => setLangMode(button.dataset.langMode));
  });
  document.querySelectorAll('.mode-tab').forEach((tab) => {
    tab.addEventListener('click', () => setInputMode(tab.dataset.mode));
  });
  $('soil-report-file').addEventListener('change', onReportFileChange);
  $('sensor-start').addEventListener('click', startSensorDemo);
  $('sensor-use').addEventListener('click', useSensorReading);
  FIELDS.forEach((name) => $(name).addEventListener('input', () => setFieldError(name, '')));
  window.addEventListener('online', checkOnline);
  window.addEventListener('offline', checkOnline);
}

async function init() {
  buildLanguageSelect();
  bindEvents();
  checkOnline();
  registerServiceWorker();

  // The page opens in English. A language mode is restored only if the user picked one earlier;
  // the region lookup (ipapi.co) therefore runs only after the user taps "Auto".
  const legacyLang = storage.get('cs_lang');
  let mode = storage.get('cs_lang_pick');
  if (!mode) mode = legacyLang && legacyLang !== DEFAULT_LANG ? 'choose' : 'en';
  await setLangMode(mode, false);
}

document.addEventListener('DOMContentLoaded', init);
