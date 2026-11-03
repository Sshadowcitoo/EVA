# Bloque 7: contrato v1 de recomendaciones, decisiones y pruebas

Base: main fb1e0684e48c80efbf97d4edf5aed90a9412cbfe, bloque 6 integrado.
Rama: `base-recomendaciones-bloque-7`. Nombres ejecutables en
`apps/recomendaciones/contracts.py`, CONTRACT_VERSION=1. El dominio implementa consultas y persistencia. Ver `docs/dominio_bloque_7.md`
para configuración, auditoría y límites de suficiencia.

## Responsabilidades

Dominio e integración: contracts.py, filtros.py, models.py, services.py, selectors.py,
apps.py, migrations/, testing/fixtures.py y test_contrato_*/test_dominio_*. Configuración,
roles compartidos, navegación común e include global también se integran desde ahí.

Interfaz: forms.py, views.py, urls.py, presenters.py si hace falta,
templates/recomendaciones/*, static/css/recomendaciones.css,
static/js/recomendaciones.js, test_web_*/test_interfaz_* y
tests/frontend/recomendaciones*.test.cjs. Documentos: interfaz_bloque_7.md y
entrega_web_bloque_7.md. No modificar archivos de dominio, migraciones o bloques
anteriores por cuenta propia ni cambiar las firmas unilateralmente.

## Operaciones públicas

Importar `from apps.recomendaciones import services` y llamar por atributo.
Todas las operaciones de datos reciben el usuario autenticado, no un ID del POST.

| Función | Retorno |
| --- | --- |
| normalizar_filtros(datos) | FiltrosRecomendaciones |
| normalizar_periodo_evaluacion(datos) | FiltrosHistorico, con ambas fechas |
| normalizar_decision(datos) | dict(decision, justificacion, version_esperada) |
| normalizar_prueba(datos) | dict(cambio, responsable_id, periodos) |
| opciones_recomendaciones(usuario) | OpcionesRecomendaciones |
| consultar_recomendaciones(filtros, usuario, pagina=1) | ListaRecomendaciones |
| evaluar_evidencia(filtros, version_criterios, usuario) | DetalleCaso |
| obtener_evaluacion(evaluacion_id, usuario) | DetalleCaso |
| generar_recomendacion(evaluacion_id, usuario) | DetalleCaso |
| obtener_recomendacion(recomendacion_id, usuario) | DetalleCaso |
| decidir_recomendacion(recomendacion_id, decision, justificacion, usuario, version_esperada) | DetalleCaso |
| registrar_prueba(recomendacion_id, cambio, responsable_id, periodos, usuario) | DetallePrueba |
| obtener_prueba(prueba_id, usuario) | DetallePrueba |
| evaluar_prueba(prueba_id, usuario, version_esperada) | DetallePrueba |

Los normalizadores y las diez operaciones de datos están implementados con ORM.
Conservar el manejo de BackendRecomendacionesNoDisponible (503) para fallos de
integración; sus tests deben simularlo explícitamente. Las fixtures no son un
proveedor productivo y no se usan en services.

## Filtros y datos

Filtros del histórico: plato, componente, porcion, desde, hasta, hora_desde y
hora_hasta, con las mismas unidades, códigos, zona Ecuador y límites del bloque 6.
Origen solo REAL. No duplicar las fórmulas de ese bloque. Para el listado se añaden
categoria, decision y suficiencia opcionales. El DTO devuelve esos tres campos y
el filtro normalizado del histórico bajo `historico`. La página se pasa aparte.

Evaluar requiere un periodo completo (desde/hasta). `version_criterios` es la cadena
elegida entre las opciones del servidor o None si aún no hay ninguna. No se envían
umbrales, estado de aprobación, cifras de muestra o suficiencia desde el formulario.

Los DTO son diccionarios Python, nunca instancias ORM. Fechas conscientes de zona;
porcentajes/variaciones en Decimal y puntos porcentuales, sin redondear al decidir.
Todos los campos definidos se entregan; ausencias se representan con None o listas
vacías, sin ceros inventados. Datos sintéticos llevan solo_pruebas=True.

## Evaluación y suficiencia (RF-15/RF-16)

EvaluacionEvidencia contiene id, origen, solo_pruebas, suficiencia, filtros,
criterios, resumen, indicadores, grupos, chequeos, motivos, referencias,
evaluada_en, vigente y motivos_vigencia. Usa los DTO de muestra/indicadores/grupos
del bloque 6. Referencias fijan servicio_id, intento_id, revision_id y version_revision.

CriteriosEvaluados conserva versión, aprobación, descripción y un snapshot JSON
de parámetros. La interfaz solo lo presenta, no interpreta predicados. Parámetros
que deberá configurar el dominio: muestra_minima (servicios), periodos_minimos,
periodo_dias, presencia_t y cobertura_minima (estos dos en 0..100), calidad,
confianza, comparabilidad y reglas versionadas por categoría/prioridad. Una clave
ausente o sin aprobar no equivale a un criterio cumplido. La configuración real
empieza con versión None, aprobada=False y reglas vacías.

Chequeos explica cada condición: codigo, etiqueta, cumple, valor_texto,
exigido_texto y motivo. Incluir muestra, persistencia, calidad, confianza y
comparabilidad. Texto ausente es None, no 0. Suficiencia es SUFICIENTE/INSUFICIENTE.
Si falla o falta una condición, mostrar «Evidencia insuficiente» con motivos y no
proponer una acción de ajuste ni sustituir ese estado por MANTENER.

Conservar el conjunto completo de evidencia y los criterios realmente aplicados,
no solo las filas paginadas de una consulta. Un resultado rechazado o un intento
nuevo posterior desactualiza las nuevas decisiones sobre la evaluación; el snapshot
anterior se conserva. La evaluación repetida de la misma entrada/evidencia/versión
debe ser idempotente, no generar propuestas duplicadas.

El histórico registra contexto en nuevas capturas completas; los registros anteriores
siguen sin contexto. t y reglas reales permanecen sin aprobar. Ver
docs/motor_contexto_piloto.md: no reconstruir contexto ni aprobar fixtures por defecto.

## Recomendación y decisión humana (RF-17/RF-18)

Categorías exactas: MANTENER, REVISAR_PORCION, REVISAR_PREPARACION,
PRUEBA_CONTROLADA. Backend elige según reglas aprobadas; JavaScript no deduce una
categoría desde una cifra. Recomendacion contiene id, evaluacion_id, categoria,
explicacion y creada_en. Explicación incluye métricas, periodo y límites, sin
atribuir desagrado, sabor o exceso de porción como causa demostrada por una imagen.

DetalleCaso devuelve evaluacion, recomendacion nullable, decision_actual nullable,
historial_decisiones, version_esperada, capacidades y pruebas. Los getters por
evaluación/recomendación y las operaciones de evaluación/generación/decisión
devuelven esa misma estructura. El evaluador no genera automáticamente: la acción
generar solo existe para una evaluación suficiente, vigente, aprobada y REAL.

DecisionRecomendacion usa ACEPTADA/DESCARTADA/EN_OBSERVACION: son estados distintos
de CONFIRMADO/RECHAZADO de Cocina. Justificación obligatoria en las tres decisiones,
1..1000 caracteres. El registro conserva ID, autor_visible, fecha, versión y
sustituye_id. Rectificaciones crean otra entrada, sin borrar la anterior. Sin
decisión, version_esperada=0. Reenvío idéntico no duplica; versión antigua produce
conflicto. Aceptar NO modifica recetas, precios, porciones o catálogo.

Las capacidades vienen del servidor: puede_evaluar, puede_generar, puede_decidir,
puede_registrar_prueba y puede_ver_analisis. Sirven para mostrar acciones; el backend
vuelve a autorizar y comprobar vigencia en cada POST. Las vistas construyen las URLs
con reverse y el ID de la respuesta; no se aceptan URLs arbitrarias del navegador.
Administración sola no obtiene acceso a imágenes de Cocina por consultar métricas.

## Prueba controlada (RF-19)

Solo desde una recomendación aceptada y vigente. Formulario: cambio obligatorio
de hasta 1000 caracteres, responsable_id (usuario activo autorizado por las opciones)
y referencia_desde/referencia_hasta/intervencion_desde/intervencion_hasta. Las fechas
son días inclusivos; la intervención empieza después del último día de referencia.
`normalizar_prueba` devuelve periodos con esos cuatro campos como date. El backend
vuelve a verificar el responsable y la aceptación; no confía en su nombre del POST.

PruebaControlada incluye ID, recomendacion_id, aceptacion_id exacta, cambio,
responsable_id/nombre, periodos, registrada_por/en, evaluada_en, estado, version,
comparacion nullable, motivos y puede_evaluar. Estados REGISTRADA/EVALUADA/NO_EVALUABLE.
DetallePrueba combina caso y prueba. ResumenPrueba en la lista del caso omite la
comparación completa, pero mantiene ID/estado/cambio/responsable/fecha/versión.

La comparación reutiliza el contrato del bloque 6 y explicita el cambio de la
intervención. No saltar las guardas de porción/modelo/contexto para forzar un número;
si no hay diseño o datos comparables, NO_EVALUABLE, sin afirmar mejora o causalidad.
Sin evaluación aún: comparacion=None, estado REGISTRADA. Una evaluación no evaluable
no equivale a mejora de cero puntos. Repetir la misma creación no duplica pruebas.
Reevaluar usa version_esperada de la prueba y conserva resultados anteriores.

## Listado y navegación

ListaRecomendaciones: version_contrato, solo_pruebas, filtros, filas, paginacion y
resumen. Cada fila es una evaluación, con recomendación nullable, nombres del grupo,
suficiencia, categoría/decisión nullable, vigencia, n y fecha. Contar evaluaciones,
no los servicios que las sustentan. resumen contiene total, insuficientes,
sin_decision, en_observacion y obsoletas. sin_decision cuenta recomendaciones
existentes sin decisión; no evaluaciones insuficientes sin propuesta. Los contadores
pueden solaparse y usan todo el alcance filtrado. Páginas de 30, mínimo una vacía.

La interfaz entrega namespace recomendaciones y estas rutas relativas:

| Nombre | Ruta | Método / rol |
| --- | --- | --- |
| lista | vacía | GET Cocina/Administración |
| evaluar | evaluar/ | POST Administración |
| evaluacion | evaluaciones/<uuid:evaluacion_id>/ | GET Cocina/Administración |
| generar | evaluaciones/<uuid:evaluacion_id>/generar/ | POST Administración |
| detalle | <uuid:recomendacion_id>/ | GET Cocina/Administración |
| decidir | <uuid:recomendacion_id>/decidir/ | POST Administración |
| registrar_prueba | <uuid:recomendacion_id>/pruebas/ | POST Administración |
| prueba | pruebas/<uuid:prueba_id>/ | GET Cocina/Administración |
| evaluar_prueba | pruebas/<uuid:prueba_id>/evaluar/ | POST Administración |

POST de decisión envía decision, justificacion y version_esperada. POST de evaluar
prueba envía su version_esperada. IDs de objetivos vienen de la URL; usuario de
request.user. GET nunca genera, decide o evalúa una prueba. CSRF y autorización
reales, no solo botones ocultos. Registro solo no accede; is_staff no concede roles.
Mantener la excepción de superusuario del helper. Usar never_cache en las vistas
protegidas que muestran decisiones y responsables. El include global /recomendaciones/
y los enlaces compartidos se añaden al integrar; no editarlos en paralelo.

## Errores y pruebas

ParametrosInvalidos.errores y ValidationError: 400 con campos conservados/escapados.
BackendRecomendacionesNoDisponible: 503 sin datos/éxito ficticio. CasoNoDisponible:
404. ConflictoRecomendacion (incluye EvidenciaDesactualizada): 409, conservar borrador,
mostrar vigencia y pedir refrescar; no reintentar escrituras a ciegas. PermissionDenied:
403; sin sesión, login. Insuficiencia/NO_EVALUABLE válidos se muestran con 200.

Fixtures exclusivas de tests en testing/fixtures.py: opciones_fixture_recomendaciones(),
lista_fixture(vacia=False), evaluacion_fixture(escenario), detalle_fixture(escenario,
administracion=True) y prueba_fixture(estado, administracion=True). Escenarios:
insuficiente, configuracion_pendiente, sin_datos, suficiente/sin_propuesta,
sin_decision, aceptada, descartada, en_observacion, obsoleta y simulada, según función.
Todas las cifras/aprobaciones de esas muestras son contrafactuales de prueba.

Los tests web sustituyen explícitamente cada función que necesiten: en especial,
para probar 503 deben simular el getter correspondiente, no asumir que el dominio
seguirá sin implementar. Probar GET sin escritura, roles/CSRF, justificación sin JS,
versiones obsoletas, evidencia desactualizada, doble envío, periodos inválidos,
insuficiencia y comparación ausente. No importar fixtures desde código productivo.
No afirmar semejanza con Figma sin acceso o exportaciones; nodos aún por verificar.
