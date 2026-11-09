# Cierre visual · Histórico y Percepción

Se amplía #69 sobre su revisión anterior. El ajuste de desborde existente se conserva. No se editan archivos de #70–#73.

Capturas antes/después a 1440 × 900 y 390 × 844. Las referencias usan las exportaciones de la auditoría. Las fichas sin marco exacto son adaptaciones.

| Ficha | Resultado | Escritorio | Móvil |
| --- | --- | --- | --- |
| `indicadores-vacio` | Verificada. El panel conserva el estado sin registros y no dibuja tendencia. | [400:866](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-866) | [320:544](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-544) |
| `indicadores-admin` | Verificada. Serie visible con grupo exacto y cuatro servicios sintéticos, incluido un cero. | [400:866](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-866) | [324:75](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=324-75) |
| `indicadores-cocina` | Verificada. Mismo grupo de QA bajo el rol Cocina, con valores y tendencia visibles. | [417:2](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=417-2) | [320:544](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-544) |
| `historico-tabla` | Corregida. Acceso directo y desplazamiento horizontal dentro del contenedor. | [403:874](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-874) | [325:41](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=325-41) |
| `historico-admin` | Corregida. Acceso directo y desplazamiento horizontal dentro del contenedor. | [403:942](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-942) | [325:59](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=325-59) |
| `historico-filtro-error` | Corregida. Resumen asociado al formulario y filtros abiertos ante error. | Sin marco exacto identificado | Sin marco exacto identificado |
| `historico-comparar` | Corregida. Instrucción específica para filtros y periodos. Se conserva el ajuste de desborde de #69. | Sin marco exacto identificado | Sin marco exacto identificado |
| `percepcion` | Corregida. Tarjeta de respuesta separada del identificador del servicio. | Sin marco exacto identificado | Sin marco exacto identificado |
| `percepcion-error` | Corregida. Error visible y borrador conservado. | Sin marco exacto identificado | Sin marco exacto identificado |
| `percepcion-guardada` | Corregida. Respuesta vigente y versión en un bloque diferenciado. | Sin marco exacto identificado | Sin marco exacto identificado |

## Comprobaciones

78 pruebas Django. Diez escenarios HTTP en Chromium por tamaño. El grupo de Indicadores usa cuatro servicios sintéticos con contexto en SQLite aislado, incluido un cero confirmado. Se verificaron la tendencia con evidencia, la ausencia de tendencia sin registros y la tabla con desplazamiento interno en móvil.

Las verificaciones son de navegador y pruebas automatizadas, con datos de QA. Siguen pendientes las comprobaciones físicas de cámara, QR impreso, vinculación PC–celular, uso táctil y revisión con fotografías operativas.
