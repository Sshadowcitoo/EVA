/* La validación de seguridad y la aceptación siempre corresponden al servidor. */
(() => {
  'use strict';
  document.querySelectorAll('[data-photo-form]').forEach((form) => {
    const input = form.querySelector('input[type="file"]');
    if (!input) return;
    input.accept = 'image/jpeg,image/png';
    input.setAttribute('capture', 'environment');
    const preview = form.querySelector('[data-photo-preview]');
    const enhancement = form.querySelector('[data-photo-enhancement]');
    const empty = form.querySelector('[data-photo-empty]');
    const status = form.querySelector('[data-photo-status]');
    const submit = form.querySelector('[data-photo-submit]');
    const permitted = !submit.disabled;
    let objectURL = null;
    let sequence = 0;
    let valid = false;
    const message = (text, error = false) => {
      status.textContent = text;
      status.dataset.error = String(error);
    };
    const clear = () => {
      if (objectURL) URL.revokeObjectURL(objectURL);
      objectURL = null;
      preview.removeAttribute('src');
      preview.hidden = true;
      enhancement.hidden = true;
      if (empty) empty.hidden = false;
      valid = false;
      submit.disabled = true;
    };
    clear();
    input.addEventListener('change', () => {
      const current = ++sequence;
      clear();
      const file = input.files[0];
      if (!file) { message('Selecciona una fotografía.'); return; }
      if (!['image/jpeg', 'image/png'].includes(file.type) || file.size === 0) {
        message('Selecciona una imagen JPEG o PNG válida.', true); return;
      }
      if (file.size > Number(form.dataset.maxBytes)) {
        message('La fotografía supera el tamaño permitido.', true); return;
      }
      objectURL = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => {
        if (current !== sequence) return;
        if (image.naturalWidth * image.naturalHeight > Number(form.dataset.maxPixels)) {
          clear(); message('La fotografía supera el límite de píxeles.', true); return;
        }
        preview.src = objectURL;
        preview.hidden = false;
        enhancement.hidden = false;
        if (empty) empty.hidden = true;
        valid = true;
        submit.disabled = !permitted;
        message('Revisa la imagen antes de guardar. Todavía no está guardada.');
      };
      image.onerror = () => {
        if (current !== sequence) return;
        clear(); message('No se puede abrir la imagen. Elige otra fotografía.', true);
      };
      image.src = objectURL;
    });
    form.querySelector('[data-photo-repeat]').addEventListener('click', () => {
      ++sequence; input.value = ''; clear(); message('Selecciona otra fotografía.'); input.click();
    });
    form.addEventListener('submit', (event) => {
      if (!valid || !permitted) { event.preventDefault(); return; }
      submit.disabled = true;
      message('Guardando fotografía… Espera la confirmación del servidor.');
    });
    window.addEventListener('pageshow', (event) => {
      if (event.persisted) input.dispatchEvent(new Event('change'));
    });
    window.addEventListener('pagehide', () => { ++sequence; clear(); });
  });
})();
