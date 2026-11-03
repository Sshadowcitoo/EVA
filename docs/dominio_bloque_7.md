# Dominio del bloque 7

Implementa las diez operaciones públicas del contrato v1. No modifica catálogo,
recetas ni porciones al aceptar una recomendación. No usa fixtures productivas.

## Persistencia

Migración `recomendaciones.0001_initial`: EvaluacionEvidencia (snapshot JSON tipado
con huella única), Recomendacion (una por evaluación), DecisionRecomendacion
(rectificaciones append-only, autor, fecha, versión y sustituye), PruebaControlada
(aceptación exacta, responsable, cambio y periodos), EvaluacionPrueba (historial
versionado de comparaciones). Todos los vínculos de auditoría usan PROTECT y no
hay permisos genéricos de edición/borrado. Los getters no escriben.

El snapshot conserva Decimal y date/time/datetime mediante serialización tipada.
El conjunto de referencias y las métricas proceden del selector completo del
histórico, no de sus primeras 30 filas. La huella incluye filtros, fuentes,
resultados, revisiones, grupos y configuración; una entrada idéntica reutiliza la
evaluación. Nuevos resultados, revisión, anulación, muestras o criterios distintos
vuelven obsoletas nuevas decisiones sobre la evaluación anterior, sin borrarla.

Escrituras con transaction.atomic, select_for_update y actualización condicional
de versión; restricciones únicas como última defensa. Conflicto de versión,
IntegrityError o bloqueo SQLite => 409, sin reintento ciego. Repetir una decisión
idéntica del mismo usuario con versión actual/anterior devuelve la misma entrada.
Cambiar de actor o contenido con versión antigua no se considera reenvío.

## Configuración pendiente, sin umbrales inventados

`EVA_RECOMENDACIONES_CRITERIOS` sigue sin aprobar por defecto. Su configuración
versionada consta de version (cadena), aprobada (bool), descripcion y reglas.
El siguiente es el esquema de reglas, no una aprobación de valores operativos:

- muestra_minima: entero positivo, servicios aptos por grupo y periodo.
- periodos_minimos y periodo_dias: enteros positivos. Bloques desde el primer día
  del filtro; solo cuentan los bloques completos con muestra mínima. No prueba
  causalidad ni independencia de preparaciones.
- presencia_t: decimal 0..100, debe coincidir con el t aprobado del histórico.
- cobertura_minima: porcentaje 0..100 de servicios aptos respecto a candidatos.
- calidad: REVISION_CONFIRMADA (selector valida fotos/protocolo/revisión real).
- confianza: decimal 0..1; mínimo de todos los componentes de los servicios aptos.
- comparabilidad: CONTEXTO_Y_GRUPO; un único grupo y contexto histórico conocido.
- categorias: lista ordenada de reglas con categoria y cuatro límites inclusivos:
  intensidad_desde/hasta, prevalencia_desde/hasta (0..100). Gana la primera regla
  aplicable. Una regla inválida invalida la selección; sin coincidencia no se genera.

Todas las condiciones y una regla aplicable deben cumplirse; faltar cualquier
criterio produce INSUFICIENTE y motivos. Las cifras de tests no son valores aprobados.
La configuración del histórico y la de recomendaciones no se confunden: sus
versiones son independientes y ambos criterios deben estar correctamente definidos.

**Límite actual:** el histórico aún no registra contexto. Por ello la evidencia
real sigue siendo insuficiente para generar propuestas, aunque haya resultados
confirmados. No se añadió un contexto ficticio ni se aprobaron umbrales para eludir
esa restricción. La prueba positiva habilita contexto hipotético solo dentro del
test y lo identifica explícitamente. Para operar propuestas reales falta acordar
y registrar contexto y aprobar criterios con evidencia.

## Pruebas controladas

Solo Administración escribe; Cocina consulta y puede ser responsable activo. No
se concede acceso por is_staff ni por conocer un UUID. Cada prueba queda ligada a
la aceptación exacta y a los periodos inclusivos validados sin solapamiento. Su
creación es idempotente por recomendación/aceptación/contenido. Cambiar la aceptación
bloquea evaluaciones nuevas de esa prueba. Reevaluar con versión actual agrega un
resultado sin borrar anteriores. Se reutiliza comparar_periodos del histórico:
si falta contexto, datos, t o diferencias comparables, NO_EVALUABLE, sin inventar
una mejora de cero. EVALUADA expresa comparación descriptiva, nunca causalidad.

## Coordinación de la interfaz

La interfaz del PR #47 conserva la propiedad de forms/views/urls/templates/static
propios. Las firmas y DTO públicos no cambian. Para comprobar 503 en tests se debe
simular explícitamente BackendRecomendacionesNoDisponible, ya que el dominio ahora
responde con ORM real. Las fixtures se limitan a tests. La integración del include
global y navegación se verifica en una rama que combina ambas partes; no adelantar
el despliegue AWS ni dar por hecha la comparación con Figma.
