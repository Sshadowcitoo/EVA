document.querySelectorAll('[data-copiar-tecnico]').forEach((boton) => {
  const detalle = boton.closest('details');
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
