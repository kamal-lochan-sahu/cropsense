'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadApp, jsonResponse, tick } = require('./helpers');

const GUIDE = {
  season: 'Kharif, June to July',
  soil: 'Clay loam',
  water: 'Keep fields flooded',
  fertilizer: 'Split NPK doses',
  pests: 'Watch for stem borer',
  harvest: 'About 120 days',
  tip: 'Transplant young seedlings',
};

const guideResponse = (guide = GUIDE) => jsonResponse(200, { guide: JSON.stringify(guide) });

async function withApp(t, options) {
  const app = await loadApp(options);
  t.after(() => app.close());
  return app;
}

/* ── Growing guide ─────────────────────────────────────────────────── */

test('the guide shows six labelled rows, a tip and the AI notice', async (t) => {
  const app = await withApp(t, { fetch: async () => guideResponse() });
  await app.page('showGuide')('rice');
  const panel = app.$('learn-panel');
  assert.equal(panel.hidden, false);
  assert.equal(panel.querySelectorAll('.guide-row').length, 6);
  assert.deepEqual(
    [...panel.querySelectorAll('.guide-row strong')].map((n) => n.textContent),
    ['Season', 'Soil', 'Water', 'Fertilizer', 'Pests', 'Harvest']);
  assert.ok(panel.textContent.includes(GUIDE.season));
  assert.ok(panel.querySelector('.learn-tip').textContent.includes(GUIDE.tip));
  assert.equal(panel.querySelector('.ai-credit').textContent, app.page('TRANSLATIONS').en.ai_credit);
  assert.match(panel.querySelector('h2').textContent, /Rice/);
});

test('the guide request carries the crop and the current language', async (t) => {
  const app = await withApp(t, { fetch: async () => guideResponse() });
  app.page('applyLang')('hi');
  await app.page('showGuide')('wheat');
  const call = app.calls.find((c) => c.url === '/crop-guide');
  assert.deepEqual(JSON.parse(call.init.body), { crop: 'wheat', lang: 'hi' });
  assert.equal(app.$('learn-panel').querySelector('.guide-row strong').textContent,
    app.page('GUIDE_LABELS').hi.season);
});

test('rows the model left out are skipped', async (t) => {
  const app = await withApp(t, { fetch: async () => guideResponse({ season: 'Rabi', soil: '' }) });
  await app.page('showGuide')('wheat');
  assert.equal(app.$('learn-panel').querySelectorAll('.guide-row').length, 1);
  assert.equal(app.$('learn-panel').querySelector('.learn-tip'), null);
});

test('guide text from the model is never parsed as HTML', async (t) => {
  const app = await withApp(t, {
    fetch: async () => guideResponse({ ...GUIDE, season: '<img src=x onerror="window.pwned=1">' }),
  });
  await app.page('showGuide')('rice');
  assert.equal(app.$('learn-panel').querySelector('img'), null);
  assert.equal(app.window.pwned, undefined);
});

test('a loading state is shown while the guide is generated', async (t) => {
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const app = await withApp(t, { fetch: async () => { await pending; return guideResponse(); } });
  const done = app.page('showGuide')('rice');
  const loading = app.$('learn-panel').querySelector('.ai-loading');
  assert.ok(loading);
  assert.equal(loading.textContent, app.page('GUIDE_LABELS').en.loading);
  release();
  await done;
  assert.equal(app.$('learn-panel').querySelector('.ai-loading'), null);
});

test('a failed guide shows the error and fallback links that open safely', async (t) => {
  const app = await withApp(t, { fetch: async () => jsonResponse(502, { error: 'AI service unavailable' }) });
  await app.page('showGuide')('kidneybeans');
  const panel = app.$('learn-panel');
  assert.match(panel.querySelector('.ai-error').textContent, new RegExp(app.page('GUIDE_LABELS').en.error));
  const links = [...panel.querySelectorAll('.learn-links a')];
  assert.equal(links.length, 3);
  for (const link of links) {
    assert.equal(link.target, '_blank');
    assert.match(link.rel, /noopener/);
    assert.ok(link.href.startsWith('https://'));
  }
});

test('a guide that is not valid JSON falls back to the error view', async (t) => {
  const app = await withApp(t, { fetch: async () => jsonResponse(200, { guide: 'not json' }) });
  await app.page('showGuide')('rice');
  assert.ok(app.$('learn-panel').querySelector('.ai-error'));
});

test('a network failure falls back to the error view', async (t) => {
  const app = await withApp(t);
  await app.page('showGuide')('rice');
  assert.ok(app.$('learn-panel').querySelector('.ai-error'));
});

test('the close button hides the guide', async (t) => {
  const app = await withApp(t, { fetch: async () => guideResponse() });
  await app.page('showGuide')('rice');
  app.$('learn-panel').querySelector('.close-btn').click();
  assert.equal(app.$('learn-panel').hidden, true);
  assert.equal(app.$('learn-panel').children.length, 0);
});

test('a slow response is ignored after the guide was closed', async (t) => {
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const app = await withApp(t, { fetch: async () => { await pending; return guideResponse(); } });
  const done = app.page('showGuide')('rice');
  app.page('hideGuide')();
  release();
  await done;
  assert.equal(app.$('learn-panel').hidden, true);
  assert.equal(app.$('learn-panel').children.length, 0);
});

test('only the latest guide request wins', async (t) => {
  const releases = [];
  const app = await withApp(t, {
    fetch: async () => {
      await new Promise((resolve) => releases.push(resolve));
      return guideResponse();
    },
  });
  const first = app.page('showGuide')('rice');
  const second = app.page('showGuide')('maize');
  releases[1]();
  await second;
  releases[0]();
  await first;
  assert.match(app.$('learn-panel').querySelector('h2').textContent, /Maize/);
});

/* ── Input tabs ────────────────────────────────────────────────────── */

test('tabs switch the visible panel and aria-selected', async (t) => {
  const app = await withApp(t);
  app.$('mode-report').click();
  assert.ok(app.$('mode-panel-report').classList.contains('active'));
  assert.ok(!app.$('mode-panel-manual').classList.contains('active'));
  assert.equal(app.$('mode-report').getAttribute('aria-selected'), 'true');
  assert.equal(app.$('mode-manual').getAttribute('aria-selected'), 'false');
});

test('choosing a soil report file shows its name', async (t) => {
  const app = await withApp(t);
  const input = app.$('soil-report-file');
  Object.defineProperty(input, 'files', { value: [{ name: 'soil-2026.pdf' }], configurable: true });
  input.dispatchEvent(new app.window.Event('change'));
  assert.equal(app.$('report-filename').textContent, 'soil-2026.pdf');
  assert.equal(app.$('report-note').style.display, 'block');
});

/* ── Sensor demo ───────────────────────────────────────────────────── */

test('the sensor demo shows seven readings inside the demo ranges', async (t) => {
  const app = await withApp(t);
  app.$('mode-sensor').click();
  app.$('sensor-start').click();
  assert.equal(app.$('sensor-readout').querySelectorAll('.sensor-cell').length, 7);
  const values = JSON.parse(app.$('sensor-readout').dataset.values);
  const ranges = app.page('SENSOR_RANGES');
  for (const [name, [low, high]] of Object.entries(ranges)) {
    assert.ok(Number(values[name]) >= low - 0.5 && Number(values[name]) <= high + 0.5, `${name}=${values[name]}`);
  }
  app.page('stopSensorDemo')();
});

test('using a sensor reading fills the form and returns to the manual tab', async (t) => {
  const app = await withApp(t);
  app.$('mode-sensor').click();
  app.$('sensor-start').click();
  const values = JSON.parse(app.$('sensor-readout').dataset.values);
  app.$('sensor-use').click();
  for (const [name, value] of Object.entries(values)) assert.equal(app.$(name).value, value);
  assert.ok(app.$('mode-panel-manual').classList.contains('active'));
  assert.equal(app.page('sensorTimer'), null);
});

test('using a reading before the demo has started does nothing', async (t) => {
  const app = await withApp(t);
  app.$('sensor-use').click();
  assert.equal(app.$('nitrogen').value, '');
});

test('leaving the sensor tab stops the live feed', async (t) => {
  const app = await withApp(t);
  app.$('mode-sensor').click();
  app.$('sensor-start').click();
  assert.notEqual(app.page('sensorTimer'), null);
  app.$('mode-manual').click();
  assert.equal(app.page('sensorTimer'), null);
});

/* ── Offline banner ────────────────────────────────────────────────── */

test('the offline banner follows the connection state', async (t) => {
  const app = await withApp(t);
  assert.equal(app.$('offline-banner').hidden, true);
  const setOnline = (value) => Object.defineProperty(app.window.navigator, 'onLine', { value, configurable: true });

  setOnline(false);
  app.window.dispatchEvent(new app.window.Event('offline'));
  assert.equal(app.$('offline-banner').hidden, false);

  setOnline(true);
  app.window.dispatchEvent(new app.window.Event('online'));
  assert.equal(app.$('offline-banner').hidden, true);
  await tick();
});
