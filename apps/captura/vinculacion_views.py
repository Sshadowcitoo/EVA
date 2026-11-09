"""Vinculación temporal: sesión autenticada y CSRF también en el teléfono."""
import base64
from io import BytesIO

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalogo.permissions import REGISTRO, roles_required
from . import services, views
from .models import Servicio, SesionCaptura


def _actualizar(sesion):
    if sesion.estado == SesionCaptura.Estado.PENDIENTE:
        if sesion.expira_en <= timezone.now():
            estado = SesionCaptura.Estado.EXPIRADA
        elif sesion.servicio.estado_captura != services._ESTADO_REQUERIDO[sesion.etapa]:
            estado = SesionCaptura.Estado.CANCELADA
        else:
            return
        SesionCaptura.objects.filter(pk=sesion.pk, estado=SesionCaptura.Estado.PENDIENTE).update(estado=estado)
        sesion.refresh_from_db()


@never_cache
@roles_required(REGISTRO)
@require_http_methods(["GET", "POST"])
def vincular(request, pk, etapa):
    servicio = get_object_or_404(Servicio, pk=pk)
    if etapa not in views.Etapa.values:
        raise Http404
    resultado = reverse("captura:foto_servido" if etapa == views.Etapa.SERVIDO else "captura:foto_retorno", args=[pk])
    contexto = views._contexto_base(servicio=servicio, etapa=etapa,
        bandeja=views._bandeja_del_servicio(servicio), plato_nombre=servicio.get_plato_display(),
        porcion_nombre=servicio.get_tipo_porcion_display(), crear_url=request.path, resultado_url=resultado)
    if request.method == "POST":
        try:
            sesion, token = services.crear_sesion_captura(servicio=servicio, etapa=etapa, usuario=request.user)
        except ValidationError as error:
            contexto["error"] = " ".join(error.messages)
        else:
            origen = settings.EVA_CAPTURE_BASE_URL.rstrip("/") or request.build_absolute_uri("/").rstrip("/")
            enlace = origen + reverse("captura:captura_vinculada") + "?" + urlencode({"token": token})
            imagen = qrcode.make(enlace, image_factory=qrcode.image.svg.SvgPathImage, border=4)
            salida = BytesIO()
            imagen.save(salida)
            contexto.update(estado=sesion.estado, caduca_en=sesion.expira_en.isoformat(),
                captura_url=enlace, qr_url="data:image/svg+xml;base64," + base64.b64encode(salida.getvalue()).decode(),
                estado_url=reverse("captura:estado_vinculacion", args=[sesion.pk]),
                cancelar_url=reverse("captura:cancelar_vinculacion", args=[sesion.pk]))
    response = render(request, "captura/vincular_celular.html", contexto)
    response["Referrer-Policy"] = "same-origin"
    return response


@never_cache
@roles_required(REGISTRO)
@require_GET
def estado(request, pk):
    sesion = get_object_or_404(SesionCaptura.objects.select_related("servicio"), pk=pk)
    _actualizar(sesion)
    datos = {"estado": sesion.estado}
    if sesion.estado == SesionCaptura.Estado.COMPLETADA and sesion.fotografia_id:
        datos["foto_url"] = reverse("captura:imagen", args=[sesion.fotografia_id])
    return JsonResponse(datos)


@never_cache
@roles_required(REGISTRO)
@require_POST
def cancelar(request, pk):
    sesion = get_object_or_404(SesionCaptura, pk=pk)
    try:
        services.cancelar_sesion(sesion=sesion)
    except ValidationError:
        pass  # Reintentar una cancelación nunca modifica una captura aceptada.
    return redirect("captura:vincular", pk=sesion.servicio_id, etapa=sesion.etapa)


@never_cache
@roles_required(REGISTRO)
@require_http_methods(["GET", "POST"])
def capturar(request):
    token = request.GET.get("token", "")
    try:
        if len(token) != 43:
            raise ValidationError("Vínculo no válido.")
        sesion = services.obtener_sesion(token=token)
    except ValidationError:
        return render(request, "captura/captura_vinculada.html",
                      views._contexto_base(vinculo_invalido=True), status=404)
    _actualizar(sesion)
    if sesion.estado != SesionCaptura.Estado.PENDIENTE:
        return render(request, "captura/captura_vinculada.html",
                      views._contexto_base(estado=sesion.estado, vinculo_vigente=False))
    return views._capturar(request, sesion.servicio_id, sesion.etapa,
                          services._ESTADO_REQUERIDO[sesion.etapa], sesion=sesion, token=token)
