const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

const codigo = readFileSync(join(__dirname, '../../static/js/indicadores.js'), 'utf8');

function renderizar(intensidades) {
  const semanas = intensidades.map((intensidad, i) => ({
    inicio: `2026-10-${String(5 + 7 * i).padStart(2, '0')}`,
    intensidad,
    parcial: false,
  }));
  const nodos = [];
  const atributos = new Map([['hidden', ''], ['aria-hidden', 'true']]);
  const leyenda = {};
  const svg = {
    dataset: { semanas: 'eva-semanas' },
    nextElementSibling: leyenda,
    append(nodo) { nodos.push(nodo); },
    removeAttribute(nombre) { atributos.delete(nombre); },
  };
  const document = {
    querySelector(selector) {
      assert.equal(selector, '.eva-trend');
      return svg;
    },
    getElementById(id) {
      assert.equal(id, 'eva-semanas');
      return { textContent: JSON.stringify(semanas) };
    },
    createElementNS(ns, tipo) {
      assert.equal(ns, 'http://www.w3.org/2000/svg');
      return {
        tipo,
        atributos: {},
        setAttribute(nombre, valor) { this.atributos[nombre] = String(valor); },
      };
    },
  };
  runInNewContext(codigo, { document });
  return {
    nodos,
    puntos: nodos.filter(n => n.tipo === 'circle'),
    segmentos: nodos.filter(n => n.atributos.class === 'eva-trend-line'),
    oculto: atributos.has('hidden'),
    ocultoAtecnologiaAsistiva: atributos.get('aria-hidden'),
    leyenda,
  };
}

test('un cero confirmado se dibuja sobre la línea de 0 %', () => {
  // Django serializa los valores Decimal como cadenas.
  const { puntos, segmentos, nodos, oculto } = renderizar(['0.00', '25.00']);
  const base = nodos.filter(n => n.atributos.class === 'eva-trend-grid')[0];
  assert.equal(puntos.length, 2);
  assert.equal(puntos[0].atributos.cy, base.atributos.y1);
  assert.equal(segmentos.length, 1);
  assert.equal(oculto, false);
});

test('una semana sin evidencia interrumpe la línea entre puntos válidos', () => {
  const { puntos, segmentos } = renderizar(['10.00', '20.00', null, '30.00']);
  assert.equal(puntos.length, 3);
  assert.equal(segmentos.length, 1);
  assert.equal(segmentos[0].atributos.x1, puntos[0].atributos.cx);
  assert.equal(segmentos[0].atributos.x2, puntos[1].atributos.cx);
  assert.ok(Number(puntos[2].atributos.cx) > Number(puntos[1].atributos.cx));
});

test('una única semana muestra un punto con coordenadas válidas', () => {
  const { puntos, segmentos, oculto, ocultoAtecnologiaAsistiva, leyenda } = renderizar(['32.86']);
  assert.equal(puntos.length, 1);
  assert.ok(Number.isFinite(Number(puntos[0].atributos.cx)));
  assert.ok(Number.isFinite(Number(puntos[0].atributos.cy)));
  assert.equal(segmentos.length, 0);
  assert.equal(oculto, false);
  assert.equal(ocultoAtecnologiaAsistiva, 'true');
  assert.deepEqual(leyenda, {});
});

test('sin valores aptos el SVG permanece oculto y sin ejes ni puntos', () => {
  for (const intensidades of [[], [null, null]]) {
    const { nodos, oculto } = renderizar(intensidades);
    assert.equal(oculto, true);
    assert.deepEqual(nodos, []);
  }
});
