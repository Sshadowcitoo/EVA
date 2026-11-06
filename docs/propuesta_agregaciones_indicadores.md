# Indicadores · propuesta de agregaciones y estados

Seguimiento de [W18](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-866) y [M20](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-544). Se conserva la paleta aprobada para el piloto. La ruta de Indicadores consume la nueva proyección de lectura. Las capturas muestran la aplicación conectada a una base local de QA.

## Población, periodo y unidad

- **Población.** Aplicar filtros y selección del histórico a toda la consulta. Usar el análisis real vigente, su intento completado y la revisión confirmada sobre ese intento, junto con las comprobaciones de elegibilidad existentes. Contar un valor apto por servicio y componente dentro de cada grupo. Registrar candidatos, aptos y excluidos como servicios únicos para cobertura. Los componentes de un mismo servicio se cuentan por separado cuando se describe la distribución por componente.
- **Periodo.** Usar la fecha de servido en America/Guayaquil. Respetar fechas inclusivas, ventana horaria semiabierta y filtros elegidos. La tendencia usa semanas calendario locales de lunes a domingo. Mostrar la fecha del lunes y marcar las semanas que el filtro recorta. Los servicios sin fecha de servido no se ubican en una semana.
- **Identidad.** Mantener la clave exacta de histórico: plato, componente, porción, contexto, modelo, configuración y protocolo. El lote permanece disponible para describir procedencia; su papel en la clave sigue el criterio vigente. Un contexto desconocido permite la descripción aislada donde el contrato la admite, sin comparación temporal ni diferencias. Nunca se combina con un contexto conocido.
- **Unidad.** Intensidad es la media aritmética del porcentaje visual por servicio y componente apto, incluidos ceros confirmados. El eje va de 0 a 100 %. Mostrar `n` y los filtros. La prevalencia, si se muestra, usa el criterio aprobado y su versión. Una diferencia válida entre periodos se expresa en puntos porcentuales. Ningún porcentaje representa peso, volumen ni cantidad absoluta.

## Paneles propuestos

| Panel | Agregación y lectura |
| --- | --- |
| Tendencia temporal | Una serie por grupo comparable explícitamente elegido. Media y n por semana de servido. Se conservan los huecos cuando falta evidencia, sin líneas a través de semanas ausentes. El detalle muestra n, fechas efectivas, valor y alcance completo o parcial. Para mostrar una variación, ambos periodos tienen que cumplir las reglas vigentes de comparación. |
| Distribución por componente | Mostrar la intensidad y n de cada componente en su grupo exacto, con plato, porción y contexto fijos. Separar modelo, configuración y protocolo si hay variantes. Las barras usan 0–100 %. Se evita una dona de porcentajes porque los denominadores son distintos y no forman partes de un total. |
| Vista por plato | Mantener fijos componente, porción, contexto y versiones. Mostrar perfiles descriptivos separados por plato, en orden de catálogo, con media y n propios. La identidad vigente incluye plato, por lo que no se calculan diferencias, rankings ni un promedio conjunto. |
| Vista por porción | Mantener fijos plato, componente, contexto y versiones. Mostrar una barra por tipo de porción con su media y n. Cambiar porción cambia el grupo. No se declara cuál es mejor ni se calcula un efecto. |
| Cobertura y exclusiones | Área secundaria. Mantener los contadores y motivos de toda la consulta. Describir por qué un candidato quedó fuera y dar acceso a la tabla paginada para rastrear el caso. |

Las cuatro tarjetas muestran intensidad del grupo, última semana del periodo, tamaño de muestra y cobertura de la consulta. Identificar qué cifras pertenecen al grupo seleccionado y cuáles al filtro general. La serie y las vistas por dimensión comparten selección de grupo y periodo. Si hay varias claves elegibles para una vista, pedir una selección explícita y mostrar qué dimensiones permanecen fijas.

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

## Proyección conectada

`consultar_panel` usa una sola selección del histórico y devuelve la tabla v1 y el panel por separado. La proyección usa los servicios aptos del grupo completo antes de paginar. La media del periodo utiliza todos sus registros aptos, con igual peso por servicio, aunque las semanas tengan tamaños diferentes. La última semana corresponde al límite final del periodo, aunque esté vacía.

Si falta un límite de fechas, se usa el extremo de las fechas de servido disponibles entre los candidatos de la consulta. El alcance semanal describe el recorte por fechas. Si hay una ventana horaria, se mantiene para todos los días. La vista pide acotar la serie cuando el periodo cubre más de 52 semanas. Las tarjetas conservan el cálculo del periodo entero y su última semana.

Con un solo grupo, la vista lo selecciona automáticamente. Con varios, se requiere elección explícita. Una selección que quedó fuera de los filtros se informa en la vista. Los perfiles solo varían una dimensión y mantienen las demás claves exactas. Un contexto desconocido conserva la media descriptiva de su grupo; la serie y los perfiles quedan indisponibles. La prevalencia conserva su regla y se consulta en el detalle de indicadores por grupo.

## Capturas de la aplicación conectada

La base SQLite de QA se preparó con el catálogo piloto y casos ORM sintéticos. Seco de pollo contiene **Arroz y Pollo**. El otro plato es **Arroz con menestra y carne**. Se añadió **Reducida** únicamente al catálogo de esa base local para ejercitar dos porciones; el catálogo del repositorio conserva su configuración.

- Con evidencia de QA: once servicios aptos en la consulta. El grupo Seco de pollo / Arroz / Estándar tiene siete valores aptos: 0, 10, 45, 55, 50, 30 y 40 %. Su media es **32,86 %**. Las muestras semanales son 2, 3, 0 y 2. El periodo va del 7 al 29 de octubre de 2026. La última semana es parcial y tiene 35,00 % con n = 2.
- Sin evidencia apta: dos servicios de QA rechazados en un periodo distinto. La cobertura muestra dos candidatos y cero aptos. Los cuatro gráficos muestran insuficiencia.

Los casos de QA ejercitan las rutas de lectura y la elegibilidad con registros sintéticos aislados. No son resultados del motor en producción. Las capturas abarcan los paneles de Indicadores hasta Cobertura y exclusiones; la tabla histórica queda debajo en la aplicación.

| Escenario | Escritorio, ventana 1440 × 900 | Móvil, ventana 390 × 844 |
| --- | --- | --- |
| Con evidencia de QA | [Ver captura](evidencias/indicadores_conectados/con-1440.jpg) | [Ver captura](evidencias/indicadores_conectados/con-390.jpg) |
| Sin evidencia apta | [Ver captura](evidencias/indicadores_conectados/sin-1440.jpg) | [Ver captura](evidencias/indicadores_conectados/sin-390.jpg) |

Chromium verificó la selección y los cuatro paneles, las escalas, la composición del seco, la última semana parcial, un hueco sin unir puntos y el estado sin evidencia, en ambas ventanas.

## Pruebas

- Cuatro regresiones de panel cubren la agregación antes de paginar, la media por registro, el cero confirmado, semanas parciales y vacías, versiones, contexto incompatible, perfiles separados y exclusión de simulaciones.
- 73 pruebas de histórico correctas y 46 de frontend correctas. Las cuatro pruebas de `indicadores.js` verifican el cero, el hueco entre semanas, el punto único y el SVG oculto cuando no hay valores aptos. La tabla semanal se entrega abierta desde el servidor y sigue disponible tras dibujar el gráfico.
- Suite completa: 583 casos, 579 correctos, tres omitidos por el paquete ONNX privado y el fallo de texto de captura vinculada previamente reproducido en `main`.
