# Jean: interfaz del bloque 2

Plantillas sin rutas nuevas ni cambios de modelos. Depende de #14 como base
compartida, y de las vistas/formularios de Lino y modelos de Isaac para integración.
No reemplaza la pantalla de registro actual hasta que esas vistas estén disponibles.

## Contexto que deben entregar las vistas autorizadas

- `buscar_bandeja.html`: `es_retorno`, `buscar_url` local, `bandeja.numero`,
  `servicio`, `plato_nombre`, `porcion_nombre`, `form` y `confirmar_url` local.
  GET busca por `numero`, sin mutaciones; POST confirma con formulario CSRF.
  `lector_habilitado=True` solo cuando la vista admita `etiqueta` (texto QR exacto)
  como alternativa exclusiva a `numero`. Rechazar entradas vacías/ambas y códigos
  desconocidos/revocados en servidor; nunca navegar al contenido arbitrario del QR.
- `fotografia.html`: `etapa` SERVIDO/RETORNO, `bandeja.numero`, nombres históricos
  `plato_nombre`/`porcion_nombre`, `form` con exactamente un campo de archivo,
  `guardar_url` local, opcional `foto_servido_url` privada/autorizada, `max_bytes`
  y `max_pixels` desde settings. La vista valida las etapas y el servicio.
- `estado_servicio.html`: `estado` real después de guardar, datos del servicio y
  `continuar_url` local opcional. No usar esa plantilla para simular un guardado.
- Todas: `operacion_habilitada=True` únicamente al conectar un endpoint real;
  `error` opcional con texto de negocio seguro. Sin endpoint/form el botón no opera.
  Nunca pasar rutas de disco, credenciales o URLs arbitrarias del cliente.

La previsualización es local (object URL), no sube imágenes a terceros. La cámara
del input se solicita por acción del usuario; conserva selección de archivos según
soporte del navegador. Tipo/tamaño/píxeles del navegador son ayuda, no seguridad:
el backend debe validar con Pillow y rechazar falsos tipos, EXIF y corruptos.
La etapa no se toma del texto visible como autorización. CSRF y roles en servidor.

## Referencia y pendientes verificables

Se contrastaron las páginas 6 y 7 de la exportación local «EVA · Flujos móvil y
web · borrador.pdf»: W06 (datos a la izquierda y foto a la derecha) y W07 (búsqueda
horizontal, ayuda azul y pasos del servicio). Se mantienen DM Sans, navegación,
colores, paneles y progresión. La variante móvil es adaptación responsive, no una
certificación del marco móvil original. La equivalencia del 70 % es un criterio
visual aproximado, no una puntuación automática ni una afirmación de igualdad.

El lector embebido usa jsQR 1.4.0 local con licencia Apache-2.0 e integridad npm
verificada. No instala dependencias Python. Cámara solo tras Activar; detiene tracks
al cerrar/ocultar/abandonar. El QR llena el campo etiqueta, sin navegar ni enviar
hasta que el operador pulsa Buscar. Entrada manual disponible ante denegación.

Pruebas de plantillas verifican los controles y estados; no sustituyen pruebas de
permisos, guardado, cámara real, servido-retorno ni concurrencia del bloque completo.
