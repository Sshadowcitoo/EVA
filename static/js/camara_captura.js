/* Cámara explícita: crea un archivo local; Guardar fotografía sigue siendo necesario. */
(() => {
  'use strict';
  document.querySelectorAll('[data-photo-form]').forEach((form) => {
    const root = form.querySelector('[data-photo-camera]');
    if (!root) return;
    const input = form.querySelector('input[type="file"]');
    const video = root.querySelector('[data-camera-video]');
    const canvas = root.querySelector('[data-camera-canvas]');
    const start = root.querySelector('[data-camera-start]');
    const take = root.querySelector('[data-camera-take]');
    const close = root.querySelector('[data-camera-stop]');
    const status = root.querySelector('[data-camera-status]');
    let stream = null;
    let generation = 0;
    const stop = () => {
      generation += 1;
      if (stream) stream.getTracks().forEach((track) => track.stop());
      stream = null;
      video.srcObject = null;
      video.hidden = true;
      take.hidden = close.hidden = true;
      take.disabled = false;
      start.disabled = false;
    };
    start.addEventListener('click', async () => {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || typeof DataTransfer === 'undefined') {
        status.textContent = 'Este navegador no permite abrir la cámara aquí. Abre EVA en Chrome o Safari, o selecciona un archivo.';
        return;
      }
      stop();
      input.value = '';
      input.dispatchEvent(new Event('change', {bubbles: true}));
      const current = generation;
      start.disabled = true;
      close.hidden = false;
      status.textContent = 'Solicitando acceso a la cámara…';
      try {
        const acquired = await navigator.mediaDevices.getUserMedia({
          audio: false, video: {facingMode: {ideal: 'environment'}, width: {ideal: 1920}, height: {ideal: 1080}},
        });
        if (current !== generation || document.hidden) {
          acquired.getTracks().forEach((track) => track.stop()); return;
        }
        stream = acquired;
        video.srcObject = acquired;
        video.hidden = false;
        await video.play();
        if (current !== generation) return;
        take.hidden = false;
        status.textContent = 'Encuadra el plato y pulsa Tomar fotografía. Todavía no se ha guardado ninguna foto.';
      } catch (error) {
        if (current !== generation) return;
        stop();
        status.textContent = error.name === 'NotAllowedError'
          ? 'No se concedió acceso a la cámara. Revisa el permiso del sitio o selecciona un archivo.'
          : 'No se pudo abrir la cámara. Comprueba que esté conectada y que otra aplicación no la esté usando, o selecciona un archivo.';
      }
    });
    take.addEventListener('click', () => {
      if (!stream || !video.videoWidth || !video.videoHeight || video.readyState < 2) {
        status.textContent = 'Espera a que aparezca la imagen de la cámara e inténtalo de nuevo.'; return;
      }
      const current = generation;
      take.disabled = true;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      try {
        canvas.getContext('2d').drawImage(video, 0, 0);
        canvas.toBlob((blob) => {
          if (current !== generation || document.hidden) return;
          if (!blob) {
            take.disabled = false;
            status.textContent = 'No se pudo preparar la foto. Inténtalo otra vez.'; return;
          }
          try {
            const transfer = new DataTransfer();
            transfer.items.add(new File([blob], 'captura.jpg', {type: 'image/jpeg'}));
            input.files = transfer.files;
            stop();
            input.dispatchEvent(new Event('change', {bubbles: true}));
            status.textContent = 'Foto tomada. Revisa la vista previa y el checklist; después pulsa Guardar fotografía.';
          } catch (_) {
            stop();
            status.textContent = 'Este navegador no permite adjuntar la foto tomada. Usa el selector de archivo o abre EVA en Chrome o Safari.';
          }
        }, 'image/jpeg', 0.95);
      } catch (_) {
        take.disabled = false;
        status.textContent = 'No se pudo tomar la fotografía. Inténtalo de nuevo o selecciona un archivo.';
      }
    });
    close.addEventListener('click', () => { stop(); status.textContent = 'Cámara cerrada.'; });
    input.addEventListener('change', stop);
    form.addEventListener('submit', stop);
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
    window.addEventListener('pagehide', stop);
  });
})();
