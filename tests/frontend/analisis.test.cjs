// Pruebas de static/js/analisis.js sin dependencias: se simula document, window y fetch.
// Ejecutar con: node --test tests/frontend/analisis.test.cjs
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const CODIGO = fs.readFileSync(path.join(__dirname, "..", "..", "static", "js", "analisis.js"), "utf8");

function ejecutar({ aviso = true, respuestas = [] } = {}) {
const temporizadores = [];
const mensaje = { textContent: "Esta pantalla se actualiza sola." };
const elemento = aviso
? {
    getAttribute: (n) => ({ "data-estado-url": "/estado/", "data-estado-actual": "EN_PROCESO" })[n],
    querySelector: () => mensaje,
    }
: null;
const estado = { recargas: 0, consultas: 0 };
const contexto = {
document: { querySelector: () => elemento },
window: {
    location: { reload: () => { estado.recargas += 1; } },
    setTimeout: (fn, ms) => { temporizadores.push({ fn, ms }); },
},
fetch: () => {
    const r = respuestas[estado.consultas] ;
    estado.consultas += 1;
    if (r === "error") { return Promise.reject(new Error("red")); }
    return Promise.resolve({ ok: r !== "http", json: () => Promise.resolve(r) });
},
};
vm.runInNewContext(CODIGO, contexto);
return { temporizadores, mensaje, estado };
}

async function avanzar(sim) {
const t = sim.temporizadores.shift();
t.fn();
await new Promise((r) => setImmediate(r));
}

test("sin aviso en la página no hace nada", () => {
const sim = ejecutar({ aviso: false });
assert.strictEqual(sim.temporizadores.length, 0);
});

test("consulta cada 3 segundos", () => {
const sim = ejecutar();
assert.strictEqual(sim.temporizadores.length, 1);
assert.strictEqual(sim.temporizadores[0].ms, 3000);
});

test("si el estado cambia, recarga la página", async () => {
const sim = ejecutar({ respuestas: [{ estado: "COMPLETADO" }] });
await avanzar(sim);
assert.strictEqual(sim.estado.recargas, 1);
});

test("si el estado sigue igual, no recarga y vuelve a consultar", async () => {
const sim = ejecutar({ respuestas: [{ estado: "EN_PROCESO" }] });
await avanzar(sim);
assert.strictEqual(sim.estado.recargas, 0);
assert.strictEqual(sim.temporizadores.length, 1);
});

test("un error de red o de servidor no rompe y sigue consultando", async () => {
const sim = ejecutar({ respuestas: ["error", "http"] });
await avanzar(sim);
await avanzar(sim);
assert.strictEqual(sim.estado.recargas, 0);
assert.strictEqual(sim.temporizadores.length, 1);
});

test("tras 20 intentos deja de consultar y pide recargar", async () => {
const sim = ejecutar({ respuestas: Array(25).fill({ estado: "EN_PROCESO" }) });
for (let i = 0; i < 20; i += 1) { await avanzar(sim); }
assert.strictEqual(sim.estado.consultas, 20);
assert.strictEqual(sim.temporizadores.length, 0);
assert.match(sim.mensaje.textContent, /Recarga la página/);
});