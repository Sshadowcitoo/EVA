# Bandejas y etiquetas QR

Base: `origin/main` en `7e241d7`. Se compararon los estados en escritorio a 1440 × 900 y móvil a 390 × 844. Las capturas usan registros y etiquetas de QA.

## Referencias y adaptaciones

| Pantalla o estado | Referencia de escritorio | Referencia móvil | Aplicación en EVA |
| --- | --- | --- | --- |
| Listado y bandeja con o sin servicio | [W04 · 400:199](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-199) y [400:673](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-673) | [320:371](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-371) | Listado paginado con estado y enlace de detalle. La ficha distingue asignación abierta, cerrada y bandeja sin servicio abierto. Son referencias relacionadas, sin marco exacto de Administración. |
| Búsqueda y errores | [400:343](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-343) y [400:728](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-728) | [320:126](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-126) y [320:462](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-462) | Adaptación del patrón de recuperación. Número e ID se apilan en móvil. Se conservan los valores y errores del formulario. |
| Asignación existente | [403:145](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-145) | [320:629](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-629) | La asignación sigue en Registro, con la interfaz abordada por el PR #70. Esta entrega verifica la asignación reflejada en Administración. |
| QR, descarga y sustitución | Sin marco exacto | Sin marco exacto | QR negro sobre fondo blanco incorporado al SVG, con margen de cuatro módulos. Acciones agrupadas y sustitución con motivo, confirmación y aviso sobre la etiqueta retirada. |
| Anulación, reemplazo guardado e historial | [400:609](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-609) como referencia relacionada de aviso | [320:102](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-102) como referencia relacionada de aviso | Adaptaciones de confirmación. Se conserva el historial y la identificación del responsable. Se distingue la operación bloqueada, la validación del formulario y la confirmación guardada. |

## Compatibilidad con las entregas anteriores

No hay dependencia de integración. El PR usa la plantilla compartida y los estilos de captura de main como base, con los estilos nuevos en `gestion_captura.css`. No edita archivos modificados por #69, #70, #71 o #72. El cambio de #72 al menú base se hereda cuando se integre. El recorrido que crea la asignación y la lectura QR de Registro siguen en sus módulos actuales.

## Comprobaciones

- 159 pruebas Django de captura aprobadas: listado y paginación, búsqueda, asignaciones, permisos por rol, permisos específicos, CSRF, conservación de fotografía y auditoría, duplicidad de reemplazo, revocación y QR con fondo blanco.
- 22 escenarios en Chromium por tamaño, sin desbordamiento a 390 px. Capturas antes/después de búsqueda, listado, detalle, descarga, confirmaciones, errores, permisos y estados históricos. Las comparaciones usan las mismas respuestas y datos de QA.
- El QR renderizado se decodificó con ZXing y coincidió exactamente con el código de QA. Se comprobó el fondo blanco del SVG y el HTTP 404 tras revocación.
- Pendiente físico: imprimir el SVG a la escala de la etiqueta final y probar lectura con cámara real en varias distancias e iluminaciones, incluida la bandeja colocada en su posición habitual. Verificar el retiro de la etiqueta anterior y la lectura de la nueva después del reemplazo.
