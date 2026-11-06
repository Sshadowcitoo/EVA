# Propuesta visual de EVA · piloto de Indicadores

Base del código: `origin/main` en `bdd23fa21bf2e331b5169f22c85e99f204cb59db`. La propuesta usa las páginas de presentación por roles de Figma. W18 y M20 se inspeccionaron en detalle. Los demás vínculos se verificaron por nombre y nodo en el archivo y se contrastaron con las plantillas y las entregas de los bloques 2 a 7. La equivalencia de cada variante se revisará al intervenir su recorrido.

## Inventario y correspondencias

Los identificadores corresponden a marcos reales dentro del [archivo EVA](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA). La columna de diferencias se refiere a la estructura implementada. Una relación temática no implica una correspondencia exacta de estados.

| Pantalla o recorrido implementado | Marcos verificados (web / móvil) | Diferencia o decisión pendiente |
| --- | --- | --- |
| Acceso y errores, `registration/login.html` | W09 400:456, W22 403:56 / M01 320:24, L02 329:44 | El acceso operativo usa un formulario común. W19–W21 403:2, 403:20, 403:38 y L03 329:68 son variantes demo. |
| Registro básico, inicio y búsqueda de bandeja, `captura/nueva_bandeja.html`, `buscar_bandeja.html` | W06 400:288, W23 403:74, W24 403:145 / M02 320:45, M02a 320:599, M02b 320:629 | EVA separa el alta básica y la bandeja física. El contexto añade sede, modalidad y lote. Revisar la relación entre selección y captura de foto. |
| Foto del servido, guardado y espera, `fotografia.html`, `estado_servicio.html`, `confirmacion.html` | W25 403:200, W26 403:255, W13 400:609 / M03 320:75, M14 320:399, M14a 320:984, M04 320:102 | Hay checklist, cámara, selección de archivo y acciones entre páginas. Los marcos representan estados del mismo flujo. |
| Buscar y confirmar retorno, foto final y búsqueda fallida | W07 400:343, W14 400:673, W15 400:728, W27 403:319, W28 403:379, W29 403:434 / M05 320:126, M05a 320:659, M13 320:371, M13a 320:686, M06 320:153, M15 320:430, M16 320:462 | La búsqueda muestra mensajes en el formulario. El retorno conserva evidencia previa y lote y requiere confirmación antes de la foto. |
| Errores de fotografía | W36 403:728, W37 403:767, W45 418:91, W46 418:130, W47 418:169 / M10 320:316, E01 331:23, E02 331:46, E03 331:69, E04 331:92, E05 334:43 | Hay errores de formulario y estados de captura. La equivalencia exacta de las variantes de recaptura requiere validación funcional por separado. |
| QR de vinculación, gestión de bandejas, anulación y reemplazo | Sin homólogo exacto identificado en las páginas revisadas | Pantallas operativas propias. Conservar confirmación, permisos y trazabilidad. |
| Cocina y lista de análisis, `analisis/lista*.html`, inicio de Cocina | W01 400:3, W31 403:553 / D02 322:52 | El código ofrece cola con filtros y estados. Revisar agrupación y prioridad del acceso al detalle. |
| Par, detalle de análisis, en proceso, fallido y no concluyente | W03 400:142, W05 400:249, W16 400:788, W30 403:489 / M07 320:181, M12 320:354, M18 320:507, M15a 320:714 | La página implementada comparte evidencia y tabla entre estados. El par de fotos tiene vista propia. |
| Revisión de Cocina y decisiones guardadas | W03 400:142, W12 400:570, W32 403:576, W33 403:599, W41 412:2, W42 412:41, W43 412:112 / M08 320:232, M17 320:489, M08a 320:746, M17a 320:1197 | Formulario, justificación, evidencia y tabla comparten pantalla. Revisar disposición y retroalimentación sin alterar el proceso. |
| Catálogo, porciones, componentes y formularios | W04 400:199 / sin homólogo exacto para cada alta o edición | El código separa listados y edición de entidades. El marco agrupa administración en una vista. |
| Indicadores e histórico | [W18](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-866), W44 417:2, W39 403:874, W40 403:942 / [M20](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-544), M21 320:1126, D04 324:75, D05 332:90, H01 325:41 y 325:59 | La ruta actual combina filtros, métricas, grupos y tabla. W18 da prioridad a cuatro tarjetas y gráficos. El piloto conserva la tabla debajo y un enlace directo en el menú. W38 403:806 y H01 325:23 describen histórico de Registro y no corresponden al permiso de esta ruta. |
| Comparar periodos y percepción por servicio | Sin homólogo exacto identificado | Comparación y percepción son rutas distintas con sus propias reglas. |
| Lista, detalle y decisiones de recomendaciones | W17 400:827, W34 403:622, W08 400:403, W10 400:474, W35 403:675, W49–W52 422:2, 422:55, 422:108, 422:132 / M19 320:527, M09a–g 320:798, 320:837, 320:874, 320:911, 320:1015, 320:1052, 320:1089, M11 320:336, M11b 320:948, M11c 320:966 | EVA separa evaluación, decisión y versiones. Mantener evidencia insuficiente y distinguir acciones por rol. |
| Prueba controlada, demostración y acceso denegado | R01 324:57 es referencia temática de demo; sin homólogos exactos para prueba controlada o 403 | La demostración conserva ruta y avisos propios. Prueba controlada y acceso denegado mantienen su semántica. |

## Sistema propuesto

| Componente | Pauta |
| --- | --- |
| Color | Lienzo `#EDF5EF`, superficie `#F7FBF7`, superficie de énfasis `#E4F0E7`, texto `#162D23`, texto secundario `#486052`, acción `#246045` con texto `#F7FBF7`. Error rojo oscuro sobre rosa, advertencia o insuficiencia ámbar sobre crema y éxito verde sobre menta. Etiqueta textual junto al color. |
| Menú y encabezado | Marca, navegación por rol, sección activa y cierre de sesión compartidos. Barra lateral de 240 px en escritorio. En móvil, menú desplegable existente y acción principal a ancho completo. |
| Tarjetas | Título, cifra o estado, explicación. Cuatro por fila en escritorio y dos por fila en móvil. Bordes suaves y radios de 12 px. |
| Formularios y botones | Etiqueta visible, ayuda y error junto al campo, foco marcado, áreas de pulsación de al menos 44 px para acciones principales. Filtros plegables y abiertos si la consulta es inválida. |
| Tablas | Títulos y encabezados conservados. Contenedor con desplazamiento propio y accesible por teclado en móvil. |
| Gráficos | Dos columnas en escritorio y una en móvil. Barras con escala explícita, valores visibles y unidades. Cada gráfico describe la población y el límite de comparación. |
| Mensajes y vacíos | Diferenciar consulta vacía, falta de aptos, múltiples grupos, criterio pendiente, error y desconexión. Usar texto explicativo y ofrecer la acción pertinente. |

## Adaptación inicial de W18

La [proyección conectada y sus capturas de QA](propuesta_agregaciones_indicadores.md) documentan la iteración posterior. Esta sección registra el piloto inicial.

La acción de cabecera enlaza a Recomendaciones con los permisos vigentes. Las cuatro tarjetas usan candidatos, aptos, excluidos e intensidad del resultado consultado. Los gráficos muestran cobertura de la muestra, motivos de exclusión, intensidad y prevalencia. Los dos últimos representan la consulta tal como la devuelve el histórico. La vista conserva filtros, grupos con sus motivos, paginación y tabla completa.

W18 presenta ejemplos de tendencia semanal, distribución por componente y rankings por plato y porción. El contrato actual no entrega series temporales ni rankings comparables. Calcularlos desde una sola página o combinar grupos modificaría el significado estadístico. Para recuperar esas piezas del diseño habría que acordar dimensiones, periodos, agrupación, criterios y agregaciones de servidor. El piloto usa barras HTML nativas y datos existentes, sin dependencias nuevas. La demo sigue separada.

## Comparación visual

Las tres columnas usan el mismo tamaño de ventana. Las cifras del marco de Figma son de demostración. Las dos capturas del código usan la misma base local de QA con dos registros creados mediante el flujo del servicio y sin evidencia apta. El resultado viene de la consulta ORM del histórico. No se muestran datos de producción.

| Tamaño | Figma, versión anterior y propuesta | Propuesta a tamaño original |
| --- | --- | --- |
| 1440 × 900 | [Comparativa W18](evidencias/propuesta_indicadores/comparativa-1440.jpg) | [Escritorio](evidencias/propuesta_indicadores/indicadores-1440.jpg) |
| 390 × 844 | [Comparativa M20](evidencias/propuesta_indicadores/comparativa-390.jpg) | [Móvil](evidencias/propuesta_indicadores/indicadores-390.jpg) |

- En escritorio se cotejaron el ancho del menú, la acción de cabecera, las cuatro tarjetas y las dos filas de gráficos. El formulario de consulta queda disponible en un desplegable antes de los resultados y el historial conserva su tabla al final.
- En móvil se cotejaron la cabecera apilada, la rejilla de dos tarjetas por fila y la lectura vertical. Los gráficos se apilan en una columna y la página permite llegar al detalle por desplazamiento o por el menú. La acción primaria lleva a Recomendaciones. M20 usa acciones de regreso a Cocina y de detalle en su prototipo.
- Contraste calculado para las combinaciones principales del piloto. Texto principal sobre superficie 14,02:1. Texto secundario sobre superficie 6,55:1. Acción primaria 7,09:1. Aviso ámbar 7,19:1 y error 7,17:1.
- Chromium verificó las columnas, el menú móvil, el enlace al historial, filtros inválidos, consulta vacía y ausencia de desborde global y errores de JavaScript a ambos tamaños.

## Pruebas y pendientes

- 71 pruebas de histórico correctas en la versión final, incluidas dos regresiones sobre barras con cero confirmado, métricas ausentes y consulta vacía.
- Suite completa de Django con 581 casos. 577 correctos, tres omisiones por paquete ONNX privado y un fallo que también se reproduce en la base `bdd23fa`. `test_pc_telefono_checklist_persistido_y_reintento_no_duplica` espera «Captura ya completada». La plantilla de captura vinculada en la base muestra «Fotografía guardada correctamente».
- 42 pruebas de frontend correctas. `manage.py check` y comprobación de migraciones correctos.
- Pendiente aprobar esta composición, la paleta y el tratamiento de gráficos vacíos antes de adaptar las demás pantallas.
- Pendiente cotejar variantes y estados de los recorridos restantes, además de acordar las agregaciones necesarias si se recuperan las series y rankings de Figma. El piloto mantiene los resultados y permisos que ofrece la ruta actual.
