# Interfaz del bloque 5: revisión de Cocina

Responsable: Jean. Rama: `jean-b5-interfaz-cocina` (parte de `cesar-b5-contratos-interfaz` e incluye `jean-b4-interfaz-analisis`).
Fecha de la revisión contra Figma: 02/11/2026. Solo lectura: no se modificó nada en Figma.

## 1. Qué se hizo

| Pieza | Archivo | Marco de Figma | Estado |
|---|---|---|---|
| Pantalla de revisión | `templates/analisis/revision.html` | W03 | Hecha |
| Evidencia con máscaras (parcial compartido) | `templates/analisis/_evidencia.html` | W03 | Hecha |
| Tabla de hallazgos por componente (parcial compartido) | `templates/analisis/_tabla_resultados.html` | W03 | Hecha |
| Detalle del análisis (ahora usa los dos parciales) | `templates/analisis/detalle.html` | W03 | Ajustado |
| Validación del formulario, motivos frecuentes, envío único | `static/js/analisis.js` | W12, W41 | Hecha |
| Estilos de la revisión | `static/css/analisis.css` | W03 | Hechos |
| Pruebas | `apps/analisis/test_interfaz_revision.py` (14), `tests/frontend/revision.test.cjs` (10) | — | 46 de `apps.analisis` y 36 de JavaScript en OK |

## 2. Reglas que cumple la pantalla

- Las tres acciones usan los textos de Figma: «Confirmar revisión», «Marcar no concluyente» y «Marcar incorrecto». Los valores internos no cambian (`CONFIRMADO`, `NO_CONCLUYENTE`, `RECHAZADO`).
- El formulario solo aparece si la vista entrega `decision_url`. Sin él se muestra «Las acciones estarán disponibles al conectar el servicio de revisión», sin botones falsos.
- «Confirmar revisión» queda deshabilitado si `puede_confirmar` es falso, con la razón visible (resultado simulado, sin evidencia o sin criterios técnicos aprobados). Un botón deshabilitado no es autorización: el backend vuelve a validar.
- Sin fotos disponibles se avisa que la evidencia venció o aún no se cargó y no se puede confirmar a ciegas.
- Marcar incorrecto, marcar no concluyente y rectificar exigen motivo. La primera confirmación no lo exige. Sin motivo, el envío se bloquea, se explica y el foco va al campo.
- El motivo es un solo campo de texto (`motivo`, máximo 1000). Con JavaScript aparece además una lista de motivos frecuentes (máscara incorrecta, fotografía dudosa, otro) que copia el texto al campo; sin JavaScript solo se ve el campo.
- Un segundo envío mientras se guarda se descarta. Al volver con el botón atrás se restauran los botones.
- La decisión vigente se muestra con palabras (Confirmada, Marcada como incorrecta, Marcada como no concluyente), autor, fecha y motivo, y se puede rectificar.
- Con análisis pendiente, en proceso, fallido o con tiempo agotado no hay formulario y se explica por qué.
- Los resultados simulados se marcan «SIMULADO» y no se pueden confirmar como evidencia.
- Las máscaras se superponen sobre su foto según `etapa` (`SERVIDO` o `RETORNO`).
- Teclado: el orden de tabulación es lógico, los botones deshabilitados se saltan y el foco tiene contorno visible.

## 3. Datos que usa la plantilla

Del contrato de César (`docs/contrato_bloque_5.md`): todo lo del bloque 4 más `mascaras`, `revision_actual` (`decision`, `autor`, `fecha`, `motivo`), `decision_url`, `version_esperada` y `puede_confirmar`. Las rutas son `pendientes_revision`, `revision_detalle` y `revisar`.

Pendiente de ratificar con César y Lino: `resultado.color_clave` (1 a 8), color estable por componente, igual al de su máscara. Sin ese dato no se dibuja el punto de color.

## 4. Mapeo con Figma

Archivo: **EVA · Flujos móvil y web** (id `vSVqy8rmaejpEGo0RwXk66`), página **02 · Web · presentación por roles**, marcos de 1440 × 900. Enlace: `https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=` + el node-id.

| Marco | Nombre en Figma | node-id | Pantalla de la app | Visto |
|---|---|---|---|---|
| W03 | Detalle de análisis | `400-142` | `analisis/revision.html` | Sí |
| W12 | Resultado incorrecto (Motivo del rechazo) | `400-570` | motivo dentro de `revision.html` | Sí |
| W41 | Rechazo con motivo | `412-2` | motivo dentro de `revision.html` | Sí |
| W32 | Revisión de Cocina guardada | `403-576` | `revision_actual` CONFIRMADO | Sí |
| W33 | Rechazo de Cocina guardado | `403-599` | `revision_actual` RECHAZADO | Sí |

**Página móvil (390 × 844): pendiente.** No hay node-id verificables de la página «01 · Móvil · presentación por roles». No se inventan. A 390 px la app se revisó solo contra sí misma (sin desbordamiento horizontal).

## 5. Comparación con Figma (revisión visual aproximada, no una métrica)

| Pantalla | Parecido estimado | Qué coincide | Qué difiere |
|---|---|---|---|
| Revisión vs W03 | Cercano, del orden del 70 % | Cuadrícula de dos columnas, fotos Servido y Retorno arriba, tarjetas laterales «Registro e identificación» y «Revisión de cocina», «Hallazgos», «Secuencia de evidencia» y los tres botones con los mismos textos y el principal en azul | Figma usa una ilustración de ejemplo y la app fotos reales con máscaras. Los hallazgos son una tabla y no una caja azul con leyenda en línea. Figma tiene menú lateral completo (Inicio, Pendientes, Historial, Indicadores, Cerrar sesión) |
| Motivo vs W12 y W41 | Parcial | Motivo obligatorio, lista de motivos (máscara incorrecta, fotografía dudosa, otro) | Figma separa el rechazo en una pantalla propia con «Guardar rechazo» y «Volver a revisión» y los textos «Al guardar» y «Sin recomendación». La app pide el motivo en la misma pantalla |
| Decisión guardada vs W32 y W33 | Parcial | Texto «Revisión cerrada» y «Consulta en solo lectura», motivo visible | Figma tiene una pantalla aparte con caja verde y «Volver al inicio de Cocina». La app muestra la decisión vigente en la tarjeta «Revisión de cocina» de la misma pantalla |

El objetivo acordado es un parecido aproximado del 70 %. Se alcanza en la pantalla principal (W03). En el rechazo y en las pantallas guardadas queda por debajo, porque Figma las dibuja como pantallas separadas y la app las resuelve en una sola. Las diferencias son la lista de lo que falta si se quiere acercarlas.

## 6. Extensiones sin marco en Figma

- Máscaras superpuestas sobre las fotos.
- Aviso de que la evidencia no está disponible y no se puede confirmar a ciegas.
- Razón visible cuando «Confirmar revisión» está bloqueado.
- Etiqueta SIMULADO con aviso de que no vale para indicadores.
- Bandeja, servicio, intento, duración y modelo en «Registro e identificación».
- Rectificación de una decisión vigente con `version_esperada`.
- Validación del motivo, bloqueo de segundo envío y mensaje «Guardando la decisión…».

## 7. Diferencias con las plantillas de César

| Tema | Figma | Plantilla de César | Esta rama |
|---|---|---|---|
| Botones de decisión | Confirmar revisión, Marcar no concluyente, Marcar incorrecto | Confirmar resultado, Rechazar resultado, Marcar no concluyente | Textos de Figma; valores internos sin cambios. **Pendiente de confirmar con César** |
| Motivo | Se elige de una lista | Texto libre | Campo único, con lista opcional que lo rellena. El contrato del backend no cambia. **Pendiente de confirmar con César** |

## 8. Pendiente

1. Confirmar con César los textos de los botones y el motivo con lista.
2. Ratificar `color_clave` y coordinar con Lino las máscaras transparentes y alineadas.
3. Conectar a las vistas reales (Lino: contextos, `estado_url`, rutas de revisión) y al modelo y servicio de revisión (Isaac). Hoy las plantillas se probaron con datos de prueba.
4. Decidir si se quieren pantallas separadas para rechazo (W12, W41) y decisión guardada (W32, W33).
5. Leer la página móvil de Figma y comparar a 390 × 844 con node-id verificados.