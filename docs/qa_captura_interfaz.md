# Correcciones de QA en captura

La revisión parte de `origin/main` en `7615a24be096128564008201de4a527bfd5d37e7`.

| Hallazgo | Comportamiento corregido |
| --- | --- |
| Bandeja, etiqueta o servicio inexistente | La búsqueda indica qué identificador no se encontró y conserva la consulta. Los enlaces directos a servicios no disponibles muestran una pantalla de ayuda con HTTP 404. |
| Consulta vacía | Al enviar campos vacíos aparece la indicación de búsqueda. Al abrir la pantalla por primera vez se muestra la ayuda de la etapa. |
| Número inválido | Se comprueban los dígitos ASCII, la longitud y el rango antes de consultar la base. `²`, `1.0`, números fuera de rango y entradas de 5000 caracteres se rechazan en el formulario. |
| POST vacío | El alta, la confirmación y las capturas validan el formulario y muestran sus campos obligatorios. |
| Ayuda y navegación | El menú distingue registro básico, servido y retorno. La confirmación del servido enlaza a la búsqueda de retorno de la misma bandeja. Cada etapa explica qué revisar. |
| Lote y decimales | Se muestra el lote guardado al revisar el contexto del servicio, incluso en captura vinculada y gestión. Los límites visibles de captura usan coma decimal y los atributos que lee JavaScript conservan sus valores numéricos. |

## Pruebas

- 574 pruebas Django ejecutadas, 571 correctas y tres de paridad ONNX omitidas por requerir el paquete privado. Ocho regresiones nuevas con cliente HTTP y ORM.
- 42 pruebas de frontend correctas.
- `manage.py check`, `makemigrations --check --dry-run` y `git diff --check` correctos.
- Chromium 153 con un servidor Django local y una base SQLite aislada. En ambas resoluciones se verificaron el valor conservado, los errores de búsqueda y del POST de retorno, el lote y el límite de 1,50 MiB configurado para el ensayo. Se comprobó el menú móvil y la ausencia de desborde horizontal o excepciones de JavaScript en los recorridos comprobados.

## Capturas de interfaz

Las capturas usan cuentas y registros de prueba. Para la vista de retorno se simuló la retención de la foto del servido en la base aislada. Las imágenes muestran exclusivamente la interfaz.

| Pantalla | Escritorio 1440 × 900 | Móvil 390 × 844 |
| --- | --- | --- |
| Búsqueda con `²` y valor conservado | [Escritorio](evidencias/qa-captura/busqueda-escritorio.jpg) | [Móvil](evidencias/qa-captura/busqueda-movil.jpg) |
| Retorno con lote y validación del POST vacío | [Escritorio](evidencias/qa-captura/retorno-escritorio.jpg) | [Móvil](evidencias/qa-captura/retorno-movil.jpg) |
| Foto del servido con instrucciones y límite decimal | [Escritorio](evidencias/qa-captura/foto-servido-escritorio.jpg) | Verificada en Chromium |

## Pendientes

- Probar la cámara y el lector QR con un dispositivo físico. La comprobación de navegador usó tamaños de pantalla de escritorio y móvil.
- Para investigar un posible fallo de datos, registrar el ID del servicio, la bandeja, la etapa y la hora del caso. Esta revisión solo confirma los fallos reproducidos con registros de QA.
