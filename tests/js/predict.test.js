'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadApp, jsonResponse, waitFor, VALID_INPUT } = require('./helpers');

const RICE = {
  crop: 'rice',
  confidence: 0.9,
  top: [
    { crop: 'rice', confidence: 0.9 },
    { crop: 'maize', confidence: 0.07 },
    { crop: 'kidneybeans', confidence: 0.03 },
  ],
};

async function submitWith(t, response, options = {}) {
  const fetchMock = typeof response === 'function' ? response : async () => response;
  const app = await loadApp({ fetch: fetchMock, ...options });
  t.after(() => app.close());
  app.fill(VALID_INPUT);
  app.submit();
  await waitFor(() => !app.$('submitBtn').disabled);
  return app;
}

test('a successful prediction shows the top 3 crops with confidence', async (t) => {
  const app = await submitWith(t, jsonResponse(200, RICE));
  const result = app.$('result');
  assert.equal(result.hidden, false);
  assert.match(result.querySelector('.result-crop strong').textContent, /Rice/);
  assert.match(result.querySelector('.result-confidence').textContent, /90%/);
  assert.equal(result.querySelectorAll('.top-list li').length, 3);
  assert.equal(result.querySelectorAll('.crop-chip')[2].textContent, 'Kidney beans');
  assert.equal(result.querySelector('.result-warning'), null);
});

test('the request goes to /predict as JSON with all seven fields', async (t) => {
  const app = await submitWith(t, jsonResponse(200, RICE));
  const call = app.calls.find((c) => c.url === '/predict');
  assert.ok(call, 'no request to /predict');
  assert.equal(call.init.method, 'POST');
  assert.equal(call.init.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(call.init.body), Object.fromEntries(
    Object.entries(VALID_INPUT).map(([name, value]) => [name, String(value)])));
});

test('decimal values are sent unchanged', async (t) => {
  const app = await loadApp({ fetch: async () => jsonResponse(200, RICE) });
  t.after(() => app.close());
  app.fill({ ...VALID_INPUT, temperature: '20.8', pH: '6.55' });
  app.submit();
  await waitFor(() => !app.$('submitBtn').disabled);
  const body = JSON.parse(app.calls.find((c) => c.url === '/predict').init.body);
  assert.equal(body.temperature, '20.8');
  assert.equal(body.pH, '6.55');
});

test('the button is disabled and busy while the request runs', async (t) => {
  let release;
  const pending = new Promise((resolve) => { release = resolve; });
  const app = await loadApp({ fetch: async () => { await pending; return jsonResponse(200, RICE); } });
  t.after(() => app.close());
  app.fill(VALID_INPUT);
  app.submit();
  assert.equal(app.$('submitBtn').disabled, true);
  assert.equal(app.$('submitBtn').getAttribute('aria-busy'), 'true');
  release();
  await waitFor(() => !app.$('submitBtn').disabled);
  assert.equal(app.$('submitBtn').getAttribute('aria-busy'), 'false');
  assert.equal(app.$('submitBtn').textContent, app.page('TRANSLATIONS').en.btn);
});

test('low confidence shows a warning', async (t) => {
  const app = await submitWith(t, jsonResponse(200, {
    crop: 'rice', confidence: 0.3, top: [{ crop: 'rice', confidence: 0.3 }],
  }));
  assert.equal(app.$('result').querySelector('.result-warning').textContent,
    app.page('TRANSLATIONS').en.low_confidence);
});

test('server warnings are listed as plain text', async (t) => {
  const app = await submitWith(t, jsonResponse(200, {
    ...RICE, warnings: [{ message: 'pH looks unusual' }, { message: 'Rainfall is very high' }],
  }));
  const items = [...app.$('result').querySelectorAll('.result-warning li')].map((li) => li.textContent);
  assert.deepEqual(items, ['pH looks unusual', 'Rainfall is very high']);
});

test('tiny confidences are shown as <1%, not 0%', async (t) => {
  const app = await loadApp();
  t.after(() => app.close());
  assert.equal(app.page('percent')(0.004), '<1%');
  assert.equal(app.page('percent')(0), '0%');
  assert.equal(app.page('percent')(0.876), '88%');
});

test('422 shows an error under each bad field and focuses the first one', async (t) => {
  const app = await submitWith(t, jsonResponse(422, {
    fields: { pH: 'must be between 0 and 14', nitrogen: 'required' },
  }));
  assert.equal(app.$('err-nitrogen').textContent, 'Required');
  assert.equal(app.$('err-nitrogen').hidden, false);
  assert.equal(app.$('err-pH').textContent, 'Must be between 0 and 14');
  assert.equal(app.$('nitrogen').getAttribute('aria-invalid'), 'true');
  assert.equal(app.$('pH').getAttribute('aria-invalid'), 'true');
  assert.equal(app.$('humidity').getAttribute('aria-invalid'), 'false');
  assert.equal(app.document.activeElement.id, 'nitrogen'); // form order, not response order
  assert.equal(app.$('result').className, 'result status-error');
  assert.equal(app.$('result').textContent, app.page('TRANSLATIONS').en.error_fix_inputs);
});

test('field errors are translated, including the range placeholders', async (t) => {
  const app = await loadApp({
    storage: { cs_lang_mode: 'choose', cs_lang: 'de' },
    fetch: async () => jsonResponse(422, { fields: { rainfall: 'must be between 0 and 5000', humidity: 'required', pH: 'not a number' } }),
  });
  t.after(() => app.close());
  app.fill(VALID_INPUT);
  app.submit();
  await waitFor(() => !app.$('submitBtn').disabled);
  const de = app.page('TRANSLATIONS').de;
  assert.equal(app.$('err-rainfall').textContent, de.err_range.replace('{min}', '0').replace('{max}', '5000'));
  assert.equal(app.$('err-humidity').textContent, de.err_required);
  assert.equal(app.$('err-pH').textContent, de.err_number);
});

test('typing in a field clears its error', async (t) => {
  const app = await submitWith(t, jsonResponse(422, { fields: { nitrogen: 'required' } }));
  assert.equal(app.$('err-nitrogen').hidden, false);
  app.$('nitrogen').dispatchEvent(new app.window.Event('input', { bubbles: true }));
  assert.equal(app.$('err-nitrogen').hidden, true);
  assert.equal(app.$('nitrogen').getAttribute('aria-invalid'), 'false');
});

test('a successful retry clears earlier field errors', async (t) => {
  const responses = [jsonResponse(422, { fields: { nitrogen: 'required' } }), jsonResponse(200, RICE)];
  const app = await loadApp({ fetch: async () => responses.shift() });
  t.after(() => app.close());
  app.fill(VALID_INPUT);
  for (let i = 0; i < 2; i += 1) {
    app.submit();
    await waitFor(() => !app.$('submitBtn').disabled);
  }
  assert.equal(app.$('err-nitrogen').hidden, true);
  assert.match(app.$('result').textContent, /Rice/);
});

test('a server error shows the generic message', async (t) => {
  const app = await submitWith(t, jsonResponse(500, {}));
  assert.equal(app.$('result').textContent, app.page('TRANSLATIONS').en.error_generic);
  assert.equal(app.$('result').className, 'result status-error');
});

test('a network failure shows the connection message', async (t) => {
  const app = await submitWith(t, async () => { throw new TypeError('Failed to fetch'); });
  assert.equal(app.$('result').textContent, app.page('TRANSLATIONS').en.error_network);
});

test('a timeout shows the timeout message', async (t) => {
  const app = await submitWith(t, async () => {
    throw Object.assign(new Error('aborted'), { name: 'AbortError' });
  });
  assert.equal(app.$('result').textContent, app.page('TRANSLATIONS').en.error_timeout);
});

test('the result is re-rendered in the new language after a language change', async (t) => {
  const app = await submitWith(t, jsonResponse(200, RICE));
  app.page('applyLang')('es');
  assert.match(app.$('result').querySelector('.result-confidence').textContent,
    new RegExp(`^${app.page('TRANSLATIONS').es.confidence}: 90%`));
});

test('crop names from the server are never parsed as HTML', async (t) => {
  const evil = '<img src=x onerror="window.pwned=1">';
  const app = await submitWith(t, jsonResponse(200, {
    crop: evil, confidence: 0.9, top: [{ crop: evil, confidence: 0.9 }],
  }));
  assert.equal(app.$('result').querySelector('img'), null);
  assert.ok(app.$('result').textContent.includes('onerror'));
  assert.equal(app.window.pwned, undefined);
});

test('warning messages from the server are never parsed as HTML', async (t) => {
  const app = await submitWith(t, jsonResponse(200, {
    ...RICE, warnings: [{ message: '<b id="injected">x</b>' }],
  }));
  assert.equal(app.document.getElementById('injected'), null);
});
