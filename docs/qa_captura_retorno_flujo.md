# Entrega 2 · Captura y Retorno

Base: `7e241d7`. Adaptación de plantillas y CSS de Captura. Las solicitudes, los permisos, la confirmación, los formatos y límites, el checklist, el contexto, el historial y las reglas de cámara y QR conservan su comportamiento.

| Recorrido | Referencia de Figma | Ajuste y alcance |
| --- | --- | --- |
| Registro y selección de bandeja | [W06 · 400:288](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-288), [W24 · 403:145](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-145), [M02 · 320:45](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-45), [M02b · 320:629](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-629) | Guardar queda junto al formulario básico. La captura con bandeja es un acceso secundario. Tras localizar una bandeja, se presenta el formulario primero y la búsqueda alternativa queda plegada. |
| Servido, cámara y vista previa | [W25 · 403:200](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-200), [M03 · 320:75](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-75), [M14 · 320:399](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-399) | Identificación breve, controles de captura, vista previa, comprobaciones y guardado en orden de uso. En escritorio conserva dos columnas. En móvil las ayudas y el contexto ampliado quedan después de la acción. |
| Retorno localizado y fotografía | [W14 · 400:673](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-673), [M13 · 320:371](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-371), [W29 · 403:434](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-434), [M06 · 320:153](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-153) | La foto de referencia precede a la casilla y al botón. Se muestra completa, con altura limitada y sin recorte. Contexto y búsqueda alternativa quedan después. |
| Confirmación y espera | [W13 · 400:609](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-609), [M04 · 320:102](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-102) | La siguiente acción queda cerca del estado. Se conservan fechas, protocolo, contexto y percepción opcional. El registro básico y el par completo son adaptaciones sin marco propio. |
| Vinculación | Adaptación de la ficha de foto y del patrón de confirmación | La generación del QR queda junto a la identidad y antes de la ayuda ampliada. Captura vinculada reutiliza el formulario de fotografía. Se verificaron los estados generado, vigente, completado, caducado, cancelado e inválido. |
| Errores | [W15 · 400:728](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-728), [M16 · 320:462](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-462), [W36 · 403:728](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-728), [M10 · 320:316](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-316) | Los marcos orientan el mensaje y la recuperación. El formulario conserva campos, errores y validaciones. La recuperación dedicada del vínculo inválido queda pendiente. |

## Evidencia

Las capturas muestran respuestas de Django de bases locales de QA, con los mismos escenarios antes y después. Los IDs y fechas pueden diferir entre las dos ejecuciones. Las imágenes del servido son muestras sintéticas.

| Escenario | Escritorio 1440 × 900 | Móvil 390 × 844 |
| --- | --- | --- |
| Fotografía de servido | [Antes](evidencias/captura-retorno/foto-servido-antes-1440.jpg) · [Después](evidencias/captura-retorno/foto-servido-despues-1440.jpg) | [Antes](evidencias/captura-retorno/foto-servido-antes-390.jpg) · [Después](evidencias/captura-retorno/foto-servido-despues-390.jpg) |
| Retorno localizado | [Antes](evidencias/captura-retorno/retorno-encontrado-antes-1440.jpg) · [Después](evidencias/captura-retorno/retorno-encontrado-despues-1440.jpg) | [Antes](evidencias/captura-retorno/retorno-encontrado-antes-390.jpg) · [Después](evidencias/captura-retorno/retorno-encontrado-despues-390.jpg) |

[Inventario actualizado y pares completos](https://chatgpt.com/library?file_id=libfile_84d915057a7c81918963d1a8aab2c96a&account_id=personal). Incluye 26 escenarios distintos de esta entrega en ambos tamaños y enlaza a los marcos disponibles.

## Verificación

- 158 pruebas Django de Captura y 46 de frontend correctas.
- Chromium verificó las vistas a 1440 × 900 y 390 × 844, sin desborde horizontal ni errores de JavaScript en las capturas. Se comprobaron la denegación de permiso de cámara y lector QR, selección de archivo, toma con cámara simulada, vista previa y los tres checks requeridos antes de enviar.
- Los estados de error y confirmación se generaron en la base aislada. Quedan pendientes cámara y QR físicos y las mejoras que el inventario etiqueta como verificadas sin ajuste. Cocina y los otros módulos quedan para sus entregas.
