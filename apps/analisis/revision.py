"""Comprobación de evidencia al decidir: fechas, pertenencia, bytes y huellas."""
from django.core.exceptions import ValidationError
from apps.captura import storage
from . import evidencia


def evidencia_disponible(analisis, intento):
    fotos = {'SERVIDO': analisis.foto_servido, 'RETORNO': analisis.foto_retorno}
    try:
        for foto in fotos.values():
            if not evidencia.protocolo_completo(foto):
                return False
            evidencia.foto_bytes(foto)
        esperados = set(analisis.servicio.composicion.values_list('pk', flat=True))
        resultados = list(intento.resultados.prefetch_related('artefactos'))
        if not esperados or {r.servicio_componente_id for r in resultados} != esperados:
            return False
        for resultado in resultados:
            artefactos = list(resultado.artefactos.all())
            if len(artefactos) != 2 or {a.etapa for a in artefactos} != set(fotos):
                return False
            for art in artefactos:
                padre = fotos[art.etapa]
                if art.foto_padre_id != padre.pk or art.eliminado_en is not None:
                    return False
                datos = evidencia.leer(art, evidencia.MAX_MASCARA)
                evidencia.mascara(datos, padre)
    except (ValidationError, storage.ErrorAlmacenamiento):
        return False
    return True
