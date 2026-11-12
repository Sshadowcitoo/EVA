(() => {
  const svg = document.querySelector('.eva-trend');
  if (!svg) return;
  const semanas = JSON.parse(document.getElementById(svg.dataset.semanas).textContent);
  if (!semanas.some(s => s.intensidad !== null)) return;
  const crear = (tipo, atributos, texto) => {
    const nodo = document.createElementNS('http://www.w3.org/2000/svg', tipo);
    Object.entries(atributos).forEach(([clave, valor]) => nodo.setAttribute(clave, valor));
    if (texto !== undefined) nodo.textContent = texto;
    svg.append(nodo);
  };
  const x = i => semanas.length === 1 ? 253 : 46 + i * 410 / (semanas.length - 1);
  const y = valor => 130 - valor * 1.14;
  for (const valor of [0, 25, 50, 75, 100]) {
    crear('line', {x1: 43, x2: 458, y1: y(valor), y2: y(valor), class: 'eva-trend-grid'});
    crear('text', {x: 1, y: y(valor) + 4}, `${valor} %`);
  }
  semanas.forEach((semana, i) => {
    if (i === 0 || i === semanas.length - 1 || semanas.length <= 5) {
      const [, mes, dia] = semana.inicio.split('-');
      crear('text', {x: x(i), y: 151, 'text-anchor': 'middle'}, `${dia}/${mes}`);
    }
    if (semana.intensidad === null) return;
    const anterior = semanas[i - 1];
    if (anterior && anterior.intensidad !== null) {
      crear('line', {x1: x(i - 1), y1: y(anterior.intensidad), x2: x(i), y2: y(semana.intensidad), class: 'eva-trend-line'});
    }
    crear('circle', {cx: x(i), cy: y(semana.intensidad), r: 4, class: semana.parcial ? 'eva-trend-point eva-trend-partial' : 'eva-trend-point'});
  });
  svg.removeAttribute('hidden');
  // Sin JavaScript la tabla permanece abierta; con el gráfico puede desplegarse.
  svg.parentElement?.querySelector('.eva-week-details')?.removeAttribute('open');
})();
