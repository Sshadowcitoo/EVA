# Checklist y captura vinculada — bloques 2 y 3

En servido y retorno, Registro confirma encuadre completo del plato, vista superior y luz suficiente. Son declaraciones del operador, no una certificación automática de calidad. Se guardan `protocolo_version=captura-v1` y las tres confirmaciones en `FotografiaServicio`. La migración aditiva 0007 conserva las fotografías anteriores con versión vacía y checklist vacío.

`FotografiaServicio.fecha` es la hora automática del registro en EVA, mostrada en la zona horaria de Ecuador. No representa el EXIF ni una hora manual de toma; los metadatos originales se eliminan antes de almacenar.

Desde la pantalla de foto, «Capturar con celular mediante QR» abre la vinculación. Crear enlace es POST con CSRF; genera un secreto aleatorio de 256 bits y guarda únicamente su hash. El QR se genera localmente como SVG embebido. Caduca a los 300 segundos y permite una sola fotografía del servicio y etapa asignados. Generar otro cancela el pendiente anterior. Recargar la pantalla de escritorio requiere generar uno nuevo, ya que no se recupera el secreto desde la base de datos.

El celular debe iniciar sesión con rol Registro. Puede ser otro operador autorizado; el número de bandeja o el enlace por sí solos no conceden acceso. Se verifican CSRF, vigencia y estado al guardar. El guardado de archivo precede a la transacción; ante rechazo se compensa el archivo. El reintento de una captura completada muestra el resultado terminal y no sobrescribe. Capturar directamente invalida el enlace pendiente al consultarlo. Anular el servicio también cancela sus enlaces.

La computadora consulta el estado cada tres segundos, sin caché, y anuncia éxito solo al recibir `COMPLETADA`. Muestra la imagen mediante el acceso privado de Django; no publica claves ni URLs de S3. Los errores de red permiten reintentar la consulta. El QR de vinculación es distinto del QR permanente de la bandeja.

Configurar `EVA_CAPTURE_BASE_URL` con el origen HTTPS público de EVA para usar teléfonos reales. En desarrollo, un enlace a 127.0.0.1 solo funciona en el mismo equipo. Nunca registrar cadenas de consulta que incluyan el token: `django.server` incorpora un filtro de redacción; la instalación pública mantiene desactivado el registro de URLs de acceso en Nginx y Gunicorn. Las respuestas sensibles llevan `no-store` y conservan la política `same-origin` necesaria para CSRF.

## Comprobación

- Pruebas HTTP con clientes independientes: checklist requerido, permisos, CSRF, servido y retorno por distintos operadores, cancelación, caducidad, regeneración, duplicados, compensación de almacenamiento e historial anterior.
- Pruebas JavaScript: vista previa, límites, consulta, pausa y recuperación ante errores.
- Comprobación visual local: foto técnica desde una segunda pestaña y confirmación automática en la computadora. Esto no sustituye una prueba con cámara y teléfono físicos.

Este cambio no activa eliminación por retención ni modifica recursos, permisos IAM o cuentas de AWS.
