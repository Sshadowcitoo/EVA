# Interfaz de recomendaciones, decisiones y pruebas

Base: base-recomendaciones-bloque-7, commit
061f1fef62e878d40403c28023f162d90ca947e2. Contrato v1 conservado.
Rama: interfaz-recomendaciones-bloque-7.

## Pantallas

Listado por filtros históricos, categoría, decisión y suficiencia; contadores de
TODO el alcance y paginación independiente. Los contadores pueden solaparse y
cuentan evaluaciones, no servicios. Opciones del servidor incluyen la historia,
sin reconstruirla desde el catálogo actual. Consultar reinicia la página.

Administración dispone en el listado de un formulario separado para evaluar
un periodo completo y una versión de criterios. La ausencia de versión se envía
como None; no se aprueban parámetros ni se fabrica suficiencia desde el navegador.
Los identificadores DOM de ambos formularios son distintos para conservar la
asociación accesible entre etiquetas, campos y errores, sin cambiar nombres POST.

El detalle presenta periodo, origen, vigencia, muestra/exclusiones, indicadores,
grupos separados, chequeos de condiciones, snapshot JSON de criterios y referencias
exactas al intento/revisión. Los números se presentan a dos decimales; no se usan
para decidir categorías. None es No disponible y un cero confirmado sigue siendo cero.

La propuesta solo aparece cuando existe en el DTO. Generar es un POST separado,
según capacidad del servidor. Evidencia insuficiente expone motivos sin una propuesta
de ajuste ni un MANTENER artificial. Evidencia desactualizada conserva el snapshot
y advierte antes de una nueva decisión.

Las decisiones tienen justificación obligatoria, control de versión, estado actual
e historial con autor/fecha y referencia sustituida. Aceptar no modifica catálogo,
receta, porción, inventario ni precios. El texto de Cocina y el de Administración
mantienen separadas la revisión de mediciones y la decisión sobre la recomendación.

La prueba controlada recoge cambio, responsable elegido de opciones y periodos
ordenados. Su detalle distingue REGISTRADA (todavía sin evaluar), EVALUADA y
NO_EVALUABLE, muestra la aceptación vinculada y consume la comparación ya calculada
del bloque 6. Una comparación ausente no equivale a mejora de cero puntos; se
muestran tamaños, exclusiones, compatibilidad y límites sin atribución causal.

## Acciones, errores y seguridad

Cocina consulta. Administración además evalúa, genera, decide, registra y evalúa
pruebas. Registro, staff sin rol e inactivos no heredan accesos. Se mantienen
roles múltiples y la excepción existente de superusuario. Los decoradores autorizan
TODOS los endpoints y los servicios reciben request.user y el UUID de la URL.
Los POST no aceptan cifras, suficiencia, identidades ni URLs del navegador como evidencia.

Las capacidades del DTO controlan las acciones del detalle, junto con el acceso
administrativo real. El backend conserva autorización, vigencia, transacciones e
idempotencia. El listado no tiene un DTO de capacidades; el acceso a evaluar se
rige por el rol explícito del contrato, sin inventar campos nuevos.

GET nunca escribe. POST requiere CSRF. never_cache protege respuestas con decisiones
y responsables. Los textos y el JSON de criterios se presentan escapados. Las
referencias se muestran como identificadores; no se inventa una ruta de imágenes
ni se da acceso a Cocina a Administración sola.

ParametrosInvalidos/ValidationError: 400 con entradas conservadas. CasoNoDisponible:
404. BackendRecomendacionesNoDisponible: 503 explícito, sin fixtures ni éxitos falsos.
ConflictoRecomendacion/EvidenciaDesactualizada: 409 con borrador conservado y acciones
bloqueadas hasta recargar y decidir de nuevo. Si no se puede leer el estado actualizado,
se conserva el 409 y el borrador. No se reintentan escrituras automáticamente.
Si faltan opciones durante un 503, las selecciones enviadas se muestran como borrador;
no se procesan operaciones usando esas opciones provisionales.

Los estados válidos de insuficiencia y no evaluable devuelven 200. Las excepciones
inesperadas no se convierten en listas vacías ni recomendaciones exitosas.
JavaScript solo evita un segundo envío accidental, muestra envío pendiente y
restaura el formulario al volver con el navegador; no calcula ni decide.

## Presentación y Figma

Se reutilizan la base visual del proyecto y los parciales de indicadores/resumen
del bloque 6, sin modificarlos. Los estilos propios están acotados a recomendaciones;
formularios y métricas pasan a una columna en móvil y las tablas tienen desplazamiento
propio accesible con teclado. Se conservan encabezados, foco visible y errores asociados.

Referencia: https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA
La comparación con Figma sigue PENDIENTE hasta disponer de acceso funcional o
exportaciones autorizadas. No se han verificado nodos de recomendaciones/móvil ni
se acredita el objetivo aproximado del 70 %. Las capturas de esta entrega verifican
su implementación, no el parecido con marcos no consultados.
