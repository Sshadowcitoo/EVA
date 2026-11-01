import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_GET, require_http_methods

from apps.catalogo.permissions import REGISTRO, roles_required

from . import limpieza, services, storage
from .forms import ConfirmarRetornoForm, FotoForm, ServicioForm
from .models import (
    AsignacionBandeja,
    Bandeja,
    EtiquetaBandeja,
    FotografiaServicio,
    Servicio,
)


@roles_required(REGISTRO)
def nueva_bandeja(request):
    if request.method == "POST":
        form = ServicioForm(request.POST)
        if form.is_valid():
            try:
                servicio = Servicio.registrar(
                    plato=form.cleaned_data["plato"],
                    porcion=form.cleaned_data["tipo_porcion"],
                    usuario=request.user,
                )
            except ValidationError as error:
                # Por si el plato se desactivó justo entre la validación
                # y el guardado: se muestra el error, no se guarda nada.
                form.add_error(None, error)
            else:
                return redirect("captura:confirmacion", pk=servicio.pk)
    else:
        form = ServicioForm()

    return render(request, "captura/nueva_bandeja.html", {"form": form})


@roles_required(REGISTRO)
def confirmacion(request, pk):
    # Solo el usuario que creó el servicio puede ver su confirmación.
    servicio = get_object_or_404(Servicio, pk=pk, creado_por=request.user)
    return render(request, "captura/confirmacion.html", {"servicio": servicio})


# ---------- Bloque 2: bandejas y captura ----------

Estado = Servicio.EstadoCaptura
Etapa = FotografiaServicio.Etapa
logger = logging.getLogger(__name__)


def _contexto_base(**extra):
    """Variables que las pantallas de Jean necesitan en todas las operaciones."""
    contexto = {
        "operacion_habilitada": True,
        "lector_habilitado": True,
        "retorno_url": reverse("captura:buscar_retorno"),
        "max_bytes": settings.EVA_CAPTURE_MAX_BYTES,
        "max_pixels": settings.EVA_CAPTURE_MAX_PIXELS,
    }
    contexto.update(extra)
    return contexto


def _localizar_bandeja(request):
    """Lee ?numero= o ?etiqueta= (solo uno). Devuelve (bandeja, consulta, error).

    Sin datos: (None, "", None). Desconocida, inactiva o revocada: 404.
    """
    numero = request.GET.get("numero", "").strip()
    etiqueta = request.GET.get("etiqueta", "").strip()
    if not numero and not etiqueta:
        return None, "", None
    if numero and etiqueta:
        return None, "", "Escribe el número o escanea la etiqueta, no ambos."

    if etiqueta:
        etiqueta_vigente = (
            EtiquetaBandeja.objects.filter(codigo=etiqueta, revocada_en__isnull=True)
            .select_related("bandeja")
            .first()
        )
        if etiqueta_vigente is None or not etiqueta_vigente.bandeja.activo:
            raise Http404("Etiqueta desconocida o revocada.")
        return etiqueta_vigente.bandeja, urlencode({"etiqueta": etiqueta}), None

    if not numero.isdigit():
        return None, "", "El número de bandeja solo puede contener dígitos."
    bandeja = get_object_or_404(Bandeja, numero=int(numero), activo=True)
    return bandeja, urlencode({"numero": numero}), None


def _asignacion_abierta(bandeja):
    return (
        AsignacionBandeja.objects.filter(bandeja=bandeja, fin__isnull=True)
        .select_related("servicio")
        .first()
    )


def _bandeja_del_servicio(servicio):
    asignacion = servicio.asignaciones.select_related("bandeja").first()
    return asignacion.bandeja if asignacion else None


def _foto_vigente(servicio, etapa):
    return FotografiaServicio.objects.filter(
        servicio=servicio, etapa=etapa, vigente=True
    ).first()


@roles_required(REGISTRO)
@require_http_methods(["GET", "POST"])
def resolver_bandeja(request):
    """Servido. GET busca la bandeja; POST crea el servicio y la asigna."""
    bandeja, consulta, error = _localizar_bandeja(request)
    contexto = _contexto_base(
        es_retorno=False,
        buscar_url=reverse("captura:resolver_bandeja"),
        bandeja=bandeja,
        error=error,
    )
    if bandeja is None:
        return render(request, "captura/buscar_bandeja.html", contexto)

    asignacion = _asignacion_abierta(bandeja)
    if asignacion:
        servicio = asignacion.servicio
        if servicio.estado_captura == Estado.PENDIENTE_SERVIDO:
            contexto["error"] = "Este servicio aún no tiene la fotografía del servido. Continúa su captura."
            contexto["continuar_url"] = reverse("captura:foto_servido", args=[servicio.pk])
            contexto["continuar_texto"] = "Continuar foto del servido"
        else:
            contexto["error"] = "La bandeja está ocupada por otro servicio. Usa otra bandeja."
        return render(request, "captura/buscar_bandeja.html", contexto)

    form = ServicioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            servicio = Servicio.registrar(
                plato=form.cleaned_data["plato"],
                porcion=form.cleaned_data["tipo_porcion"],
                usuario=request.user,
                bandeja=bandeja,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            return redirect("captura:foto_servido", pk=servicio.pk)

    contexto.update(
        form=form,
        confirmar_url=f"{reverse('captura:resolver_bandeja')}?{consulta}",
    )
    return render(request, "captura/buscar_bandeja.html", contexto)


@roles_required(REGISTRO)
@require_http_methods(["GET", "POST"])
def buscar_retorno(request):
    """Retorno. GET localiza el servicio en espera; POST confirma la correspondencia."""
    bandeja, consulta, error = _localizar_bandeja(request)
    contexto = _contexto_base(
        es_retorno=True,
        buscar_url=reverse("captura:buscar_retorno"),
        bandeja=bandeja,
        error=error,
    )
    if bandeja is None:
        return render(request, "captura/buscar_bandeja.html", contexto)

    asignacion = _asignacion_abierta(bandeja)
    if asignacion is None:
        contexto["error"] = "La bandeja no tiene un servicio esperando retorno. Puede estar libre o su servicio ya fue cerrado."
        contexto["continuar_url"] = reverse("captura:resolver_bandeja")
        contexto["continuar_texto"] = "Ir al registro de servido"
        return render(request, "captura/buscar_bandeja.html", contexto)
    if asignacion.servicio.estado_captura != Estado.EN_ESPERA_RETORNO:
        contexto["error"] = "Primero debes guardar la fotografía del servido; todavía no se puede registrar el retorno."
        if asignacion.servicio.estado_captura == Estado.PENDIENTE_SERVIDO:
            contexto["continuar_url"] = reverse("captura:foto_servido", args=[asignacion.servicio_id])
            contexto["continuar_texto"] = "Continuar foto del servido"
        return render(request, "captura/buscar_bandeja.html", contexto)
    servicio = asignacion.servicio

    form = ConfirmarRetornoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        return redirect("captura:foto_retorno", pk=servicio.pk)

    contexto.update(
        servicio=servicio,
        plato_nombre=servicio.get_plato_display(),
        porcion_nombre=servicio.get_tipo_porcion_display(),
        form=form,
        confirmar_url=f"{reverse('captura:buscar_retorno')}?{consulta}",
    )
    return render(request, "captura/buscar_bandeja.html", contexto)


def _capturar(request, pk, etapa, estado_esperado, sesion=None, token=None):
    """Lógica común de foto_servido y foto_retorno."""
    servicio = get_object_or_404(Servicio, pk=pk)
    bandeja = _bandeja_del_servicio(servicio)
    nombre_vista = "captura:foto_servido" if etapa == Etapa.SERVIDO else "captura:foto_retorno"
    contexto = _contexto_base(
        servicio=servicio,
        bandeja=bandeja,
        etapa=etapa,
        es_retorno=etapa == Etapa.RETORNO,
        plato_nombre=servicio.get_plato_display(),
        porcion_nombre=servicio.get_tipo_porcion_display(),
    )

    # Si la etapa ya no está pendiente, se muestra el estado real (sin formulario).
    if servicio.estado_captura != estado_esperado:
        if not servicio.estado_captura:
            raise Http404("Servicio histórico sin captura.")
        if etapa == Etapa.RETORNO and servicio.estado_captura == Estado.PENDIENTE_SERVIDO:
            contexto["error"] = "Primero debe registrarse la fotografía del servido."
        contexto["estado"] = servicio.estado_captura
        contexto["fotografias_registradas"] = servicio.fotografias.filter(vigente=True)
        contexto["continuar_url"] = reverse("captura:resolver_bandeja")
        return render(request, "captura/estado_servicio.html", contexto)

    form = FotoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        imagen = form.cleaned_data["foto"]
        clave = storage.generar_clave(servicio.pk, etapa, imagen.extension)

        # 1) Guardar el archivo FUERA de cualquier transacción de base de datos.
        try:
            carga = limpieza.registrar_carga(clave)
            guardado = storage.guardar(imagen.contenido, clave, tipo_contenido=imagen.tipo)
        except storage.ArchivoExistente:
            from django.utils import timezone
            carga.resuelta_en = timezone.now()
            carga.resultado = "colision"
            carga.save(update_fields=["resuelta_en", "resultado"])
            form.add_error(None, "No se pudo asignar el archivo. Inténtalo de nuevo.")
        except storage.ErrorAlmacenamiento:
            form.add_error(None, "No se pudo guardar la fotografía. Inténtalo de nuevo.")
        else:
            # 2) Registrar metadatos y avanzar el estado (transacción de Isaac).
            try:
                carga.version_id = guardado.version_id
                carga.save(update_fields=["version_id"])
                registrar = services.registrar_captura if sesion is None else services.consumir_sesion
                destino = {"servicio": servicio, "etapa": etapa} if sesion is None else {"token": token}
                registrar(
                    **destino,
                    checklist=form.confirmaciones(),
                    clave_archivo=guardado.clave,
                    tipo_contenido=imagen.tipo,
                    tamano_bytes=imagen.tamano,
                    ancho=imagen.ancho,
                    alto=imagen.alto,
                    autor=request.user,
                    backend=guardado.backend,
                    hash_sha256=guardado.hash_sha256,
                    version_id=guardado.version_id,
                )
            except Exception as exc:
                # 3) Compensación: la BD rechazó, se borra el archivo huérfano.
                try:
                    storage.eliminar(guardado.clave, backend=guardado.backend, version_id=guardado.version_id)
                except storage.ErrorAlmacenamiento:
                    # Registro operativo para reintentar la limpieza; sin token ni
                    # nombre de archivo del cliente. Nunca mostrar éxito al fallar.
                    logger.error("EVA_CAPTURE_ORPHAN backend=%s clave=%s version=%s",
                                 guardado.backend, guardado.clave, guardado.version_id)
                if not isinstance(exc, ValidationError):
                    raise
                servicio.refresh_from_db()
                if servicio.estado_captura != estado_esperado:
                    # Doble clic o reintento: la primera captura ya fue aceptada.
                    return redirect(nombre_vista, pk=servicio.pk)
                form.add_error(None, exc)
            else:
                if sesion is not None:
                    return redirect(request.get_full_path())
                return redirect(nombre_vista, pk=servicio.pk)

    if etapa == Etapa.RETORNO:
        foto_servido = _foto_vigente(servicio, Etapa.SERVIDO)
        if foto_servido and foto_servido.disponible:
            contexto["foto_servido_url"] = reverse("captura:imagen", args=[foto_servido.pk])
            contexto["fecha_servido"] = foto_servido.fecha
        elif foto_servido:
            contexto["foto_servido_retenida"] = True

    contexto.update(form=form, guardar_url=reverse(nombre_vista, args=[servicio.pk]),
                    vincular_url=reverse("captura:vincular", args=[servicio.pk, etapa]))
    if sesion is not None:
        contexto.update(guardar_url=request.get_full_path(), vincular_url=None,
                        vinculo_vigente=True, estado=sesion.estado)
        return render(request, "captura/captura_vinculada.html", contexto)
    return render(request, "captura/fotografia.html", contexto)


@roles_required(REGISTRO)
@require_http_methods(["GET", "POST"])
def foto_servido(request, pk):
    return _capturar(request, pk, Etapa.SERVIDO, Estado.PENDIENTE_SERVIDO)


@roles_required(REGISTRO)
@require_http_methods(["GET", "POST"])
def foto_retorno(request, pk):
    return _capturar(request, pk, Etapa.RETORNO, Estado.EN_ESPERA_RETORNO)


@roles_required(REGISTRO)
@require_GET
def imagen(request, pk):
    """Entrega los bytes de una foto solo a usuarios con rol Registro."""
    foto = get_object_or_404(FotografiaServicio, pk=pk)
    if not foto.disponible:
        respuesta = HttpResponse("Fotografía no disponible por retención de 90 días. El historial se conserva.", status=410)
        respuesta["Cache-Control"] = "private, no-store"
        return respuesta
    try:
        archivo = storage.abrir(foto.clave_archivo, backend=foto.backend, version_id=foto.version_id)
    except storage.ArchivoNoEncontrado:
        raise Http404("Fotografía no disponible.")
    except storage.ErrorAlmacenamiento:
        return HttpResponse("No se pudo consultar la fotografía. Inténtalo de nuevo.", status=503)
    respuesta = FileResponse(archivo, content_type=foto.tipo_contenido)
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["Content-Length"] = foto.tamano_bytes
    return respuesta
