# Cierre de la auditoría visual de EVA

Quedan 44 fichas con cambios visuales pendientes tras la entrega de Bandejas y etiquetas QR. Las entregas en PR borrador se consideran listas para revisión.

## Acceso (1)

- `404` · Ruta desconocida

## Captura (9)

- `servido-buscar` · Buscar bandeja para servido
- `servido-error` · Bandeja inexistente, entrada conservada
- `vinculo-invalido` · Vínculo inválido
- `retorno-buscar` · Buscar bandeja de retorno
- `servicio-404` · Servicio inexistente
- `qr-permiso` · Lector QR: cámara denegada
- `vinculada-completada` · Captura vinculada completada
- `vinculada-expirada` · Vínculo caducado
- `vinculada-cancelada` · Vínculo cancelado

## Análisis (9)

- `inicio-cocina-vacio` · Inicio Cocina / cola de revisión vacía
- `analisis-vacio` · Lista de análisis vacía
- `par-solicitar` · Par disponible para solicitar análisis
- `analisis-detalle` · Análisis completado
- `inicio-cocina` · Inicio Cocina / cola con resultados
- `analisis-no-concluyente` · Resultado no concluyente
- `analisis-cargando` · En Proceso
- `analisis-fallo` · Fallido
- `analisis-lista` · Lista de análisis con estados

## Histórico (7)

- `indicadores-vacio` · Indicadores sin registros
- `indicadores-admin` · Indicadores Administración con grupo de QA
- `indicadores-cocina` · Indicadores Cocina con grupo de QA
- `historico-tabla` · Tabla histórica de Cocina
- `historico-admin` · Tabla histórica de Administración
- `historico-filtro-error` · Filtros con fecha inválida
- `historico-comparar` · Comparar periodos / formulario

## Recomendaciones (12)

- `recom-vacio` · Listado sin evaluaciones
- `recom-insuficiente` · Evaluación con evidencia insuficiente
- `recom-lista-admin` · Listado y evaluación para Administración
- `recom-lista-cocina` · Listado de solo lectura para Cocina
- `recom-error` · Evaluación incompleta
- `recom-suficiente` · Evaluación suficiente · hipótesis QA
- `recom-decidir` · Decisión administrativa · hipótesis QA
- `recom-decision-error` · Decisión inválida · hipótesis QA
- `recom-decision-guardada` · Decisión guardada y alta de prueba · hipótesis QA
- `recom-detalle-cocina` · Detalle de solo lectura · hipótesis QA
- `prueba` · Prueba controlada registrada · hipótesis QA
- `prueba-evaluada` · Prueba no evaluable · hipótesis QA

## Percepción (3)

- `percepcion` · Percepción del comensal
- `percepcion-error` · Percepción con POST inválido
- `percepcion-guardada` · Percepción guardada

## Demostración (3)

- `demo-indicadores` · Demostración de Indicadores con datos
- `demo-indicadores-vacio` · Demostración de Indicadores sin aptos
- `demo-recomendaciones` · Demostración de recomendaciones

## Fuera del rediseño

Administración técnica de Django. Se conservan sus seis fichas de inventario como referencia.

El 404 general permanece en la lista de cierre. El 404 de una etiqueta revocada se verificó como estado funcional y conserva la página general pendiente.
