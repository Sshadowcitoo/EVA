# Acceso, navegación por rol y catálogo

Base de comparación: `origin/main` en `7e241d7`. Las capturas antes y después usan las mismas respuestas HTTP y registros sintéticos de QA. Se comprobaron los tamaños 1440 × 900 y 390 × 844.

| Pantalla y estado | Figma escritorio (1440 × 900) | Figma móvil (390 × 844) | Cambio y diferencia que se conserva |
| --- | --- | --- | --- |
| Acceso y redirección desde ruta protegida | [W09 · 400:456](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-456) | [M01 · 320:24](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=320-24) | Marca y acceso en dos zonas en escritorio. En móvil, encabezado compacto y tarjeta con la mascota junto a la bienvenida. W09 es un selector demo. EVA conserva un formulario de acceso real y el destino solicitado. |
| Credenciales inválidas | [403:56](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-56) | [329:44](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=329-44) | Aviso junto al formulario. Se conserva el mensaje de autenticación y la acción de reintentar. |
| Cuenta sin rol y acceso denegado | Sin marco exacto en los consultados | Sin marco exacto en los consultados | La cuenta sin rol reutiliza el formulario con su aviso. El 403 recupera la navegación disponible del rol y elimina enlaces obsoletos rotulados como pendientes. |
| Menú de Registro | [403:74](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=403-74) | [322:23](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=322-23) | Referencias de inicio de rol. EVA mantiene las rutas de registro básico, servido y retorno. |
| Menú de Cocina | [400:3](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-3) | [322:52](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=322-52) | Referencias de inicio de rol. Se conserva la entrada a pendientes y las consultas autorizadas. |
| Menú de Administración | [W04 · 400:199](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-199) | [324:75](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=324-75) como referencia relacionada de Indicadores | Adaptación del patrón de navegación. EVA conserva los destinos actuales, muestra los roles y reúne los enlaces en una columna en el menú móvil. Escape lo cierra y devuelve el foco. |
| Listado de platos, vacío y tras desactivar | [W04 · 400:199](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-199) como referencia de listado | Sin marco propio identificado | Acción de alta arriba, listado debajo y entrada separada a recomendaciones. Las pestañas, el estado y las acciones por fila se conservan. La columna de actualización muestra un guion si falta el dato. |
| Alta, edición y validación de platos | Sin marco exacto | Sin marco exacto | Adaptación con título de tarea, vuelta a platos, composición agrupada, errores junto a sus campos y acciones de guardar y cancelar. |
| Componentes y porciones, con alta, edición, error y desactivación | Sin marco exacto. Patrón de [W04 · 400:199](https://www.figma.com/design/vSVqy8rmaejpEGo0RwXk66/EVA?node-id=400-199) | Sin marco propio identificado | Mismo patrón del catálogo. Se conserva el código estable en edición y las operaciones POST de activar o desactivar. |

## Verificación y pendientes

- Pasaron 60 pruebas de Django del catálogo y permisos de captura. Se verificaron destinos por rol, credenciales inválidas, redirección segura, CSRF, código inmutable, composición, historial y recuperación de navegación en el 403.
- Se reprodujeron 25 escenarios en Chromium por viewport. En la variante corregida se comprobó el ancho de página, el botón de acceso visible, los avisos, el borrador tras error, el código de solo lectura, y el menú abierto, cerrado y operable por teclado.
- Los datos de QA permiten comprobar el POST de desactivar y reactivar las tres entidades. Se comprobó que desactivar un plato conserva sus dos relaciones de composición. No se añadieron columnas de persistencia ni se cambiaron permisos.
- Quedan pendientes el 404 general, la administración técnica de Django, las páginas de destino de otros módulos y las pruebas visuales en dispositivos físicos. La fecha de actualización que muestra W04 sigue sin dato en el modelo vigente.
