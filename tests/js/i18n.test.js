'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadApp, jsonResponse, tick } = require('./helpers');

const GUIDE_KEYS = ['season', 'soil', 'water', 'fertilizer', 'pests', 'harvest', 'tip', 'loading', 'error'];

async function withApp(t, options) {
  const app = await loadApp(options);
  t.after(() => app.close());
  return app;
}

test('every language has exactly the English keys', async (t) => {
  const app = await withApp(t);
  const translations = app.page('TRANSLATIONS');
  const english = Object.keys(translations.en).sort();
  assert.equal(Object.keys(translations).length, 21);
  for (const [lang, dict] of Object.entries(translations)) {
    assert.deepEqual(Object.keys(dict).sort(), english, `keys differ in ${lang}`);
  }
});

test('no translation is empty and err_range keeps both placeholders', async (t) => {
  const app = await withApp(t);
  for (const [lang, dict] of Object.entries(app.page('TRANSLATIONS'))) {
    for (const [key, value] of Object.entries(dict)) {
      assert.ok(typeof value === 'string' && value.trim(), `${lang}.${key} is empty`);
    }
    assert.ok(dict.err_range.includes('{min}') && dict.err_range.includes('{max}'), `${lang}.err_range`);
  }
});

test('every language has all guide labels', async (t) => {
  const app = await withApp(t);
  const labels = app.page('GUIDE_LABELS');
  const languages = Object.keys(app.page('TRANSLATIONS'));
  assert.deepEqual(Object.keys(labels).sort(), languages.sort());
  for (const [lang, dict] of Object.entries(labels)) {
    assert.deepEqual(Object.keys(dict).sort(), [...GUIDE_KEYS].sort(), `guide labels differ in ${lang}`);
  }
});

test('the language picker lists every translated language once', async (t) => {
  const app = await withApp(t);
  const options = [...app.$('lang-select').options].map((option) => option.value);
  assert.deepEqual([...options].sort(), Object.keys(app.page('TRANSLATIONS')).sort());
  assert.equal(new Set(options).size, options.length);
});

test('t() falls back to English, then to the key itself', async (t) => {
  const app = await withApp(t);
  app.page('TRANSLATIONS').hi.close = '';
  app.page('applyLang')('hi');
  assert.equal(app.page('t')('close'), app.page('TRANSLATIONS').en.close);
  assert.equal(app.page('t')('no_such_key'), 'no_such_key');
});

test('applyLang switches text, lang and direction (Arabic is right-to-left)', async (t) => {
  const app = await withApp(t);
  const translations = app.page('TRANSLATIONS');

  app.page('applyLang')('ar');
  assert.equal(app.document.documentElement.lang, 'ar');
  assert.equal(app.document.documentElement.dir, 'rtl');
  assert.equal(app.$('submitBtn').textContent, translations.ar.btn);
  assert.equal(app.$('lang-select').getAttribute('aria-label'), translations.ar.lang_select_label);

  app.page('applyLang')('de');
  assert.equal(app.document.documentElement.dir, 'ltr');
  assert.equal(app.$('submitBtn').textContent, translations.de.btn);

  app.page('applyLang')('xx'); // unknown code falls back to English
  assert.equal(app.document.documentElement.lang, 'en');
  assert.equal(app.$('submitBtn').textContent, translations.en.btn);
});

test('every language can be applied without errors', async (t) => {
  const app = await withApp(t);
  for (const lang of Object.keys(app.page('TRANSLATIONS'))) {
    app.page('applyLang')(lang);
    assert.equal(app.document.documentElement.lang, lang);
    for (const node of app.document.querySelectorAll('[data-i18n]')) {
      assert.ok(node.textContent.trim(), `${lang}: empty text for ${node.dataset.i18n}`);
    }
  }
});

test('detectBrowserLang picks the first supported non-English language', async (t) => {
  const app = await withApp(t);
  const setLanguages = (value) => Object.defineProperty(app.window.navigator, 'languages', { value, configurable: true });
  const detect = app.page('detectBrowserLang');

  setLanguages(['hi-IN', 'en']);
  assert.equal(detect(), 'hi');
  setLanguages(['en-US', 'de-DE']);
  assert.equal(detect(), 'de');
  setLanguages(['en-US']);
  assert.equal(detect(), null);
  setLanguages(['xx-YY']);
  assert.equal(detect(), null);
});

test('auto mode uses the browser language when it is supported', async (t) => {
  const app = await withApp(t, { storage: { cs_lang_pick: 'auto' }, languages: ['ja-JP'] });
  assert.equal(app.document.documentElement.lang, 'ja');
  assert.equal(app.$('submitBtn').textContent, app.page('TRANSLATIONS').ja.btn);
});

test('auto mode falls back to the IP location, and to English when that fails', async (t) => {
  const odisha = await withApp(t, {
    storage: { cs_lang_pick: 'auto' },
    fetch: async () => jsonResponse(200, { country_code: 'IN', region: 'Odisha' }),
  });
  assert.equal(odisha.document.documentElement.lang, 'or');

  const failing = await withApp(t, { storage: { cs_lang_pick: 'auto' } });
  assert.equal(failing.document.documentElement.lang, 'en');
});

test('choosing a language from the dropdown applies and remembers it', async (t) => {
  const app = await withApp(t);
  app.document.querySelector('[data-lang-mode="choose"]').click();
  await tick();
  assert.equal(app.$('lang-dropdown').hidden, false);

  app.$('lang-select').value = 'ta';
  app.$('lang-select').dispatchEvent(new app.window.Event('change'));
  assert.equal(app.document.documentElement.lang, 'ta');
  assert.equal(app.window.localStorage.getItem('cs_lang'), 'ta');
  assert.equal(app.window.localStorage.getItem('cs_lang_pick'), 'choose');
});

test('the saved language mode is restored on load', async (t) => {
  const app = await withApp(t, { storage: { cs_lang_pick: 'choose', cs_lang: 'ko' } });
  assert.equal(app.document.documentElement.lang, 'ko');
  assert.equal(app.$('lang-select').value, 'ko');
  assert.equal(app.$('lang-dropdown').hidden, false);
});

/* ── Default language: English until the user changes it ───────────── */

const ipLookups = (app) => app.calls.filter((call) => call.url.includes('ipapi.co'));
const modeButton = (app, mode) => app.document.querySelector(`[data-lang-mode="${mode}"]`);

test('the page opens in English even when the browser prefers another language', async (t) => {
  const app = await withApp(t, { languages: ['ja-JP', 'hi-IN'] });
  assert.equal(app.document.documentElement.lang, 'en');
  assert.equal(app.$('submitBtn').textContent, app.page('TRANSLATIONS').en.btn);
  assert.equal(modeButton(app, 'en').getAttribute('aria-pressed'), 'true');
  assert.equal(modeButton(app, 'auto').getAttribute('aria-pressed'), 'false');
});

test('opening the page makes no region lookup and saves no language mode', async (t) => {
  const app = await withApp(t, { languages: ['de-DE'] });
  assert.equal(ipLookups(app).length, 0);
  assert.equal(app.window.localStorage.getItem('cs_lang_pick'), null);
});

test('tapping Auto switches to the browser language and remembers the choice', async (t) => {
  const app = await withApp(t, { languages: ['de-DE'] });
  modeButton(app, 'auto').click();
  await tick(10);
  assert.equal(app.document.documentElement.lang, 'de');
  assert.equal(modeButton(app, 'auto').getAttribute('aria-pressed'), 'true');
  assert.equal(app.window.localStorage.getItem('cs_lang_pick'), 'auto');
  assert.equal(ipLookups(app).length, 0); // the browser language was enough
});

test('tapping Auto looks up the region only when the browser language is English', async (t) => {
  const app = await withApp(t, {
    fetch: async () => jsonResponse(200, { country_code: 'IN', region: 'Odisha' }),
  });
  assert.equal(ipLookups(app).length, 0);
  modeButton(app, 'auto').click();
  await tick(10);
  assert.equal(ipLookups(app).length, 1);
  assert.equal(app.document.documentElement.lang, 'or');
});

test('tapping English after Auto goes back to English and remembers it', async (t) => {
  const app = await withApp(t, { languages: ['fr-FR'] });
  modeButton(app, 'auto').click();
  await tick(10);
  assert.equal(app.document.documentElement.lang, 'fr');
  modeButton(app, 'en').click();
  await tick(10);
  assert.equal(app.document.documentElement.lang, 'en');
  assert.equal(app.window.localStorage.getItem('cs_lang_pick'), 'en');
});

test('an Auto mode saved by an earlier version is ignored, so the page opens in English', async (t) => {
  const app = await withApp(t, { storage: { cs_lang_mode: 'auto' }, languages: ['ja-JP'] });
  assert.equal(app.document.documentElement.lang, 'en');
  assert.equal(ipLookups(app).length, 0);
});

test('a language the user picked earlier is still restored', async (t) => {
  const app = await withApp(t, { storage: { cs_lang: 'ta' } });
  assert.equal(app.document.documentElement.lang, 'ta');
  assert.equal(app.$('lang-select').value, 'ta');
  assert.equal(app.$('lang-dropdown').hidden, false);
  assert.equal(modeButton(app, 'choose').getAttribute('aria-pressed'), 'true');
});
