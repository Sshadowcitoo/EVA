const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function harness() {
  const callbacks = {};
  const input = {files: [], value: '', setAttribute() {}, addEventListener(n, fn) { callbacks[n] = fn; }, click() {}};
  const preview = {removeAttribute() {}};
  const enhancement = {};
  const status = {dataset: {}};
  const submit = {disabled: false};
  const repeat = {addEventListener(n, fn) {callbacks.repeat = fn;}};
  const elements = {'input[type="file"]': input, '[data-photo-preview]': preview,
    '[data-photo-enhancement]': enhancement, '[data-photo-status]': status,
    '[data-photo-submit]': submit, '[data-photo-repeat]': repeat};
  const form = {dataset: {maxBytes: '10485760', maxPixels: '20000000'}, querySelector(s) {return elements[s];},
    addEventListener(n, fn) {callbacks['form-' + n] = fn;}};
  const images = [];
  const revoked = [];
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../static/js/captura.js'), 'utf8'), {
    document: {querySelectorAll: () => [form]},
    window: {addEventListener(n, fn) {callbacks['window-' + n] = fn;}},
    URL: {createObjectURL: () => 'blob:local', revokeObjectURL: u => revoked.push(u)},
    Image: class {constructor() {images.push(this);}},
  });
  return {callbacks, input, preview, status, submit, images, revoked};
}

test('no permite enviar sin archivo ni declara éxito al previsualizar', () => {
  const h = harness(); let prevented = false;
  h.callbacks['form-submit']({preventDefault() {prevented = true;}});
  assert.equal(prevented, true);
  h.input.files = [{type: 'image/jpeg', size: 100}]; h.callbacks.change();
  assert.equal(h.submit.disabled, true);
  Object.assign(h.images[0], {naturalWidth: 100, naturalHeight: 100}); h.images[0].onload();
  assert.equal(h.submit.disabled, false);
  assert.match(h.status.textContent, /Todavía no está guardada/);
});

test('rechaza tamaño, píxeles y archivo ilegible; repetir invalida la foto', () => {
  const h = harness();
  h.input.files = [{type: 'image/png', size: 10485761}]; h.callbacks.change();
  assert.equal(h.images.length, 0); assert.equal(h.submit.disabled, true);
  h.input.files = [{type: 'image/png', size: 100}]; h.callbacks.change();
  Object.assign(h.images[0], {naturalWidth: 10000, naturalHeight: 10000});h.images[0].onload();
  assert.equal(h.submit.disabled, true);assert.match(h.status.textContent, /píxeles/);
  h.callbacks.change();h.images[1].onerror();assert.match(h.status.textContent, /No se puede abrir/);
  h.callbacks.repeat();assert.equal(h.submit.disabled, true);assert.ok(h.revoked.length > 0);
});

test('una carga anterior no habilita la foto elegida posteriormente', () => {
  const h = harness();h.input.files = [{type: 'image/jpeg', size: 100}];h.callbacks.change();
  h.input.files = [{type: 'text/html', size: 100}];h.callbacks.change();
  Object.assign(h.images[0], {naturalWidth: 100, naturalHeight: 100});h.images[0].onload();
  assert.equal(h.submit.disabled, true);assert.equal(h.preview.hidden, true);
});
