# Cierre visual de Captura

Continuación directa de #70, sobre `81a0e22`. Esta entrega reutiliza las búsquedas y el lector existentes en esa rama. No requiere #71–#73.

| Ficha | Resultado | Referencia de escritorio y móvil |
| --- | --- | --- |
| servido-buscar | Verificada en #70. Se conserva búsqueda por número y alternativa QR. | [400:288](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-288) · [320:45](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-45), marcos relacionados |
| servido-error | Verificada en #70. La consulta fallida conserva el número. | [400:728](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-728) · [320:462](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-462) |
| retorno-buscar | Verificada en #70. Se conserva la ayuda de correspondencia del par. | [400:343](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-343) · [320:126](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-126) |
| qr-permiso | Verificada en #70 con permiso denegado simulado. La búsqueda manual sigue disponible. | Adaptación sin marco exacto |
| servicio-404 | Corregida. Las dos rutas de recuperación se ofrecen en una tarjeta, apiladas en móvil. | [400:728](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-728) · [320:462](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-462), marcos relacionados |
| vinculo-invalido | Corregida. Mantiene HTTP 404 y ofrece instrucciones sin mostrar datos del servicio. | Adaptación sin marco exacto |
| vinculada-completada | Corregida. Encabezado de confirmación y acceso a Registro, sin formulario de carga. | Adaptación sin marco exacto |
| vinculada-expirada | Corregida. Identifica la caducidad y explica cómo generar otro enlace. | Adaptación sin marco exacto |
| vinculada-cancelada | Corregida. Identifica la cancelación y explica cómo recuperar el flujo. | Adaptación sin marco exacto |

158 pruebas Django de Captura. Los cinco estados ajustados se comprobaron en Chromium a 1440 × 900 y 390 × 844, con capturas antes y después. Las cuatro verificaciones reutilizan los pares de evidencia de #70. La prueba del vínculo inválido comprueba el 404, el acceso de recuperación y la ausencia de carga. Quedan pendientes la cámara física, el escaneo de etiquetas, la vinculación PC–celular en equipos físicos y la comprobación táctil. El 404 general conserva su ficha de cierre.
