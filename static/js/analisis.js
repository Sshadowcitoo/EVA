// Pantallas de análisis y revisión de Cocina.
// 1) Detalle: actualiza el estado mientras el análisis está en curso.
// Consulta cada 3 s la dirección de data-estado-url (GET JSON {"estado": "..."}).
// Reglas de la consulta: mismo origen, sin caché, sin seguir redirecciones, tiempo máximo por petición y
// plazo total, pausa al ocultar la página, y error con reintento manual si algo falla.
(function () {
"use strict";
iniciarRevision();
iniciarConsulta();

// Revisión de Cocina: motivo obligatorio según la acción, sugerencias de motivo y envío único.
// El servidor vuelve a validar todo; esto solo evita errores y dobles envíos.
function iniciarRevision() {
var formulario = document.querySelector("[data-revision-form]");
if (!formulario) { return; }

var motivo = formulario.querySelector("#motivo-revision");
var error = formulario.querySelector("[data-motivo-error]");
var estado = formulario.querySelector("[data-revision-estado]");
var sugerencias = formulario.querySelector("[data-motivo-sugerencias]");
var selector = sugerencias ? sugerencias.querySelector("select") : null;
var botones = Array.prototype.slice.call(formulario.querySelectorAll("button[type=submit]"));
var inhabilitados = botones.map(function (b) { return b.hasAttribute("disabled"); });
var rectificar = formulario.hasAttribute("data-rectificar");
var enviando = false;

if (sugerencias) { sugerencias.hidden = false; }
if (selector) {
    selector.addEventListener("change", function () {
    if (selector.value) { motivo.value = selector.value; }
    motivo.focus();
    });
}

formulario.addEventListener("submit", function (evento) {
    var boton = evento.submitter;
    var requiere = rectificar || Boolean(boton && boton.hasAttribute("data-requiere-motivo"));
    if (enviando) { evento.preventDefault(); return; }
    if (requiere && !motivo.value.trim()) {
    evento.preventDefault();
    error.hidden = false;
    motivo.setAttribute("aria-invalid", "true");
    motivo.focus();
    return;
    }
    error.hidden = true;
    motivo.removeAttribute("aria-invalid");
    enviando = true;
    estado.textContent = "Guardando la decisión…";
    window.setTimeout(function () {
    botones.forEach(function (b) { b.disabled = true; });
    }, 0);
});

// Al volver con el botón "atrás" el formulario debe quedar usable.
window.addEventListener("pageshow", function () {
    enviando = false;
    estado.textContent = "";
    botones.forEach(function (b, i) { b.disabled = inhabilitados[i]; });
});
}

// Consulta del estado mientras el análisis está en curso.
function iniciarConsulta() {
var ESTADOS = ["PENDIENTE", "EN_PROCESO", "COMPLETADO", "FALLIDO", "TIEMPO_AGOTADO"];
var INTERVALO_MS = 3000;
var TIMEOUT_PETICION_MS = 5000;
var PLAZO_TOTAL_MS = 60000;
var MAX_FALLOS_SEGUIDOS = 3;

var aviso = document.querySelector("[data-estado-url]");
if (!aviso) { return; }

var url = aviso.getAttribute("data-estado-url");
var actual = aviso.getAttribute("data-estado-actual");
var mensaje = aviso.querySelector("[data-estado-mensaje]");
var boton = aviso.querySelector("[data-estado-reintentar]");

var temporizador = null;
var controlador = null;
var temporizadorPeticion = null;
var inicio = Date.now();
var fallos = 0;
var terminado = false;
var pausado = false;

function decir(texto) { if (mensaje) { mensaje.textContent = texto; } }
function mostrarBoton(visible) { if (boton) { boton.hidden = !visible; } }

function cancelar() {
    if (temporizador !== null) { window.clearTimeout(temporizador); temporizador = null; }
    if (temporizadorPeticion !== null) { window.clearTimeout(temporizadorPeticion); temporizadorPeticion = null; }
    if (controlador) { controlador.abort(); controlador = null; }
}

function terminar(texto, conBoton) {
    terminado = true;
    cancelar();
    decir(texto);
    mostrarBoton(Boolean(conBoton));
}

function programar() {
    if (terminado || pausado) { return; }
    if (Date.now() - inicio >= PLAZO_TOTAL_MS) {
    terminar("Sigue en curso. Recarga la página para ver el avance.", true);
    return;
    }
    temporizador = window.setTimeout(consultar, INTERVALO_MS);
}

function fallar(texto) {
    fallos += 1;
    if (fallos >= MAX_FALLOS_SEGUIDOS) {
    terminar(texto, true);
    return;
    }
    programar();
}

function consultar() {
    temporizador = null;
    if (terminado || pausado) { return; }
    controlador = new AbortController();
    var propio = controlador;
    temporizadorPeticion = window.setTimeout(function () { propio.abort(); }, TIMEOUT_PETICION_MS);

    fetch(url, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
    cache: "no-store",
    redirect: "error",
    signal: propio.signal
    })
    .then(function (respuesta) {
        if (propio !== controlador) { return; }
        window.clearTimeout(temporizadorPeticion);
        temporizadorPeticion = null;
        if (respuesta.status === 401 || respuesta.status === 403) {
        terminar("Tu sesión terminó o ya no tienes acceso. Inicia sesión de nuevo.", true);
        return;
        }
        if (!respuesta.ok) {
        fallar("No se pudo consultar el estado. Revisa tu conexión y reintenta.");
        return;
        }
        return respuesta.json().then(function (datos) {
        if (propio !== controlador) { return; }
        var nuevo = datos && datos.estado;
        if (ESTADOS.indexOf(nuevo) === -1) {
            terminar("No se reconoció el estado del análisis. Recarga la página.", true);
            return;
        }
        fallos = 0;
        if (nuevo !== actual) {
            terminar("El análisis cambió de estado. Actualizando…", false);
            window.location.reload();
            return;
        }
        programar();
        });
    })
    .catch(function () {
        if (propio !== controlador) { return; } // cancelada a propósito (página oculta o cerrada)
        window.clearTimeout(temporizadorPeticion);
        temporizadorPeticion = null;
        fallar("No se pudo consultar el estado. Revisa tu conexión o tu sesión y reintenta.");
    });
}

function reiniciar() {
    cancelar();
    terminado = false;
    pausado = false;
    fallos = 0;
    inicio = Date.now();
    mostrarBoton(false);
    decir("Consultando de nuevo…");
    consultar();
}

if (boton) { boton.addEventListener("click", reiniciar); }

document.addEventListener("visibilitychange", function () {
    if (terminado) { return; }
    if (document.hidden) {
    pausado = true;
    cancelar();
    } else if (pausado) {
    pausado = false;
    programar();
    }
});

window.addEventListener("pagehide", function () {
    terminado = true;
    cancelar();
});

programar();
}
})();
