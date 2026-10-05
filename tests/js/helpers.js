'use strict';

/* Loads the real app/templates/index.html together with the real translations.js and app.js
   into jsdom, so the tests exercise exactly what the browser runs. */

const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (relative) => fs.readFileSync(path.join(ROOT, relative), 'utf8');

function renderTemplate() {
  return read('app/templates/index.html')
    .replace(/\{\{\s*asset_version\s*\}\}/g, 'test')
    .replace(/<script src="\/static\/js\/([^"?]+)[^"]*"[^>]*><\/script>/g,
      (_match, file) => `<script>${read(`app/static/js/${file}`)}</script>`);
}

function jsonResponse(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

const tick = (ms = 0) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitFor(condition, timeoutMs = 2000) {
  const start = Date.now();
  while (!condition()) {
    if (Date.now() - start > timeoutMs) throw new Error('waitFor timed out');
    await tick(5);
  }
}

/* options.fetch      mock fetch(url, init); defaults to a network failure
   options.storage    initial localStorage content; empty by default, which opens in English without any network call
   options.languages  navigator.languages */
async function loadApp(options = {}) {
  const storage = options.storage || {};
  const languages = options.languages || ['en-US', 'en'];
  const calls = [];
  const fetchMock = options.fetch || (async () => { throw new TypeError('network down'); });

  const dom = new JSDOM(renderTemplate(), {
    url: 'http://localhost/',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    beforeParse(window) {
      window.fetch = (url, init) => { calls.push({ url: String(url), init }); return fetchMock(url, init); };
      Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
      window.Element.prototype.scrollIntoView = function scrollIntoView() {};
      for (const [key, value] of Object.entries(storage)) window.localStorage.setItem(key, value);
    },
  });
  const { window } = dom;
  await new Promise((resolve) => {
    if (window.document.readyState === 'complete') resolve();
    else window.addEventListener('load', resolve);
  });
  await tick(10); // let the async init() finish

  const $ = (id) => window.document.getElementById(id);
  return {
    window,
    document: window.document,
    calls,
    $,
    /* Evaluates an expression in the page's global scope (app.js uses top-level const/function). */
    page: (expression) => window.eval(expression),
    fill(values) {
      for (const [name, value] of Object.entries(values)) $(name).value = String(value);
    },
    submit() {
      $('cropForm').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    },
    close: () => window.close(),
  };
}

const VALID_INPUT = {
  nitrogen: 90, phosphorus: 42, potassium: 43, temperature: 20.8, humidity: 82, pH: 6.5, rainfall: 200,
};

module.exports = { loadApp, jsonResponse, waitFor, tick, VALID_INPUT };
