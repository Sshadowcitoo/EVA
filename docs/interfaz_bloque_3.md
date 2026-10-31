# Jean: interfaz de captura vinculada

Depende de la interfaz del bloque 2 y del contrato #15. Este PR solo cambia
plantillas, CSS, JavaScript y pruebas de presentación. No crea sesiones/tokens,
endpoints, QR del servidor, adaptador S3, permisos ni migraciones.

## Integración con Lino

La vista autorizada renderiza `captura/vincular_celular.html` con:

- Contexto del bloque 2: bandeja, nombres históricos, etapa, `es_retorno`,
  `retorno_url`, `operacion_habilitada` y error de negocio opcional.
- `crear_url` y `cancelar_url`: rutas locales POST con CSRF. `crear_form` y
  `cancelar_form` opcionales conservan campos ocultos e idempotencia del backend.
- `estado`: PENDIENTE, COMPLETADA, CANCELADA o EXPIRADA. `caduca_en`: ISO 8601 con
  zona horaria, generado por servidor. Mostrar solo una solicitud vigente por etapa.
- `qr_url`: imagen local/autorizada generada por qrcode en el servidor; nunca un
  servicio externo. `captura_url`: enlace HTTPS del mismo origen, opcional.
- `estado_url`: endpoint GET privado de esa solicitud. `resultado_url`: ruta local
  al servicio confirmado, opcional. No incluir el token en esa respuesta JSON.

Respuesta mínima de estado: `{"estado": "PENDIENTE"}`. Solo COMPLETADA confirma
guardado; `foto_id` puede conservarse para otros consumidores. Opcionalmente puede
añadirse `foto_url` local, servida por Django con autorización, para la miniatura.
No devolver claves S3, URLs públicas, rutas de disco ni datos personales.
Los errores de guardado de la carga se presentan en el formulario móvil mediante
`error`/errores de campos: no convierten una solicitud pendiente en COMPLETADA.

Polling cada tres segundos, sin consultas solapadas, con timeout de diez segundos,
solo al mismo origen, cookies de sesión, cache no-store y sin seguir redirecciones.
401/403/404/410 detienen la consulta; fallo de red/5xx permite reintentar manualmente.
HTML de login, JSON malformado o estado desconocido no significan guardado exitoso.
Se pausa al ocultar/abandonar la página y termina ante un estado terminal del servidor.
El reloj local oculta el QR al vencer el plazo, pero no presume si una foto ya llegó:
consulta el estado autorizado para resolver esa carrera.

La vista del teléfono usa `captura/captura_vinculada.html` con `vinculo_vigente`
validado por servidor, formulario multipart y `guardar_url`. La autorización se
revalida en POST, aunque el formulario se hubiera abierto antes de caducar. Sin
vigencia no se renderiza input de archivo ni guardado. El backend conserva `next`
local al iniciar sesión y debe impedir cambios de etapa, uso repetido o token ajeno.

Todas las páginas operativas y JSON deben usar Cache-Control private/no-store
en las vistas. Mantener Referrer-Policy same-origin para que CSRF funcione sin
filtrar el enlace a sitios externos. Este PR no altera la política global.

## Diseño y aceptación

Reutiliza dos columnas, tarjetas, colores y tipografía contrastados con W06/W07
en la exportación del prototipo. El panel QR y sus estados son una extensión
consistente: no se afirma que exista un marco idéntico en el archivo Figma.
Móvil se adapta a una columna. Evidencias con datos ficticios en `docs/evidencias/jean`.
El QR de las capturas de revisión es un ejemplo local sin sesión operativa; no es
evidencia de emisión de tokens ni de un guardado real desde el teléfono.

No cerrar el bloque hasta que Isaac y Lino publiquen sus interfaces definitivas,
se conecten estas plantillas a vistas reales y Eduardo verifique PC→teléfono→S3
con dos dispositivos HTTPS, roles, expiración, cancelación y fallos de guardado.
Las pruebas actuales usan dobles de red y datos ficticios; no acreditan S3 real.
