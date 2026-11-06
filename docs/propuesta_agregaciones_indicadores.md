# Indicadores · propuesta de agregaciones y estados

Seguimiento de [W18](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-866) y [M20](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-544). Se conserva la paleta aprobada para el piloto. Esta revisión propone el contrato de lectura y muestra dos prototipos de QA. La aplicación del PR conserva la consulta actual mientras se acuerdan las agregaciones.

## Población, periodo y unidad

- **Población.** Aplicar filtros y selección del histórico a toda la consulta. Usar el análisis real vigente, su intento completado y la revisión confirmada sobre ese intento, junto con las comprobaciones de elegibilidad existentes. Contar un valor apto por servicio y componente dentro de cada grupo. Registrar candidatos, aptos y excluidos como servicios únicos para cobertura. Los componentes de un mismo servicio se cuentan por separado cuando se describe la distribución por componente.
- **Periodo.** Usar la fecha de servido en America/Guayaquil. Respetar fechas inclusivas, ventana horaria semiabierta y filtros elegidos. La tendencia usa semanas calendario locales de lunes a domingo. Mostrar la fecha del lunes y marcar las semanas que el filtro recorta. Los servicios sin fecha de servido no se ubican en una semana.
- **Identidad.** Mantener la clave exacta de histórico: plato, componente, porción, contexto, modelo, configuración y protocolo. El lote permanece disponible para describir procedencia; su papel en la clave sigue el criterio vigente. Un contexto desconocido permite la descripción aislada donde el contrato la admite, sin comparación temporal ni diferencias. Nunca se combina con un contexto conocido.
- **Unidad.** Intensidad es la media aritmética del porcentaje visual por servicio y componente apto, incluidos ceros confirmados. El eje va de 0 a 100 %. Mostrar `n` y los filtros. La prevalencia, si se muestra, usa el criterio aprobado y su versión. Una diferencia válida entre periodos se expresa en puntos porcentuales. Ningún porcentaje representa peso, volumen ni cantidad absoluta.

## Paneles propuestos

| Panel | Agregación y lectura |
| --- | --- |
| Tendencia temporal | Una serie por grupo comparable explícitamente elegido. Media y n por semana de servido. Se conservan los huecos cuando falta evidencia, sin líneas a través de semanas ausentes. Para mostrar una variación, ambos periodos tienen que cumplir las reglas vigentes de comparación. |
| Distribución por componente | Mostrar la intensidad y n de cada componente en su grupo exacto, con plato, porción y contexto fijos. Separar modelo, configuración y protocolo si hay variantes. Las barras usan 0–100 %. Se evita una dona de porcentajes porque los denominadores son distintos y no forman partes de un total. |
| Vista por plato | Mantener fijos componente, porción, contexto y versiones. Mostrar perfiles descriptivos separados por plato, en orden de catálogo, con media y n propios. La identidad vigente incluye plato, por lo que no se calculan diferencias, rankings ni un promedio conjunto. |
| Vista por porción | Mantener fijos plato, componente, contexto y versiones. Mostrar una barra por tipo de porción con su media y n. Cambiar porción cambia el grupo. No se declara cuál es mejor ni se calcula un efecto. |
| Cobertura y exclusiones | Área secundaria. Mantener los contadores y motivos de toda la consulta. Describir por qué un candidato quedó fuera y dar acceso a la tabla paginada para rastrear el caso. |

Las cuatro tarjetas pueden mostrar intensidad del grupo, intensidad del último corte, tamaño de muestra y cobertura de la consulta. Identificar qué cifras pertenecen al grupo seleccionado y cuáles al filtro general. La serie y las vistas por dimensión comparten selección de grupo y periodo. Si hay varias claves elegibles para una vista, pedir una selección explícita y mostrar qué dimensiones permanecen fijas.

## Evidencia insuficiente

| Situación | Presentación |
| --- | --- |
| Cero confirmado con evidencia apta | Mostrar 0 % y n; conservar el punto o la fila del grupo. |
| Consulta vacía | Mostrar «Sin registros» y permitir cambiar filtros. Omitir ejes y puntos sin datos. |
| Candidatos sin evidencia apta | Mostrar «Evidencia insuficiente» y los motivos. El número de aptos puede ser cero; la intensidad queda ausente. |
| Semana sin valores o grupo sin contexto válido | Dejar un hueco en la tendencia o mostrar «Grupo no comparable». Conservar el detalle descriptivo permitido y la identidad del grupo. |
| Solo una semana con datos | Mostrar el punto y n, sin afirmar tendencia. |
| Criterio pendiente, desconexión o error | Informar el estado de forma separada. El criterio de presencia pendiente solo bloquea prevalencia. La ausencia de servicio o un error de consulta no se convierte en un cero. |

Se mantienen los criterios actuales. El mínimo existente para una media descriptiva es un valor apto. No se incorpora un mínimo de política para recomendar. Para una tendencia legible se requieren al menos dos semanas con valor; esta regla afecta la representación, no la elegibilidad de los registros.

## Contrato por acordar

Proponer una proyección de lectura adicional que devuelva periodo, filtros, grupo exacto elegido, grupos elegibles, puntos semanales (inicio, fin efectivo, n, intensidad, estado), perfiles por dimensión (clave completa, etiqueta, n, intensidad, estado) y cobertura. Agregar en servidor sobre la selección completa antes de paginar. Conservar el contrato v1 de la tabla y sus permisos. Validar casos con semanas parciales, más de una página, ceros, contexto desconocido, varias versiones y filtros sin evidencia. Este PR no conecta la nueva proyección a la ruta.

## Prototipos de QA

La cabecera marca **Prototipo QA** en ambos escenarios. Para el escenario con evidencia, el prototipo toma los cuatro valores aptos de la fixture existente `historico_fixture('con_datos')` (0, 10, 30 y 60) como entradas de prueba. Las cuatro semanas QA usan subconjuntos consecutivos de dos valores y el último corte usa el primero y el último. Los grupos de componente, plato y porción usan subconjuntos explícitos de esa misma fuente, cada uno agregado por separado con la función vigente `calcular`. Estas asignaciones son casos de prueba para revisar la composición. No representan registros operativos ni habilitan criterios. El escenario sin evidencia usa listas aptas vacías y omite barras y puntos.

Los perfiles adicionales de QA usan para pollo los tres últimos valores y para ensalada los dos primeros. El segundo plato usa los dos valores centrales y la porción reducida los dos últimos. Los ocho servicios de la serie de referencia son distintos por semana. Los grupos adicionales de plato y porción aportan dos servicios distintos cada uno. Los otros componentes se cuentan dentro de los servicios de referencia. El escenario sin evidencia toma los cinco candidatos excluidos y el motivo de la fixture `sin_aptos`.

| Escenario | Escritorio, ventana 1440 × 900 | Móvil, ventana 390 × 844 |
| --- | --- | --- |
| QA con evidencia | [Pantalla completa](evidencias/propuesta_agregaciones/con-evidencia-1440.jpg) | [Pantalla completa](evidencias/propuesta_agregaciones/con-evidencia-390.jpg) |
| QA sin evidencia | [Pantalla completa](evidencias/propuesta_agregaciones/sin-evidencia-1440.jpg) | [Pantalla completa](evidencias/propuesta_agregaciones/sin-evidencia-390.jpg) |

Chromium comprobó las cuatro tarjetas, cuatro paneles, ausencia de barras en los paneles vacíos y ausencia de desborde horizontal en ambas ventanas. Las capturas incluyen el contenido bajo el primer pliegue. El prototipo es estático y no forma parte de las rutas de EVA.
