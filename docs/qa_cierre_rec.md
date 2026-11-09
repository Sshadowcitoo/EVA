# Cierre visual · Recomendaciones, Demostración y 404

Parte de main y no modifica archivos de #69–#73 ni de la entrega de Histórico y Percepción. La demostración de Indicadores hereda la plantilla de Histórico como antes. Las dos ramas pueden integrarse por separado.

Capturas antes/después a 1440 × 900 y 390 × 844. Las referencias usan las exportaciones de la auditoría. Las fichas sin marco exacto son adaptaciones.

| Ficha | Resultado | Escritorio | Móvil |
| --- | --- | --- | --- |
| `404` | Corregida. Recuperación según rol con HTTP 404 preservado. Comprobado con DEBUG=False. | Sin marco exacto identificado | Sin marco exacto identificado |
| `recom-vacio` | Corregida. Controles plegables y mensaje de vacío visible sin desplegar formularios. | Sin marco exacto identificado | Sin marco exacto identificado |
| `recom-insuficiente` | Verificada. Permanece sin propuesta ni acción para generarla. Criterios operativos sin aprobar. | [400:827](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-827) | [320:527](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-527) |
| `recom-lista-admin` | Corregida. Filtros y evaluación plegables con acceso al resumen y tabla. | [403:622](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-622) | [324:57](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=324-57) |
| `recom-lista-cocina` | Corregida. Consulta de solo lectura; sin formulario de evaluación. | Sin marco exacto identificado | Sin marco exacto identificado |
| `recom-error` | Corregida. Formulario de evaluación abierto automáticamente y errores visibles. | Sin marco exacto identificado | Sin marco exacto identificado |
| `recom-suficiente` | Verificada. Capacidad comprobada bajo hipótesis de QA aislada, sin habilitar criterios en operación. | [403:622](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-622) | [324:57](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=324-57) |
| `recom-decidir` | Corregida. Acceso directo a decisión y pruebas, sin cambiar autorización ni formulario. | [400:403](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-403) | [320:837](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-837) |
| `recom-decision-error` | Corregida. Se conserva la decisión enviada y el formulario de corrección. | [403:675](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-675) | [320:837](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-837) |
| `recom-decision-guardada` | Corregida. Atajo a pruebas controladas y decisión vigente preservada. | [400:474](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-474) | [320:336](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-336) |
| `recom-detalle-cocina` | Corregida. Accesos de consulta y ausencia de formulario de decisión. | Sin marco exacto identificado | Sin marco exacto identificado |
| `prueba` | Corregida. Periodos de referencia e intervención distinguibles y apilados en móvil. | Sin marco exacto identificado | Sin marco exacto identificado |
| `prueba-evaluada` | Corregida. El estado no evaluable conserva el aviso y la diferencia no disponible. | Sin marco exacto identificado | Sin marco exacto identificado |
| `demo-indicadores` | Corregida. Escenario y retorno al histórico operativo diferenciados. | [400:866](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-866) | [320:544](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-544) |
| `demo-indicadores-vacio` | Corregida. Aviso de demostración, controles y ausencia de tendencia. | [400:866](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-866) | [320:544](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-544) |
| `demo-recomendaciones` | Corregida. Navegación explícita entre demostraciones y retorno a operación. | [403:622](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-622) | [324:57](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=324-57) |

## Comprobaciones

89 pruebas Django y 46 pruebas frontend. Dieciséis escenarios HTTP en Chromium por tamaño. Los estados suficientes y las pruebas controladas se obtuvieron en SQLite de QA con las hipótesis del ensayo existente. La insuficiencia se comprobó con criterios operativos sin aprobar. Las demostraciones conservan datos ficticios y el 404 se verificó con DEBUG=False.

Las verificaciones son de navegador y pruebas automatizadas, con datos de QA. Siguen pendientes las comprobaciones físicas de cámara, QR impreso, vinculación PC–celular, uso táctil y revisión con fotografías operativas.
