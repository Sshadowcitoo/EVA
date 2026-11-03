/* Evita envíos accidentales; la concurrencia se resuelve en el servidor. */
(function (root) {
  function prepararFormulario(form) {
    let enviando = false;
    form.addEventListener('submit', function (event) {
      if (enviando) { event.preventDefault(); return; }
      if (!form.checkValidity()) { event.preventDefault(); return; }
      enviando = true;
      const button = form.querySelector('button[type="submit"]');
      if (button) button.disabled = true;
      const estado = form.querySelector('[data-envio]');
      if (estado) estado.textContent = 'Enviando solicitud… Espera la confirmación del servidor.';
    });
    function restablecer() {
      enviando = false;
      const button = form.querySelector('button[type="submit"]');
      if (button && !form.dataset.bloqueado) button.disabled = false;
      const estado = form.querySelector('[data-envio]');
      if (estado) estado.textContent = '';
    }
    if (root.addEventListener) root.addEventListener('pageshow', restablecer);
  }
  if (typeof module !== 'undefined') module.exports = { prepararFormulario };
  if (root.document) root.document.querySelectorAll('[data-rec-submit]').forEach(prepararFormulario);
})(typeof window !== 'undefined' ? window : globalThis);
