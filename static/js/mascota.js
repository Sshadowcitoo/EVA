/* La mascota indica una espera; solo el servidor confirma el guardado. */
(() => {
  'use strict';
  document.querySelectorAll('form[data-eva-save]').forEach((form) => {
    const waiting = form.querySelector('[data-eva-saving]');
    if (!waiting) return;
    form.addEventListener('submit', (event) => {
      if (!event.defaultPrevented && form.checkValidity()) waiting.hidden = false;
    });
    window.addEventListener('pageshow', () => { waiting.hidden = true; });
  });
})();
