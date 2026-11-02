# Bloque 4: contrato compartido de César

Base revisada: main 1a2230635b32 y rama remota isaac-b4-modelos-analisis a6795ec48dc2, consulta 02/11/2026. La rama de Isaac está publicada; no había PR suyo abierto al consultar GitHub. Este contrato mantiene sus nombres; no implica merge de su trabajo ni validación del modelo.

## Propiedad y dependencias

- César: app registrada, configuración/permisos, este contrato, contrato del motor e integración.
- Isaac: AnalisisServicio, IntentoAnalisis, ResultadoComponente, ArtefactoAnalisis, migraciones y services.py. No necesita editar settings.py.
- Lino: cliente, worker, rutas/vistas y almacenamiento de artefactos.
- Eduardo: pruebas de integración y evidencias; preparar casos sin esperar, ejecutar integración tras integrar dependencias.
- Jean: disponibilidad confirmada para la interfaz de los bloques 4 y 5, con mapeo y comparación en Figma.

Desde la confirmación de disponibilidad, Jean tiene la propiedad de `templates/analisis/*`, `static/css/analisis.css` y `static/js/analisis.js`. César no editará esos archivos sin coordinarlo con él. Las bases ya publicadas en PR #32 y #33 se conservan como punto de partida; no duplicar ni descartar `revision.html` del bloque 5.

Jean puede partir de `cesar-b4-contratos-motor` en `jean-b4-interfaz-analisis`, con PR contra esa rama y dependencia explícita del #32. Para bloque 5: `jean-b5-interfaz-cocina`, basada en `cesar-b5-contratos-interfaz` (#33), llevando primero los cambios compartidos de su bloque 4. Tras integrar las dependencias, cambiar las bases de los PR a main. Jean abre los PR; César hace la integración.

No hacer merge de entregas propias: abrir PR con dependencias. Orden: base de César, modelos de Isaac, integración de Lino, pantallas conectadas y pruebas. `apps.py` de esta entrega reproduce el de Isaac para permitir registrar la app sin copiar sus modelos; Git puede integrar el archivo idéntico.

## Nombres y decisiones ratificadas

Se conservan AnalisisServicio.Origen REAL/SIMULADO y estados de IntentoAnalisis: PENDIENTE, EN_PROCESO, COMPLETADO, FALLIDO, TIEMPO_AGOTADO. ResultadoComponente: CONCLUYENTE / NO_CONCLUYENTE y sus motivos publicados por Isaac. No cambiar estado_captura para indicar análisis.

1. Porcentaje >100: conservar valor, NO_CONCLUYENTE/MAYOR_100; sin recorte automático.
2. Componente esperado ausente: NO_CONCLUYENTE/SIN_DETECCION; un componente ajeno al servicio o repetido invalida la respuesta completa.
3. Reintentar únicamente FALLIDO o TIEMPO_AGOTADO; nuevo intento, sin sobrescribir el anterior.
4. El presupuesto total de 30 s comienza al reclamar el worker: incluye lectura de archivos, llamada, validación y cierre. Es una decisión conservadora; reclamar no equivale literalmente al inicio de la llamada. Lino registra ambos tiempos y usa solo el presupuesto restante para la llamada. Una respuesta tardía no se acepta.
5. Las máscaras heredan 90 días desde su foto padre. `artefactos_vencidos()` es un selector, no una limpieza implementada.

## Confianza y comparabilidad

`EVA_ANALISIS_CRITERIOS` queda explícitamente SIN APROBACIÓN: umbrales vacíos, comparabilidad no aprobada, versión pendiente-evaluacion. `criterios_componente(codigo)` devuelve umbral None si falta configuración aprobada o el número es inválido. No inventar un 0.5/0.8 como umbral real. Los valores de tests son solo fixtures.

Isaac puede mantener umbral por parámetro y SIN_CRITERIO; Lino debe obtenerlo de esta configuración, nunca del POST del navegador o de una respuesta no confiable del motor. Se aprobarán por clase y versión después de evaluar preparaciones reales independientes, máscaras manuales, error en puntos porcentuales, IoU/Dice y proporción no concluyente.

Comparabilidad solo si hay protocolo/checklist de ambas fotos, calidad suficiente y transformación documentada a una misma región/escala del plato. El checklist actual declara encuadre/vista/luz; no demuestra por sí solo tolerancias o alineación. `comparable` se pasa explícitamente y debe ser False si falta evidencia o aprobación. No usar el valor por defecto True del dominio como certificación.

Antes de reclamar y antes de completar: fotos disponibles/no vencidas, par exacto, servicio no anulado, composición histórica y mismo modelo/configuración. Isaac debe reforzar estos guardas en su rama; su solicitud actual solo verifica par completo. El cierre debe comprobar estado y límite también dentro de la transición transaccional; una comprobación anterior no elimina una carrera con el vencimiento.

## Interfaz Django propuesta para Lino

namespace `analisis`: lista (GET), solicitar (POST por servicio), detalle/estado (GET por análisis), reintentar (POST por análisis), evidencia (GET de artefacto/foto vinculados al caso). Los includes globales se añaden cuando exista urls.py real; no publicar rutas que importen vistas inexistentes.

Roles: Cocina solicita/reintenta/consulta; Registro no hereda Cocina y Administración sola tampoco. `configurar_roles` sincroniza permisos de analisis después de migrar, sin crearlos artificialmente. No abrir globalmente captura:imagen: crear gateway de evidencia de análisis con autorización del caso.

Contexto de templates/analisis: `casos`, y detalle con `caso.plato_nombre`, `caso.porcion_nombre`, `caso.estado`, `caso.origen`, `caso.version_modelo`, `resultados` (componente, porcentaje_texto, confianza_texto, estado, motivo), `foto_servido_url`, `foto_retorno_url`, `error`, `solicitar_url`, `reintentar_url`. URLs ausentes deshabilitan acciones; porcentajes nulos se representan “No concluyente”, nunca 0. Las máscaras se entregan mediante URLs autorizadas, no claves S3.

### Ampliación opcional ratificada para la interfaz de Jean (PR #34)

Estos datos no son nuevas columnas obligatorias ni bloquean el renderizado. Lino construye el contexto a partir de los registros autorizados; no acepta porcentajes, permisos o URLs de evidencia enviados por el navegador.

| Dato | Semántica y ausencia |
| --- | --- |
| `caso.bandeja_numero` | Número del soporte físico asociado históricamente a ese servicio, no su asignación actual. Ausente: guion. Rotular **Bandeja**, no Registro: el soporte se reutiliza. |
| `caso.servicio_id` | UUID del servicio para distinguir varios usos de una bandeja; conservar la identificación única en detalle y acciones. No sustituirlo por bandeja_numero. |
| `caso.intento_numero` | Número del intento que se está mostrando, entero positivo; ausente: omitir. |
| `caso.duracion_texto` | Texto legible derivado de duracion_ms del mismo intento, nunca inventar 0 s cuando sea nulo. Ausente: omitir. |
| `resumen.por_revisar` | Conteo de servicios distintos con resultado vigente completado REAL y revisión humana pendiente, dentro del mismo alcance/filtros que la lista. Ausente/None: Sin datos. Cero solo si la consulta real devuelve cero. |
| `resumen.no_concluyentes` | Servicios distintos del mismo alcance con algún resultado vigente NO_CONCLUYENTE. No sumar componentes como si fueran servicios. Puede solaparse con por_revisar; las tarjetas no son categorías disjuntas. Ausente/None: Sin datos. |
| `historial_url` | Enlace interno autorizado a una pantalla ya implementada. Ausente: Pendiente de conexión. No obliga a implementar histórico dentro del bloque 4. |
| `mascaras` | Lista opcional `[{url, componente, etapa}]`; etapa solo SERVIDO/RETORNO. URL privada autorizada de una máscara de ese caso y foto padre, con geometría compatible. Sin elementos: sin superposición. |
| `estado_url` | URL relativa del mismo origen, autorizada por caso; GET JSON `{"estado":"PENDIENTE|EN_PROCESO|COMPLETADO|FALLIDO|TIEMPO_AGOTADO"}`. La notación indica alternativas, no un valor literal. Ausente: recarga manual. |

Los conteos de SIMULADO se omiten de estas tarjetas o se muestran en un resumen separado y explícitamente rotulado; no mezclarlos con evidencia real. Si Lino aún no implementó una consulta o permiso, omite el dato: una tarjeta sin datos no es un cero demostrado.

Máscaras operativas y visualización: preservar la máscara original. Para superponer sobre la foto, entregar una representación PNG con fondo transparente, alineada con su foto padre. Acordar color estable por componente y leyenda coincidente; no asignar colores solo según la posición de la fila ni superponer un PNG opaco que tape el plato. La conversión de visualización no altera las áreas del resultado ni reinicia la retención.

Consulta automática a cargo de Jean: mismo origen, `cache: no-store`, autorización en servidor, rechazo de redirecciones y validación de los cinco estados. Añadir AbortController con límite por petición y plazo total; veinte consultas no garantizan 60 s si un fetch queda abierto. Detener/abortar al ocultar o cerrar la página y al terminar; mostrar error/reintento manual ante pérdida de sesión o red, sin anunciar éxito ni recargar por un estado desconocido. El límite de consulta de la UI es independiente del plazo de 30 s del worker. Pruebas de JavaScript deben cubrir estas condiciones, además de las de plantilla.

## Motor y respuesta v1

Propuesto `POST /v1/analizar-par`, autenticación interna configurada por César, solo endpoint permitido desde configuración del servidor. Enviar multipart con fotos operativas JPEG/PNG y campo metadata JSON: schema_version=1, request_id UUID del intento, servicio_id, version_modelo, version_configuracion y componentes [{id,codigo}] de Servicio.composicion.

Respuesta JSON acotada: schema_version, request_id, version_modelo, origen, componentes [{id, area_inicial, area_residual, confianza, comparable, oculto, mascaras:[{etapa, png_base64, ancho, alto}]}]. No aceptar URLs remotas, rutas del sistema, componentes ajenos, NaN/infinito, confianza fuera de [0,1] o dimensiones incoherentes. Declarar transformación/ROI que justifica áreas comparables. Lino fija límites de respuesta y valida bytes PNG antes de almacenarlos.

El motor no decide roles, confianza aprobada ni revisión humana. Si falta una máscara o no se puede establecer ausencia evaluable, no inventa residuo cero. La respuesta de un adaptador SIMULADO mantiene ese origen y nunca se convierte en REAL por configuración del cliente.

`EVA_VISUAL_ENDPOINT` y `EVA_VISUAL_VERSION_MODELO` están vacíos a propósito: no hay pesos ni entorno de inferencia validado. Esta entrega no instala YOLO/OpenCV ni simula que el motor real existe. Su implementación y evaluación siguen bloqueadas por imágenes, pesos y elección del entorno. Nunca entrenar en la EC2 pequeña por defecto ni crear recursos de pago sin autorización.

## Persistencia y retención

Un resultado se publica solo tras guardar todas sus máscaras y metadatos; compensar/reconciliar fallos. La cola CargaFotografia y la limpieza actual solo reconocen fotos. Antes de reutilizarlas para máscaras, Lino debe extender referencias a ArtefactoAnalisis o usar una cola específica; de lo contrario se borrarían como huérfanas a las 24 h. Fotos/máscaras vencidas: no lectura privada, historial conservado.

Cierre: check, suite, migraciones sin cambios no esperados, prueba de timeout real, permisos aislados, duplicados, retención y recorrido completo. Esta base desbloquea implementación; no acredita IA validada ni bloque 4 terminado.
