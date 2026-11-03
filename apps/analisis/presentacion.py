"""DTO de la interfaz de Jean; sin claves privadas ni cifras del navegador."""
from django.urls import reverse
from .evidencia import color_clave


def contexto(analisis, intento):
    servicio = analisis.servicio
    asignacion = servicio.asignaciones.select_related('bandeja').order_by('-inicio').first()
    caso = dict(plato_nombre=servicio.get_plato_display(), porcion_nombre=servicio.get_tipo_porcion_display(),
                servicio_id=str(servicio.pk), estado=intento.estado if intento else 'PENDIENTE',
                origen=analisis.origen, version_modelo=analisis.version_modelo,
                bandeja_numero=asignacion.bandeja.numero if asignacion else None,
                intento_numero=intento.numero if intento else None,
                duracion_texto=f'{intento.duracion_ms / 1000:.2f} s' if intento and intento.duracion_ms is not None else None)
    resultados, mascaras = [], []
    if intento and intento.estado == 'COMPLETADO':
        for resultado in intento.resultados.select_related('servicio_componente').prefetch_related('artefactos'):
            comp = resultado.servicio_componente
            resultados.append(dict(componente=comp.componente_nombre, estado=resultado.estado, motivo=resultado.motivo,
                                   porcentaje_texto=f'{resultado.porcentaje:.2f} %' if resultado.estado == 'CONCLUYENTE' and resultado.porcentaje is not None else 'No concluyente',
                                   confianza_texto=f'{resultado.confianza:.2%}' if resultado.confianza is not None else 'Sin dato',
                                   color_clave=color_clave(comp.componente_codigo)))
            for mascara in resultado.artefactos.all():
                if mascara.eliminado_en is None and mascara.foto_padre.disponible:
                    mascaras.append(dict(url=reverse('analisis:mascara', args=[analisis.pk, mascara.pk]),
                                         componente=comp.componente_nombre, etapa=mascara.etapa))
    datos = dict(caso=caso, resultados=resultados, mascaras=mascaras,
                 estado_url=reverse('analisis:estado', args=[analisis.pk]))
    for etapa, foto in [('servido', analisis.foto_servido), ('retorno', analisis.foto_retorno)]:
        if foto.disponible:
            datos['foto_' + etapa + '_url'] = reverse('analisis:foto', args=[analisis.pk, foto.pk])
    if intento and intento.estado in ('FALLIDO', 'TIEMPO_AGOTADO'):
        datos['reintentar_url'] = reverse('analisis:reintentar', args=[analisis.pk])
    return datos
