'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadApp, jsonResponse, waitFor, VALID_INPUT } = require('./helpers');

const item = (field, status, extra = {}) => ({
  field, status, value: 50, low: 40, median: 47, high: 58, ...extra,
});

const ALL_OK = [item('nitrogen', 'ok'), item('phosphorus', 'ok'), item('potassium', 'ok'), item('pH', 'ok', { low: 5.4, high: 7.5 })];

function riceWith(items) {
  return {
    crop: 'rice',
    confidence: 0.9,
    top: [{ crop: 'rice', confidence: 0.9 }],
    advice: items === undefined ? undefined : { crop: 'rice', items },
  };
}

async function submit(t, body, options = {}) {
  const app = await loadApp({ fetch: async () => jsonResponse(200, body), ...options });
  t.after(() => app.close());
  app.fill(VALID_INPUT);
  app.submit();
  await waitFor(() => !app.$('submitBtn').disabled);
  return app;
}

const rows = (app) => [...app.$('result').querySelectorAll('.advice-row')];

test('soil advice shows one row per nutrient with its status', async (t) => {
  const app = await submit(t, riceWith([
    item('nitrogen', 'low'), item('phosphorus', 'ok'), item('potassium', 'high'), item('pH', 'ok'),
  ]));
  const en = app.page('TRANSLATIONS').en;
  assert.equal(app.$('result').querySelector('.advice-title').textContent, en.advice_title);
  assert.deepEqual(rows(app).map((r) => r.querySelector('.advice-name').textContent),
    [en.nitrogen, en.phosphorus, en.potassium, en.ph]);
  assert.deepEqual(rows(app).map((r) => r.querySelector('.advice-badge').textContent),
    [en.status_low, en.status_ok, en.status_high, en.status_ok]);
  assert.deepEqual(rows(app).map((r) => r.className),
    ['advice-row advice-low', 'advice-row advice-ok', 'advice-row advice-high', 'advice-row advice-ok']);
});

test('each row shows the typical range of the crop', async (t) => {
  const app = await submit(t, riceWith([item('nitrogen', 'ok', { low: 62.9, high: 95 }), ...ALL_OK.slice(1)]));
  assert.equal(rows(app)[0].querySelector('.advice-range').textContent,
    app.page('TRANSLATIONS').en.advice_typical.replace('{min}', '62.9').replace('{max}', '95'));
});

test('low values get the matching fertilizer hint', async (t) => {
  const app = await submit(t, riceWith([
    item('nitrogen', 'low'), item('phosphorus', 'low'), item('potassium', 'low'), item('pH', 'low'),
  ]));
  const en = app.page('TRANSLATIONS').en;
  assert.deepEqual(rows(app).map((r) => r.querySelector('.advice-hint').textContent),
    [en.fert_n, en.fert_p, en.fert_k, en.ph_low]);
});

test('high values say not to add more, and high pH has its own hint', async (t) => {
  const app = await submit(t, riceWith([
    item('nitrogen', 'high'), item('phosphorus', 'ok'), item('potassium', 'high'), item('pH', 'high'),
  ]));
  const en = app.page('TRANSLATIONS').en;
  assert.equal(rows(app)[0].querySelector('.advice-hint').textContent, en.advice_high);
  assert.equal(rows(app)[2].querySelector('.advice-hint').textContent, en.advice_high);
  assert.equal(rows(app)[3].querySelector('.advice-hint').textContent, en.ph_high);
  assert.equal(rows(app)[1].querySelector('.advice-hint'), null);
});

test('when everything is in range a confirmation is shown', async (t) => {
  const app = await submit(t, riceWith(ALL_OK));
  assert.equal(app.$('result').querySelector('.advice-all-ok').textContent, app.page('TRANSLATIONS').en.advice_ok);
  assert.equal(app.$('result').querySelectorAll('.advice-hint').length, 0);
});

test('the confirmation is not shown when something is off', async (t) => {
  const app = await submit(t, riceWith([item('nitrogen', 'low'), ...ALL_OK.slice(1)]));
  assert.equal(app.$('result').querySelector('.advice-all-ok'), null);
});

test('the advice always carries the not-a-lab-test note', async (t) => {
  const app = await submit(t, riceWith(ALL_OK));
  assert.equal(app.$('result').querySelector('.advice-note').textContent, app.page('TRANSLATIONS').en.advice_note);
});

test('advice appears before the generic tip', async (t) => {
  const app = await submit(t, riceWith(ALL_OK));
  const children = [...app.$('result').children].map((n) => n.className.split(' ')[0]);
  assert.ok(children.indexOf('advice') > -1);
  assert.ok(children.indexOf('advice') < children.indexOf('result-tip'));
});

test('a result without advice still renders normally', async (t) => {
  const app = await submit(t, riceWith(undefined));
  assert.equal(app.$('result').querySelector('.advice'), null);
  assert.match(app.$('result').textContent, /Rice/);
});

test('an empty advice list renders nothing', async (t) => {
  const app = await submit(t, riceWith([]));
  assert.equal(app.$('result').querySelector('.advice'), null);
});

test('unknown fields, bad statuses and non-numeric ranges are skipped', async (t) => {
  const app = await submit(t, riceWith([
    item('nitrogen', 'low'),
    item('<img src=x onerror="window.pwned=1">', 'low'),
    item('phosphorus', 'weird'),
    item('potassium', 'ok', { low: 'a', high: null }),
  ]));
  assert.equal(rows(app).length, 1);
  assert.equal(app.$('result').querySelector('img'), null);
  assert.equal(app.window.pwned, undefined);
});

test('advice follows the selected language, including right after a language change', async (t) => {
  const app = await submit(t, riceWith([item('nitrogen', 'low'), ...ALL_OK.slice(1)]));
  app.page('applyLang')('hi');
  const hi = app.page('TRANSLATIONS').hi;
  assert.equal(app.$('result').querySelector('.advice-title').textContent, hi.advice_title);
  assert.equal(rows(app)[0].querySelector('.advice-name').textContent, hi.nitrogen);
  assert.equal(rows(app)[0].querySelector('.advice-badge').textContent, hi.status_low);
  assert.equal(rows(app)[0].querySelector('.advice-hint').textContent, hi.fert_n);
});

test('every language has all soil advice texts with the range placeholders', async (t) => {
  const app = await loadApp();
  t.after(() => app.close());
  const keys = ['advice_title', 'status_low', 'status_ok', 'status_high', 'advice_typical', 'fert_n',
    'fert_p', 'fert_k', 'ph_low', 'ph_high', 'advice_high', 'advice_ok', 'advice_note'];
  for (const [lang, dict] of Object.entries(app.page('TRANSLATIONS'))) {
    for (const key of keys) assert.ok(dict[key] && dict[key].trim(), `${lang}.${key}`);
    assert.ok(dict.advice_typical.includes('{min}') && dict.advice_typical.includes('{max}'), lang);
  }
});
