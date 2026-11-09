# Cierre visual de Análisis

Continuación directa de #71, sobre `8f1ffb8`. Reutiliza los estilos y las máscaras de Revisión de Cocina sin alterar el formulario de decisión. No requiere #70, #72 ni #73.

| Fichas | Resultado | Referencias de escritorio y móvil |
| --- | --- | --- |
| inicio-cocina-vacio, inicio-cocina | Cola de revisión diferenciada de la lista técnica. Resumen compacto, acceso a ambos recorridos y mensaje propio cuando no hay pendientes. | [400:3](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-3), [403:553](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-553) · [322:52](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=322-52) |
| analisis-vacio, analisis-lista | La lista conserva pares y estados técnicos, incluso si el caso dejó la cola de revisión. | Adaptación relacionada con [400:3](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-3) · [322:52](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=322-52) |
| par-solicitar | Acción de solicitud en una tarjeta, con regreso explícito al listado. | Adaptación sin marco exacto |
| analisis-detalle | Servido y retorno lado a lado con máscaras. Se conservan el origen, el intento y los hallazgos. | [400:142](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-142) · [320:181](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-181), marcos relacionados |
| analisis-no-concluyente | La ficha técnica conserva el estado y el motivo por componente. Un componente sin evidencia apta sigue sin porcentaje. | [400:249](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-249) · [320:354](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-354) |
| analisis-cargando | Se conserva la consulta del estado y se ofrece retorno a la lista. | [403:489](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-489) · [320:714](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-714) |
| analisis-fallo | Aviso técnico y botón de reintento cuando la vista lo autoriza. Sin porcentajes en el fallo. | [400:788](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-788) · [320:507](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-507) |

166 pruebas Django de Análisis y 46 de frontend aprobadas. Se comprobaron nueve escenarios de Análisis en Chromium a 1440 × 900 y 390 × 844. La evidencia de QA usa una respuesta sintética del motor en la prueba de integración para generar las seis máscaras sintéticas y comprobar su visualización. El estado de carga se mantuvo estable durante la captura con una respuesta local de QA. La validación física con fotografías de operación y dispositivos reales sigue pendiente.
