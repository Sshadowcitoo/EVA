# Claridad de la interfaz de EVA

Base de revisión: `origin/main` en `5a42d14`. Se conservan la paleta amarillo pastel y crema, las advertencias y las mascotas originales.

| Vista | Marcos de referencia | Adaptación solicitada |
| --- | --- | --- |
| Login y credenciales inválidas | [400:456](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-456) · [320:24](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-24) · [403:56](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-56) · [329:44](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=329-44) | Bienvenida breve, composición en dos zonas en escritorio y encabezado compacto en móvil. El formulario de acceso existente conserva errores, campos y destino solicitado. |
| Histórico y vacío | [403:942](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-942) · [325:59](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=325-59) | La lista se adapta a tarjetas de servicio plegables. Se mantiene la paginación por fila del contrato. Una tarjeta puede tener más componentes en la página siguiente. |
| Revisión de Cocina | [400:142](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-142) · [320:232](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-232) | Evidencia, hallazgos y luego decisión. Las acciones alternativas quedan en Más opciones y el motivo conserva sus requisitos. |
| Catálogo, Percepción y detalles | [400:199](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-199) como referencia de catálogo | El patrón de Detalles técnicos y la agrupación por servicio son adaptaciones sin marco exacto. Los códigos siguen disponibles cuando el flujo requiere introducirlos, por ejemplo, al crear una entrada o buscar un servicio por ID. |

Las referencias se revisaron mediante las exportaciones del inventario. Los marcos de escritorio miden 1440 × 900 y los móviles 390 × 844. Se reutilizan `static/img/eva-mascota-bienvenida.png` y `static/img/eva-mascota-alerta.png` del repositorio. El contorno de plato y hojas es un SVG decorativo propio del login. El icono de copia también es SVG propio. Las fotos, máscaras y QR conservan sus superficies. La galería no incorpora miniaturas de platos.

## Verificación

- 545 pruebas Django y 46 de frontend.
- Nueve escenarios de QA a 1440 × 900 y 390 × 844. Se comprobaron login y error, el grupo de Histórico con bandeja y 0 %, el estado vacío, los diagnósticos plegados, la copia del UUID, las seis máscaras sintéticas de Cocina y el acceso a las acciones secundarias.
- Los datos de pantalla son sintéticos. Las comparaciones antes/después usan el mismo escenario y la revisión de main indicada arriba.
- Se conservaron selectores, cálculos, criterios, filtros, paginación, permisos y operaciones. La agrupación de Histórico se aplica a la presentación después de obtener la página. Los grupos de comparación siguen separados.
- Quedan pendientes las pruebas físicas previamente registradas. La limpieza de QA se mantiene separada.
