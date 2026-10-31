const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function harness(respond, options = {}) {
  const callbacks = {};
  const nodes = {};
  for (const key of ['status', 'countdown', 'retry', 'photo', 'qr', 'cancel', 'result']) {
    nodes[key] = {hidden: key !== 'qr', addEventListener(n, fn) {callbacks[key + '-' + n] = fn;}};
  }
  const root = {dataset: {state: 'PENDIENTE', stateUrl: options.url || '/estado/', expiresAt: '2099-01-01T00:00:00Z'},
    querySelector(selector) {return nodes[selector.slice(11, -1)];}};
  const timers = new Map();
  let nextTimer = 0;
  const requests = [];
  const document = {hidden: false, querySelectorAll: () => [root], addEventListener(n, fn) {callbacks[n] = fn;}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../static/js/vinculacion.js'), 'utf8'), {
    document, window: {location: {origin: 'https://eva.example'}, addEventListener(n, fn) {callbacks[n] = fn;}},
    URL, Date, AbortController,
    setTimeout(fn, delay) {timers.set(++nextTimer, {fn, delay});return nextTimer;},
    clearTimeout(id) {timers.delete(id);},
    async fetch(url, init) {requests.push({url, init});return respond();},
  });
  return {callbacks, nodes, root, timers, requests, document};
}
const flush = () => new Promise(resolve => setImmediate(resolve));
const response = (estado, extra = {}) => ({ok: true, status: 200, json: async () => ({estado, ...extra})});

test('solo confirma guardado con COMPLETADA y no carga imagen externa', async () => {
  const h = harness(() => response('COMPLETADA', {foto_url: 'https://otro.example/foto'}));await flush();
  assert.equal(h.root.dataset.state, 'COMPLETADA');assert.equal(h.nodes.qr.hidden, true);
  assert.equal(h.nodes.photo.hidden, true);assert.equal(h.timers.size, 0);
  assert.equal(h.requests[0].init.redirect, 'error');
});

test('pendiente consulta cada tres segundos y se pausa al ocultar', async () => {
  const h = harness(() => response('PENDIENTE'));await flush();
  assert.ok([...h.timers.values()].some(t => t.delay === 3000));
  assert.match(h.nodes.status.textContent, /no confirma/);
  h.document.hidden = true;h.callbacks.visibilitychange();assert.equal(h.timers.size, 0);
  h.document.hidden = false;h.callbacks.visibilitychange();await flush();assert.equal(h.requests.length, 2);
});

test('403 detiene; fallo de red permite reintento sin anunciar éxito', async () => {
  const denied = harness(() => ({ok: false, status: 403}));await flush();
  assert.equal(denied.nodes.retry.hidden, true);assert.equal(denied.timers.size, 0);
  let fail = true;
  const h = harness(() => {if (fail) throw new Error('offline');return response('EXPIRADA');});await flush();
  assert.equal(h.nodes.retry.hidden, false);assert.match(h.nodes.status.textContent, /conexión/);
  fail = false;h.callbacks['retry-click']();await flush();assert.equal(h.root.dataset.state, 'EXPIRADA');
});

test('rechaza consulta externa y estados desconocidos', async () => {
  const external = harness(() => response('COMPLETADA'), {url: 'https://otro.example/estado/'});await flush();
  assert.equal(external.requests.length, 0);
  const unknown = harness(() => response('INVENTADO'));await flush();
  assert.equal(unknown.root.dataset.state, 'PENDIENTE');assert.equal(unknown.nodes.retry.hidden, false);
});
