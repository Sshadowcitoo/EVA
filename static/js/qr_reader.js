/* Lee el valor; nunca navega ni autentica por el contenido de un QR. */
(() => {
  'use strict';
  document.querySelectorAll('[data-qr-reader]').forEach((root) => {
    const video = root.querySelector('[data-qr-video]');
    const canvas = root.querySelector('[data-qr-canvas]');
    const start = root.querySelector('[data-qr-start]');
    const stopButton = root.querySelector('[data-qr-stop]');
    const status = root.querySelector('[data-qr-status]');
    const value = root.querySelector('[data-qr-value]');
    let stream = null;
    let frame = null;
    let generation = 0;
    let reading = false;
    const stop = () => {
      generation += 1;
      reading = false;
      if (frame !== null) cancelAnimationFrame(frame);
      if (stream) stream.getTracks().forEach((track) => track.stop());
      stream = null;
      video.srcObject = null;
      video.hidden = true;
      start.disabled = false;
      stopButton.hidden = true;
    };
    const scan = () => {
      if (!reading) return;
      if (video.readyState >= 2 && video.videoWidth > 0) {
        const ratio = Math.min(1, 640 / video.videoWidth);
        canvas.width = Math.round(video.videoWidth * ratio);
        canvas.height = Math.round(video.videoHeight * ratio);
        const context = canvas.getContext('2d', {willReadFrequently: true});
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
        const result = window.jsQR(pixels.data, pixels.width, pixels.height);
        if (result && result.data.length <= 2048) {
          value.value = result.data;
          const number = root.closest('form').querySelector('[name="numero"]');
          if (number) number.value = '';
          stop();
          status.textContent = 'Etiqueta leída. Pulsa Buscar registro para comprobarla en el sistema.';
          value.focus();
          return;
        }
      }
      frame = requestAnimationFrame(scan);
    };
    start.addEventListener('click', async () => {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || !window.jsQR) {
        status.textContent = 'El lector no está disponible. Introduce el número visible de la bandeja.';
        return;
      }
      start.disabled = true;
      const current = ++generation;
      try {
        const acquired = await navigator.mediaDevices.getUserMedia({video: {facingMode: 'environment', width: {ideal: 640}}, audio: false});
        if (current !== generation || document.hidden) {
          acquired.getTracks().forEach((track) => track.stop()); return;
        }
        stream = acquired;
        video.srcObject = stream;
        video.hidden = false;
        stopButton.hidden = false;
        await video.play();
        if (current !== generation) return;
        reading = true;
        status.textContent = 'Apunta al QR de la bandeja.';
        scan();
      } catch (error) {
        if (current !== generation) return;
        stop();
        status.textContent = 'No se pudo usar la cámara. Revisa el permiso o introduce el número de la bandeja.';
      }
    });
    stopButton.addEventListener('click', () => { stop(); status.textContent = 'Cámara detenida.'; });
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
    window.addEventListener('pagehide', stop);
    root.querySelector('details').addEventListener('toggle', (event) => { if (!event.target.open) stop(); });
  });
})();
