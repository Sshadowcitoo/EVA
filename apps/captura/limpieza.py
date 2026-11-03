"""Retención de bytes, conservando servicios, resultados y metadatos de auditoría."""
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from . import storage
from .models import CargaFotografia, FotografiaServicio

DIAS_RETENCION = 90
HORAS_CARGA_INCOMPLETA = 24


def registrar_carga(clave):
    backend = storage._backend(settings.EVA_STORAGE_BACKEND)
    storage._validar_clave(clave)
    destino = storage._prefijo() + clave if backend == "s3" else clave
    return CargaFotografia.objects.create(backend=backend, clave_archivo=destino)


def ejecutar(*, aplicar=False, limite=500, ahora=None):
    from apps.analisis.models import ArtefactoAnalisis
    ahora = ahora or timezone.now()
    fotos = FotografiaServicio.objects.filter(
        fecha__lte=ahora - timedelta(days=DIAS_RETENCION), eliminada_en__isnull=True,
    ).order_by("fecha", "pk")
    cargas = CargaFotografia.objects.filter(
        creada_en__lte=ahora - timedelta(hours=HORAS_CARGA_INCOMPLETA), resuelta_en__isnull=True,
    ).order_by("creada_en", "pk")
    mascaras = ArtefactoAnalisis.objects.filter(
        foto_padre__fecha__lte=ahora - timedelta(days=DIAS_RETENCION), eliminado_en__isnull=True,
    ).order_by("foto_padre__fecha", "pk")
    informe = dict(modo="aplicar" if aplicar else "simulacion", dias_retencion=DIAS_RETENCION,
                   horas_carga_incompleta=HORAS_CARGA_INCOMPLETA, limite_por_grupo=limite,
                   fotos_candidatas=fotos.count(), cargas_por_reconciliar=cargas.count(),
                   fotos_eliminadas=0, cargas_eliminadas=0, cargas_vinculadas=0, errores=0)
    informe["fotos_protegidas_por_referencia_reciente"] = 0
    informe.update(mascaras_candidatas=mascaras.count(), mascaras_eliminadas=0,
                   mascaras_protegidas_por_referencia_reciente=0)
    if not aplicar:
        return informe
    for foto in fotos[:limite]:
        if FotografiaServicio.objects.filter(
            backend=foto.backend, clave_archivo=foto.clave_archivo, eliminada_en__isnull=True,
            fecha__gt=ahora - timedelta(days=DIAS_RETENCION),
        ).exists():
            informe["fotos_protegidas_por_referencia_reciente"] += 1
            continue
        if ArtefactoAnalisis.objects.filter(
            backend=foto.backend, clave_archivo=foto.clave_archivo, eliminado_en__isnull=True,
            foto_padre__fecha__gt=ahora - timedelta(days=DIAS_RETENCION),
        ).exists():
            informe["fotos_protegidas_por_referencia_reciente"] += 1
            continue
        try:
            storage.eliminar(foto.clave_archivo, backend=foto.backend, version_id=foto.version_id)
        except storage.ErrorAlmacenamiento:
            FotografiaServicio.objects.filter(pk=foto.pk).update(
                limpieza_intentos=F("limpieza_intentos") + 1,
                limpieza_error="No se pudo eliminar el archivo; se reintentará en la siguiente ejecución.")
            informe["errores"] += 1
        else:
            FotografiaServicio.objects.filter(pk=foto.pk, eliminada_en__isnull=True).update(
                eliminada_en=ahora, limpieza_intentos=F("limpieza_intentos") + 1, limpieza_error="")
            informe["fotos_eliminadas"] += 1
    for mascara in mascaras[:limite]:
        reciente = ahora - timedelta(days=DIAS_RETENCION)
        if (FotografiaServicio.objects.filter(backend=mascara.backend, clave_archivo=mascara.clave_archivo,
                                             eliminada_en__isnull=True, fecha__gt=reciente).exists()
                or ArtefactoAnalisis.objects.filter(backend=mascara.backend, clave_archivo=mascara.clave_archivo,
                                                   eliminado_en__isnull=True, foto_padre__fecha__gt=reciente).exists()):
            informe["mascaras_protegidas_por_referencia_reciente"] += 1
            continue
        try:
            storage.eliminar(mascara.clave_archivo, backend=mascara.backend, version_id=mascara.version_id)
        except storage.ErrorAlmacenamiento:
            informe["errores"] += 1
        else:
            ArtefactoAnalisis.objects.filter(pk=mascara.pk, eliminado_en__isnull=True).update(eliminado_en=ahora)
            informe["mascaras_eliminadas"] += 1
    for carga in cargas[:limite]:
        # Cualquier referencia a esa clave protege el objeto, incluso no vigente.
        if (FotografiaServicio.objects.filter(backend=carga.backend, clave_archivo=carga.clave_archivo).exists()
                or ArtefactoAnalisis.objects.filter(backend=carga.backend, clave_archivo=carga.clave_archivo).exists()):
            CargaFotografia.objects.filter(pk=carga.pk).update(resuelta_en=ahora, resultado="vinculada", error="")
            informe["cargas_vinculadas"] += 1
            continue
        try:
            storage.eliminar(carga.clave_archivo, backend=carga.backend, version_id=carga.version_id)
        except storage.ErrorAlmacenamiento:
            CargaFotografia.objects.filter(pk=carga.pk).update(
                intentos=F("intentos") + 1, error="No se pudo limpiar la carga; se reintentará.")
            informe["errores"] += 1
        else:
            CargaFotografia.objects.filter(pk=carga.pk, resuelta_en__isnull=True).update(
                resuelta_en=ahora, resultado="eliminada", intentos=F("intentos") + 1, error="")
            informe["cargas_eliminadas"] += 1
    return informe
