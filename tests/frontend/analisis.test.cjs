// Pruebas de static/js/analisis.js sin dependencias: se simulan document, window y fetch.
// Ejecutar con: node --test tests/frontend/analisis.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const CODIGO = fs.readFileSync(path.join(__dirname, "..", "..", "static", "js", "analisis.js"), "utf8");

function armar({ aviso = true, url = "/analisis/1/estado/" } = {}) {
let reloj = 0;
let siguienteId = 1;
const temporizadores = new Map();
const oyentes = {};
const sim = { recargas: 0, llamadas: [], oculto: false, escuchas: {} };
const mensaje = { textContent: "Esta pantalla se actualiza sola." };
const boton = { hidden: true, addEventListener(n, fn) { oyentes["boton-" + n] = fn; } };
const elemento = aviso ? {
getAttribute: (n) => ({ "data-estado-url": url, "data-estado-actual": "EN_PROCESO" })[n],
querySelector: (s) => (s === "[data-estado-mensaje]" ? mensaje : s === "[data-estado-reintentar]" ? boton : null),
} : null;
const documento = {
get hidden() { return sim.oculto; },
querySelector: () => elemento,
addEventListener(n, fn) { oyentes["doc-" + n] = fn; },
};
const ventana = {
location: { reload() { sim.recargas += 1; } },
setTimeout(fn, ms) { const id = siguienteId++; temporizadores.set(id, { fn, ms, en: reloj + ms }); return id; },
clearTimeout(id) { temporizadores.delete(id); },
addEventListener(n, fn) { oyentes["win-" + n] = fn; },
};
// Cada llamada a fetch queda registrada; la prueba decide cómo responde.
const respuestas = [];
function fetchFalso(u, opciones) {
const llamada = { url: u, opciones };
llamada.promesa = new Promise((resolver, rechazar) => {
    llamada.resolver = resolver;
    llamada.rechazar = rechazar;
    opciones.signal.addEventListener("abort", () => rechazar(new Error("abortada")));
});
sim.llamadas.push(llamada);
respuestas.push(llamada);
return llamada.promesa;
}
vm.runInNewContext(CODIGO, {
document: documento, window: ventana, fetch: fetchFalso, AbortController,
Date: { now: () => reloj },
});
sim.mensaje = mensaje;
sim.boton = boton;
sim.oyentes = oyentes;
sim.pendientes = () => temporizadores.size;
sim.avanzar = async (ms) => {
const objetivo = reloj + ms;
for (;;) {
    const proximos = [...temporizadores.entries()].filter(([, t]) => t.en <= objetivo).sort((a, b) => a[1].en - b[1].en);
    if (!proximos.length) { break; }
    const [id, t] = proximos[0];
    temporizadores.delete(id);
    reloj = t.en;
    t.fn();
    await new Promise((r) => setImmediate(r));
}
reloj = objetivo;
};
sim.responder = async (llamada, { status = 200, datos = {}, json = null } = {}) => {
llamada.resolver({ status, ok: status >= 200 && status < 300, json: json || (() => Promise.resolve(datos)) });
await new Promise((r) => setImmediate(r));
};
sim.fallarRed = async (llamada) => { llamada.rechazar(new TypeError("red")); await new Promise((r) => setImmediate(r)); };
return sim;
}

test("sin aviso en la página no hace nada", () => {
const sim = armar({ aviso: false });
assert.equal(sim.pendientes(), 0);
});

test("consulta a los 3 segundos con mismo origen, sin caché y sin seguir redirecciones", async () => {
const sim = armar();
await sim.avanzar(2999);
assert.equal(sim.llamadas.length, 0);
await sim.avanzar(1);
assert.equal(sim.llamadas.length, 1);
const { url, opciones } = sim.llamadas[0];
assert.equal(url, "/analisis/1/estado/");
assert.equal(opciones.credentials, "same-origin");
assert.equal(opciones.cache, "no-store");
assert.equal(opciones.redirect, "error");
assert.ok(opciones.signal);
});

test("si el estado válido cambia, recarga la página", async () => {
const sim = armar();
await sim.avanzar(3000);
await sim.responder(sim.llamadas[0], { datos: { estado: "COMPLETADO" } });
assert.equal(sim.recargas, 1);
});

test("si el estado sigue igual no recarga y vuelve a consultar", async () => {
const sim = armar();
await sim.avanzar(3000);
await sim.responder(sim.llamadas[0], { datos: { estado: "EN_PROCESO" } });
assert.equal(sim.recargas, 0);
await sim.avanzar(3000);
assert.equal(sim.llamadas.length, 2);
});

test("un estado desconocido no recarga: se detiene y ofrece reintento manual", async () => {
const sim = armar();
await sim.avanzar(3000);
await sim.responder(sim.llamadas[0], { datos: { estado: "INVENTADO" } });
assert.equal(sim.recargas, 0);
assert.equal(sim.pendientes(), 0);
assert.equal(sim.boton.hidden, false);
assert.match(sim.mensaje.textContent, /No se reconoció el estado/);
});

test("una respuesta sin estado tampoco recarga", async () => {
const sim = armar();
await sim.avanzar(3000);
await sim.responder(sim.llamadas[0], { datos: {} });
assert.equal(sim.recargas, 0);
assert.equal(sim.boton.hidden, false);
});

test("pérdida de sesión (401 o 403) detiene la consulta y lo explica", async () => {
for (const status of [401, 403]) {
const sim = armar();
await sim.avanzar(3000);
await sim.responder(sim.llamadas[0], { status });
assert.equal(sim.recargas, 0);
assert.equal(sim.pendientes(), 0);
assert.match(sim.mensaje.textContent, /sesión/);
assert.equal(sim.boton.hidden, false);
}
});

test("una redirección (el navegador la rechaza) cuenta como fallo y no se sigue", async () => {
const sim = armar();
await sim.avanzar(3000);
await sim.fallarRed(sim.llamadas[0]);
assert.equal(sim.recargas, 0);
assert.equal(sim.pendientes(), 1); // sigue intentando
});

test("tres fallos seguidos detienen la consulta y muestran el reintento manual", async () => {
const sim = armar();
for (let i = 0; i < 3; i += 1) {
await sim.avanzar(3000);
await sim.responder(sim.llamadas[i], { status: 500 });
}
assert.equal(sim.llamadas.length, 3);
assert.equal(sim.pendientes(), 0);
assert.equal(sim.boton.hidden, false);
assert.match(sim.mensaje.textContent, /No se pudo consultar/);
});

test("un fallo aislado no detiene la consulta", async () => {
const sim = armar();
await sim.avanzar(3000);
await sim.responder(sim.llamadas[0], { status: 500 });
await sim.avanzar(3000);
await sim.responder(sim.llamadas[1], { datos: { estado: "EN_PROCESO" } });
await sim.avanzar(3000);
assert.equal(sim.llamadas.length, 3);
});

test("una petición colgada se aborta a los 5 segundos", async () => {
const sim = armar();
await sim.avanzar(3000);
assert.equal(sim.llamadas[0].opciones.signal.aborted, false);
await sim.avanzar(4999);
assert.equal(sim.llamadas[0].opciones.signal.aborted, false);
await sim.avanzar(1);
assert.equal(sim.llamadas[0].opciones.signal.aborted, true);
assert.equal(sim.pendientes(), 1); // cuenta como fallo y reprograma
});

test("el plazo total corta la consulta aunque haya peticiones lentas", async () => {
const sim = armar();
for (let i = 0; i < 40 && sim.boton.hidden; i += 1) {
await sim.avanzar(3000);
if (sim.llamadas.length && !sim.llamadas[sim.llamadas.length - 1].resuelta) {
    sim.llamadas[sim.llamadas.length - 1].resuelta = true;
    await sim.responder(sim.llamadas[sim.llamadas.length - 1], { datos: { estado: "EN_PROCESO" } });
}
}
assert.equal(sim.pendientes(), 0);
assert.equal(sim.boton.hidden, false);
assert.match(sim.mensaje.textContent, /Recarga la página/);
});

test("al ocultar la página aborta la petición y pausa; al volver reanuda", async () => {
const sim = armar();
await sim.avanzar(3000);
sim.oculto = true;
sim.oyentes["doc-visibilitychange"]();
assert.equal(sim.llamadas[0].opciones.signal.aborted, true);
assert.equal(sim.pendientes(), 0);
await sim.avanzar(10000);
assert.equal(sim.llamadas.length, 1);
sim.oculto = false;
sim.oyentes["doc-visibilitychange"]();
await sim.avanzar(3000);
assert.equal(sim.llamadas.length, 2);
});

test("al cerrar o salir de la página detiene todo", async () => {
const sim = armar();
await sim.avanzar(3000);
sim.oyentes["win-pagehide"]();
assert.equal(sim.llamadas[0].opciones.signal.aborted, true);
assert.equal(sim.pendientes(), 0);
await sim.avanzar(10000);
assert.equal(sim.llamadas.length, 1);
});

test("el botón de reintento manual vuelve a consultar", async () => {
const sim = armar();
await sim.avanzar(3000);
await sim.responder(sim.llamadas[0], { status: 403 });
assert.equal(sim.boton.hidden, false);
sim.oyentes["boton-click"]();
assert.equal(sim.boton.hidden, true);
assert.equal(sim.llamadas.length, 2);
});