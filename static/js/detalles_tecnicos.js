// Reúne metadatos de lectura sin duplicarlos ni mover los formularios de acción.
(() => {
  const destino = document.querySelector('[data-detalles-contenido]');
  if (!destino) return;
  const fuentes = Array.from(document.querySelectorAll('.eva-tecnico, [data-eva-tecnico]'));
  fuentes.forEach((fuente) => {
    const resumen = Array.from(fuente.children).find((hijo) => hijo.tagName === 'SUMMARY');
    const titulo = fuente.dataset.titulo || (resumen ? resumen.textContent : 'Información del registro');
    const bloque = document.createElement('section');
    bloque.className = 'eva-tecnico-bloque';
    const cabecera = document.createElement('h2');
    cabecera.textContent = titulo.replace(/^Detalles técnicos\s*[·:]?\s*/i, '') || 'Información del registro';
    bloque.appendChild(cabecera);
    if (resumen) resumen.remove();
    while (fuente.firstChild) bloque.appendChild(fuente.firstChild);
    // Si estaba dentro de otra fuente, conserva esa agrupación en el apartado final.
    if (destino.contains(fuente)) fuente.replaceWith(bloque);
    else { destino.appendChild(bloque); fuente.remove(); }
  });
  const vacio = destino.querySelector('[data-detalles-vacio]');
  if (vacio && destino.querySelector('.eva-tecnico-bloque')) vacio.remove();
})();

document.querySelectorAll('[data-copiar-tecnico]').forEach((boton) => {
  const detalle = boton.closest('.eva-tecnico-bloque') || boton.closest('details');
  const valor = detalle.querySelector('[data-valor-tecnico]');
  const estado = detalle.querySelector('[data-estado-copia]');
  boton.hidden = false;
  boton.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(valor.textContent);
      estado.textContent = 'Copiado.';
    } catch {
      const rango = document.createRange();
      rango.selectNodeContents(valor);
      const seleccion = window.getSelection();
      seleccion.removeAllRanges();
      seleccion.addRange(rango);
      estado.textContent = 'Texto seleccionado. Usa la opción de copiar de tu dispositivo.';
    }
  });
});
