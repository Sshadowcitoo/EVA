// Pruebas de la revisión de Cocina en static/js/analisis.js, sin dependencias.
// Ejecutar con: node --test tests/frontend/revision.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const CODIGO = fs.readFileSync(path.join(__dirname, "..", "..", "static", "js", "analisis.js"), "utf8");

function boton(valor, { requiereMotivo = false, deshabilitado = false } = {}) {
const atributos = new Set();
if (requiereMotivo) { atributos.add("data-requiere-motivo"); }
if (deshabilitado) { atributos.add("disabled"); }
return { value: valor, disabled: deshabilitado, hasAttribute: (n) => atributos.has(n) };
}

function armar({ formulario = true, rectificar = false, confirmarDeshabilitado = false } = {}) {
const oyentes = {};
const temporizadores = [];
const motivo = {
value: "", atributos: {}, enfocado: 0,
setAttribute(n, v) { this.atributos[n] = v; },
removeAttribute(n) { delete this.atributos[n]; },
focus() { this.enfocado += 1; },
};
const error = { hidden: true };
const estado = { textContent: "" };
const selector = { value: "", addEventListener(n, fn) { oyentes["selector-" + n] = fn; } };
const sugerencias = { hidden: true, querySelector: () => selector };
const botones = [
boton("CONFIRMADO", { deshabilitado: confirmarDeshabilitado }),
boton("NO_CONCLUYENTE", { requiereMotivo: true }),
boton("RECHAZADO", { requiereMotivo: true }),
];
const elementos = {
"#motivo-revision": motivo, "[data-motivo-error]": error, "[data-revision-estado]": estado,
"[data-motivo-sugerencias]": sugerencias,
};
const form = {
querySelector: (s) => elementos[s] || null,
querySelectorAll: () => botones,
hasAttribute: (n) => n === "data-rectificar" && rectificar,
addEventListener(n, fn) { oyentes["form-" + n] = fn; },
};
const sim = { motivo, error, estado, selector, sugerencias, botones, oyentes };
vm.runInNewContext(CODIGO, {
document: {
    querySelector: (s) => (s === "[data-revision-form]" && formulario ? form : null),
    addEventListener() {},
},
window: {
    setTimeout(fn) { temporizadores.push(fn); return temporizadores.length; },
    clearTimeout() {},
    addEventListener(n, fn) { oyentes["win-" + n] = fn; },
    location: { reload() {} },
},
fetch: () => new Promise(() => {}),
AbortController,
Date,
});
sim.enviar = (valor) => {
const evento = {
    submitter: botones.find((b) => b.value === valor),
    prevenido: false,
    preventDefault() { this.prevenido = true; },
};
oyentes["form-submit"](evento);
return evento;
};
sim.vaciarTemporizadores = () => { while (temporizadores.length) { temporizadores.shift()(); } };
return sim;
}

test("sin formulario de revisión no hace nada", () => {
const sim = armar({ formulario: false });
assert.equal(Object.keys(sim.oyentes).length, 0);
});

test("muestra la lista de motivos frecuentes solo cuando hay JavaScript", () => {
const sim = armar();
assert.equal(sim.sugerencias.hidden, false);
});

test("elegir un motivo frecuente lo copia al campo de motivo; la opción vacía no lo borra", () => {
const sim = armar();
sim.selector.value = "Máscara incorrecta";
sim.oyentes["selector-change"]();
assert.equal(sim.motivo.value, "Máscara incorrecta");
sim.selector.value = "";
sim.oyentes["selector-change"]();
assert.equal(sim.motivo.value, "Máscara incorrecta");
});

test("marcar incorrecto sin motivo se bloquea, explica y lleva el foco al motivo", () => {
const sim = armar();
const evento = sim.enviar("RECHAZADO");
assert.equal(evento.prevenido, true);
assert.equal(sim.error.hidden, false);
assert.equal(sim.motivo.atributos["aria-invalid"], "true");
assert.equal(sim.motivo.enfocado, 1);
});

test("un motivo de solo espacios cuenta como vacío", () => {
const sim = armar();
sim.motivo.value = "   ";
assert.equal(sim.enviar("NO_CONCLUYENTE").prevenido, true);
});

test("marcar no concluyente con motivo pasa, avisa y evita más envíos", () => {
const sim = armar();
sim.motivo.value = "Fotografía dudosa";
const evento = sim.enviar("NO_CONCLUYENTE");
assert.equal(evento.prevenido, false);
assert.equal(sim.error.hidden, true);
assert.match(sim.estado.textContent, /Guardando/);
sim.vaciarTemporizadores();
assert.ok(sim.botones.every((b) => b.disabled));
});

test("confirmar por primera vez no exige motivo", () => {
const sim = armar();
assert.equal(sim.enviar("CONFIRMADO").prevenido, false);
});

test("al rectificar, hasta confirmar exige motivo", () => {
const sim = armar({ rectificar: true });
assert.equal(sim.enviar("CONFIRMADO").prevenido, true);
sim.motivo.value = "Revisé de nuevo las fotos";
assert.equal(sim.enviar("CONFIRMADO").prevenido, false);
});

test("un segundo envío mientras guarda se descarta", () => {
const sim = armar();
assert.equal(sim.enviar("CONFIRMADO").prevenido, false);
assert.equal(sim.enviar("CONFIRMADO").prevenido, true);
});

test("al volver con el botón atrás se restaura el formulario y Confirmar sigue bloqueado si lo estaba", () => {
const sim = armar({ confirmarDeshabilitado: true });
sim.motivo.value = "ok";
sim.enviar("RECHAZADO");
sim.vaciarTemporizadores();
assert.ok(sim.botones.every((b) => b.disabled));
sim.oyentes["win-pageshow"]();
assert.equal(sim.botones[0].disabled, true);   // Confirmar: bloqueado desde el servidor
assert.equal(sim.botones[1].disabled, false);
assert.equal(sim.botones[2].disabled, false);
assert.equal(sim.estado.textContent, "");
assert.equal(sim.enviar("RECHAZADO").prevenido, false);
});
