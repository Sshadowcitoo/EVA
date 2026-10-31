/* Consulta privada de solo lectura. El servidor decide vigencia, permisos y guardado. */
(() => {
  'use strict';
  document.querySelectorAll('[data-capture-link]').forEach((root) => {
    const status = root.querySelector('[data-link-status]');
    const countdown = root.querySelector('[data-link-countdown]');
    const retry = root.querySelector('[data-link-retry]');
    const photo = root.querySelector('[data-link-photo]');
    const qr = root.querySelector('[data-link-qr]');
    const cancel = root.querySelector('[data-link-cancel]');
    const result = root.querySelector('[data-link-result]');
    const terminal = new Set(['COMPLETADA', 'CANCELADA', 'EXPIRADA']);
    let state = root.dataset.state;
    let timer = null;
    let controller = null;
    let stopped = false;
    let busy = false;
    let generation = 0;
    const expires = Date.parse(root.dataset.expiresAt);
    const expiryLabel = root.querySelector('time');
    if (expiryLabel && Number.isFinite(expires)) expiryLabel.textContent = new Date(expires).toLocaleTimeString('es-EC');
    const localURL = (value) => {
      if (!value) return null;
      try {
        const url = new URL(value, window.location.origin);
        return url.origin === window.location.origin && !url.username && !url.password ? url.href : null;
      } catch (_) { return null; }
    };
    const endpoint = localURL(root.dataset.stateUrl);
    const pause = () => {
      generation += 1;
      clearTimeout(timer);
      if (controller) controller.abort();
      controller = null;
      busy = false;
    };
    const hideQR = () => { if (qr) qr.hidden = true; };
    const finish = (next) => {
      state = next;
      root.dataset.state = state;
      stopped = true;
      pause();
      hideQR();
      if (cancel) cancel.hidden = true;
      retry.hidden = true;
      countdown.textContent = '';
      status.textContent = {
        COMPLETADA: 'Fotografía guardada y confirmada por el servidor.',
        EXPIRADA: 'El enlace caducó. Genera otro para continuar.',
        CANCELADA: 'El enlace fue cancelado y ya no permite capturar.',
      }[state];
      if (result) result.hidden = state !== 'COMPLETADA';
    };
    const failure = (message, recoverable = true) => {
      stopped = true;
      pause();
      status.textContent = message;
      retry.hidden = !recoverable;
      if (!recoverable) { hideQR(); if (cancel) cancel.hidden = true; }
    };
    const poll = async () => {
      if (stopped || document.hidden || busy || state !== 'PENDIENTE') return;
      busy = true;
      const current = ++generation;
      controller = new AbortController();
      const requestController = controller;
      const timeout = setTimeout(() => requestController.abort(), 10000);
      try {
        const response = await fetch(endpoint, {credentials: 'same-origin', cache: 'no-store', redirect: 'error',
          headers: {Accept: 'application/json'}, signal: controller.signal});
        if (current !== generation) return;
        if (response.status === 401 || response.status === 403) {
          failure('La sesión caducó o no tienes permiso. Inicia sesión de nuevo para consultar.', false); return;
        }
        if (response.status === 404 || response.status === 410) {
          failure('El enlace ya no está disponible. Consulta el servicio o genera otro enlace.', false); return;
        }
        if (!response.ok) throw new Error('Respuesta no válida');
        const data = await response.json();
        if (current !== generation) return;
        if (!['PENDIENTE', 'COMPLETADA', 'EXPIRADA', 'CANCELADA'].includes(data.estado)) throw new Error('Estado desconocido');
        if (terminal.has(data.estado)) {
          finish(data.estado);
          if (data.estado === 'COMPLETADA' && data.foto_url) {
            const imageURL = localURL(data.foto_url);
            if (imageURL) { photo.src = imageURL; photo.hidden = false; }
          }
          return;
        }
        // Alcanzar el plazo local no equivale a que el servidor haya rechazado la foto.
        if (Date.now() >= expires) {
          hideQR();
          countdown.textContent = 'Plazo local alcanzado. Esperando confirmación del servidor.';
        } else {
          countdown.textContent = 'Tiempo restante aproximado: ' + Math.ceil((expires - Date.now()) / 1000) + ' s.';
        }
        status.textContent = 'Esperando fotografía. Escanear el QR no confirma el guardado.';
        timer = setTimeout(poll, 3000);
      } catch (_) {
        if (current === generation) failure('No se pudo consultar el estado. Revisa la conexión y vuelve a consultar.');
      } finally {
        clearTimeout(timeout);
        if (current === generation) { busy = false; controller = null; }
      }
    };
    retry.addEventListener('click', () => {
      if (!endpoint || !Number.isFinite(expires) || terminal.has(state)) return;
      stopped = false;
      retry.hidden = true;
      poll();
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) pause();
      else if (!stopped) poll();
    });
    window.addEventListener('pagehide', pause);
    window.addEventListener('pageshow', (event) => { if (event.persisted && !stopped) poll(); });
    if (terminal.has(state)) finish(state);
    else if (state === 'PENDIENTE') {
      if (endpoint && Number.isFinite(expires)) poll();
      else failure('La consulta de estado aún no está conectada. No se ha confirmado ningún guardado.', false);
    }
  });
})();
