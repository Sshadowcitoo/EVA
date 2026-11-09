# Revisión de Cocina en escritorio y móvil

Base de la comparación: `origin/main` en `7e241d7`. Capturas de la aplicación a 1440 × 900 y 390 × 844 con la misma evidencia sintética, máscaras de prueba y estados HTTP en ambas versiones. Los cuadros de color de la evidencia provienen del escenario de QA. Las cifras y fotos ilustrativas de Figma no se incorporaron a EVA.

| Estado | Escritorio original 1440 × 900 | Móvil original 390 × 844 | Distribución en EVA |
| --- | --- | --- | --- |
| Antes de decidir | [W03](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-142) | [M08](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-232) | Identidad y acceso al motivo arriba. Servido y retorno juntos, con sus máscaras y opción de ampliar. Hallazgos antes del formulario. |
| Resultado incorrecto, motivo y envío | [W12](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-570) y [W41](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=412-2) | [M17](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-489), referencia para ambos | Motivo y las tres acciones junto a los hallazgos. En móvil los botones pasan a una columna y pueden alcanzarse desde el resumen. |
| Confirmación guardada | [W32](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-576) | [M08a](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-746) | La decisión vigente se ve arriba. El detalle de autor, fecha y motivo sigue en la ficha y el historial. |
| Rechazo guardado | [W33](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-599) | [M17a](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-1197) | Se ve el estado guardado y se conserva el motivo. La rectificación mantiene la justificación obligatoria. |

EVA conserva el formulario integrado y los metadatos completos. La opción de ampliación de las fotos, el salto al formulario, el borrador recuperable y los avisos de simulación, evidencia vencida y permisos son adaptaciones. El error HTTP 400 por motivo vacío y el conflicto 409 no tienen marco exacto identificado entre los consultados.

## Verificación

- Django: 165 pruebas de `apps.analisis`. Incluyen las tres decisiones con ORM, historial, rectificación, idempotencia, permisos y CSRF. La regresión de versión obsoleta exige que el borrador vuelva al campo editable.
- JavaScript: 46 pruebas. Incluyen validación de motivo y control de envío.
- Chromium: 11 escenarios en cada viewport, con capturas antes y después. Incluyen revisión pendiente, motivo escrito, HTTP 400, confirmación guardada, HTTP 409 con borrador, rechazo guardado, no concluyente, simulación, fotos vencidas y acceso HTTP 403 para Registro y Administración. Se verificaron las seis máscaras, los modos de dos columnas y ampliado, el acceso al formulario y el ancho de página.
- El caso no concluyente combina la decisión guardada con un componente de QA sin porcentaje apto. Para el conflicto se envió una versión anterior. Queda pendiente la comprobación visual con fotos operativas y dispositivos físicos, además de reproducir dos sesiones guardando simultáneamente en navegador. Los estados del motor en proceso y fallido se comprueban en pruebas de plantilla.
