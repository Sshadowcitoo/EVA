const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function harness({supported = true} = {}) {
  const events = {};
  const node = (id) => ({hidden: false, disabled: false, addEventListener(event, callback) {events[id + event] = callback;}});
  const start = node('start'), take = node('take'), close = node('close'), status = {};
  const video = {...node('video'), videoWidth: 640, videoHeight: 480, readyState: 2, async play() {}};
  let blobCallback;
  const canvas = {getContext: () => ({drawImage() {}}), toBlob(callback) {blobCallback = callback;}};
  const input = {...node('input'), files: [], dispatchEvent(event) {events['input' + event.type]?.();}};
  const nodes = {'[data-camera-start]': start, '[data-camera-take]': take, '[data-camera-stop]': close,
    '[data-camera-status]': status, '[data-camera-video]': video, '[data-camera-canvas]': canvas};
  const root = {querySelector: (selector) => nodes[selector]};
  const form = {...node('form'), querySelector: (selector) => selector === '[data-photo-camera]' ? root : input};
  const document = {hidden: false, querySelectorAll: () => [form], addEventListener(event, callback) {events['document' + event] = callback;}};
  let request, resolve, reject, constraints, stopped = 0;
  const stream = {getTracks: () => [{stop() {stopped++;}}]};
  const navigator = {mediaDevices: supported ? {getUserMedia(value) {
    constraints = value;
    request = new Promise((yes, no) => {resolve = yes; reject = no;});
    return request;
  }} : undefined};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../static/js/camara_captura.js'), 'utf8'), {
    document, navigator, window: {isSecureContext: true, addEventListener(event, callback) {events['window' + event] = callback;}},
    DataTransfer: class {constructor() {this.files = []; this.items = {add: (file) => this.files.push(file)};}},
    File: class {constructor(content, name, options) {this.name = name; this.type = options.type;}},
    Event: class {constructor(type) {this.type = type;}},
  });
  return {events, input, video, take, status, stream, document,
    grant() {resolve(stream);}, deny() {reject({name: 'NotAllowedError'});},
    encode() {blobCallback({size: 100, type: 'image/jpeg'});},
    get requested() {return !!request;}, get constraints() {return constraints;}, get stopped() {return stopped;}};
}

test('no abre cámara automáticamente ni solicita audio; tomar no guarda en servidor', async () => {
  const h = harness();
  assert.equal(h.requested, false);
  const opening = h.events.startclick(); h.grant(); await opening;
  assert.equal(h.constraints.audio, false);
  assert.equal(h.video.srcObject, h.stream);
  assert.match(h.status.textContent, /Todavía no se ha guardado/);
  h.events.takeclick(); h.encode();
  assert.equal(h.input.files[0].type, 'image/jpeg');
  assert.equal(h.video.srcObject, null);
  assert.equal(h.stopped, 1);
  assert.match(h.status.textContent, /después pulsa Guardar/);
});

test('cerrar mientras llega permiso descarta el stream tardío y apaga sus pistas', async () => {
  const h = harness();
  const opening = h.events.startclick(); h.events.closeclick(); h.grant(); await opening;
  assert.equal(h.stopped, 1);
  assert.equal(h.video.srcObject, null);
});

test('ocultar pestaña durante codificación descarta foto y apaga cámara', async () => {
  const h = harness();
  const opening = h.events.startclick(); h.grant(); await opening;
  h.events.takeclick();
  h.document.hidden = true; h.events.documentvisibilitychange(); h.encode();
  assert.equal(h.input.files.length, 0);
  assert.equal(h.stopped, 1);
});

test('permiso denegado o navegador sin soporte explica alternativa sin anunciar éxito', async () => {
  const h = harness();
  const opening = h.events.startclick(); h.deny(); await opening;
  assert.match(h.status.textContent, /No se concedió/);
  assert.equal(h.input.files.length, 0);
  const fallback = harness({supported: false});
  await fallback.events.startclick();
  assert.match(fallback.status.textContent, /selecciona un archivo/);
  assert.equal(fallback.requested, false);
});
