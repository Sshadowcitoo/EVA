# Entrega 1 · Comparar periodos en móvil

Base de auditoría: `7e241d7`. Ruta: `/historico/comparar/`.

| Ficha del inventario | Estado en esta entrega |
| --- | --- |
| `historico-comparar-resultado` · P1 | Desborde corregido y verificado en QA. Pendiente revisión del PR. |
| `historico-comparar` · P2 | Formulario inicial y error de filtros comprobados. La adaptación de su jerarquía queda pendiente. |
| Resto del inventario | Pendiente para entregas separadas. |

## Ajuste

El ancho mínimo intrínseco de los resúmenes, que incluyen identificadores y versiones largos, ampliaba la cuadrícula de comparación. La cuadrícula y sus secciones pueden encogerse dentro de la página. Los identificadores largos admiten saltos de línea y los periodos se apilan en móvil. En escritorio quedan dos columnas. Se conserva el desplazamiento propio de las tablas históricas.

## Referencia visual

La auditoría no localizó un marco propio de Comparar periodos. Esta es una adaptación del patrón de tarjetas y lectura vertical de Histórico e Indicadores. Referencias relacionadas: [W18, escritorio, nodo 400:866](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-866) y [M20, móvil, nodo 320:544](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-544).

## Evidencia

Misma respuesta de comparación de la base local de QA, con la ventana desplazada al resultado. Se usaron los estilos base y corregido de la aplicación. El texto de ambas versiones coincide.

| Ventana | Antes | Después | Ancho del documento |
| --- | --- | --- | --- |
| 1440 × 900 | [Captura](evidencias/comparar-periodos/antes-1440.jpg) | [Captura](evidencias/comparar-periodos/despues-1440.jpg) | 1440 → 1440 px |
| 390 × 844 | [Captura](evidencias/comparar-periodos/antes-390.jpg) | [Captura](evidencias/comparar-periodos/despues-390.jpg) | 531 → 390 px |

En Chromium, la ruta inicial, el resultado de QA y el error de filtros conservan el documento en 390 px. En la lista histórica, la tabla de 760 px se desplaza dentro de su contenedor de 316 px mientras el documento permanece en 390 px. Se comprobó un desplazamiento interno de 200 px.

Pasaron 161 pruebas de Histórico y Recomendaciones y 3 pruebas frontend de Histórico. El parche de aplicación modifica solo CSS de la cuadrícula de comparación.
