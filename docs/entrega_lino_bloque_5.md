# Bloque 5: vistas y decisiones de Cocina conectadas

Esta rama sustituye la segunda parte de Lino. Se apoya en la rama del bloque 4 y
combina, conservando autoría/historial, las dependencias #38 de Isaac (762a510),
#35 de Jean (18cab5f) y #37 de Eduardo (8b7a47b). Sus merges en esta rama NO son
merges a main. Se conservaron las guardas del #39 contra totales parciales y fotos
eliminadas. Los conflictos de combinación se resolvieron conservando ambas partes.

## Recorrido y contratos

- Cocina entra por `/analisis/revision/`. El login y la ruta provisional existente
  encuentran la ruta real sin cambiar la prioridad de Registro para cuentas mixtas.
- `/analisis/` conserva los pares por analizar y resultados, con paginación. Los
  completados enlazan a revisión; los demás a detalle/estado/reintento del bloque 4.
- La cola de revisión muestra resultados vigentes sin revisión. Los contadores
  cuentan servicios distintos, no componentes, y separan SIMULADO de REAL.
- `/analisis/revision/<analisis>/` conecta el DTO con la plantilla de Jean: fotos,
  máscaras transparentes, colores estables, resultado, revisión vigente e historial.
- POST `/analisis/revision/<analisis>/<intento>/decidir/` incluye el intento exacto
  en la URL; no aprueba otro intento porque cambió el resultado desde el GET.

Decision conserva CONFIRMADO/RECHAZADO/NO_CONCLUYENTE. Motivo es un solo campo,
máximo 1000 caracteres. El formulario del servidor valida decisión, versión y
motivo; el dominio exige motivo también para rectificar. Un envío idéntico se
reconoce como repetición, no crea una revisión adicional. Un conflicto de versión
o bloqueo concurrente SQLite devuelve 409, sin reintentar escrituras a ciegas.

Los formularios GET no escriben. POST requiere CSRF, cuenta activa, rol Cocina y
permiso add_revisionanalisis; solo Registro o Administración reciben 403. Tras
migrar se debe ejecutar configurar_roles para sincronizar los permisos reales.

## Confirmar con evidencia disponible

La vista comprueba pertenencia al caso, vigencia, protocolo, edad, disponibilidad
física, dimensiones, formatos y huellas de las fotos y de las dos máscaras por
componente. No confía en evidencia_disponible, origen, porcentaje o permisos del
POST. Luego llama a revisar_resultado con la comprobación del servidor, y el
dominio aplica la regla de elegibilidad de César sobre criterios históricos.

SIMULADO, no concluyente, configuración sin aprobación, evidencia ausente o un
resultado anterior al actual no se convierten en evidencia apta por una decisión.
La fecha de retención puede bloquear nuevas confirmaciones sin borrar una revisión
válida anterior. Rechazar o marcar no concluyente sigue permitido con motivo cuando
corresponde; no cambia el resultado técnico original.

Las revisiones sustituidas conservan autor, fecha, motivo y versión. El historial
se presenta bajo el formulario. Los errores conservan el motivo como borrador
escapado para copiarlo; las plantillas originales de Jean se extienden sin editar
sus archivos ni duplicar sus pantallas. Se documenta la URL más específica del POST
como ampliación del contrato anterior para fijar el intento exacto.

## Pruebas y ensayo operativo aislado

Pruebas cubren confirmación idempotente, rectificación, versión obsoleta, roles,
CSRF, GET sin escritura, motivo sin JavaScript, límites, escape de texto, evidencia
faltante/alterada/vencida, SIMULADO, contadores y navegación. Los tests antiguos
de destino provisional se aislaron donde no hay rutas, y el recorrido real de login
ahora espera la ruta integrada de Cocina.

Ensayo reproducible: `python ops/analisis/smoke_integracion.py`. Usa su propia
carpeta temporal, SQLite, settings y fotografías sintéticas, con motor HTTP local
SIMULADO. Ejecuta realmente el supervisor y proceso hijo Django, no un doble de
Popen: solicitud HTTP -> cola -> llamada HTTP autenticada -> máscaras/resultados
persistidos -> gateways privados -> revisión -> confirmación simulada bloqueada
-> rechazo guardado. No usa AWS ni la base operativa. No prueba calidad del modelo.

La verificación final completa aprobó 341 pruebas Django y 36 JavaScript, además
del ensayo aislado con worker real. Check sin problemas, migraciones sin cambios
inesperados y diff --check limpio. Migraciones:
solo la 0002 de Isaac; no se generaron modelos de revisión duplicados.

## Integración y despliegue pendientes

1. Revisar/integrar el PR del bloque 4, esta entrega y las dependencias 5 en orden.
2. Actualizar la demo con respaldo, migrate, configurar_roles y collectstatic.
3. Configurar endpoint/token/modelo y aprobar criterios cuando exista evaluación;
   instalar/activar el servicio del worker solo en el despliegue autorizado.
4. Probar HTTPS, permisos aislados, S3 y limpieza en el servidor real. Revisar
   Figma móvil/escritorio y el protocolo de comparabilidad con evidencia propia.

No se hizo merge a main ni despliegue AWS desde estas dos entregas. No hay motor
REAL operativo ni precisión acreditada; las imágenes, pesos y evaluación siguen
pendientes. Los bloques 6 y 7 y el cierre final continúan fuera de este trabajo.
