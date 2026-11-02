// Actualiza el detalle del análisis mientras está en curso.
// Consulta cada 3 segundos la dirección de data-estado-url (JSON con {"estado": "..."}).
// Cuando el estado cambia, recarga la página para mostrar el resultado.
(function () {
"use strict";
var aviso = document.querySelector("[data-estado-url]");
if (!aviso) { return; }

var url = aviso.getAttribute("data-estado-url");
var actual = aviso.getAttribute("data-estado-actual");
var mensaje = aviso.querySelector("[data-estado-mensaje]");
var MAX_INTENTOS = 20; // unos 60 segundos
var intentos = 0;

function consultar() {
intentos += 1;
fetch(url, { headers: { Accept: "application/json" }, credentials: "same-origin" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (datos) {
    if (datos && datos.estado && datos.estado !== actual) {
        window.location.reload();
        return;
    }
    programar();
    })
    .catch(programar);
}

function programar() {
if (intentos >= MAX_INTENTOS) {
    if (mensaje) { mensaje.textContent = "Sigue en curso. Recarga la página para ver el avance."; }
    return;
}
window.setTimeout(consultar, 3000);
}

programar();
})();