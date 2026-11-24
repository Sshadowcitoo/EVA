// Reúne las explicaciones de lectura sin mover los formularios de acción.
(() => {
  const destino = document.querySelector('[data-detalles-contenido]');
  if (!destino) return;
  const fuentes = Array.from(document.querySelectorAll('.eva-informacion'));
  fuentes.forEach((fuente) => {
    const resumen = Array.from(fuente.children).find((hijo) => hijo.tagName === 'SUMMARY');
    const titulo = fuente.dataset.titulo || (resumen ? resumen.textContent : 'Sobre este resultado');
    const bloque = document.createElement('section');
    bloque.className = 'eva-tecnico-bloque';
    const cabecera = document.createElement('h2');
    cabecera.textContent = titulo || 'Sobre este resultado';
    bloque.appendChild(cabecera);
    if (resumen) resumen.remove();
    while (fuente.firstChild) bloque.appendChild(fuente.firstChild);
    // Si estaba dentro de otra fuente, conserva esa agrupación en el apartado final.
    if (destino.contains(fuente)) fuente.replaceWith(bloque);
    else { destino.appendChild(bloque); fuente.remove(); }
  });
})();
