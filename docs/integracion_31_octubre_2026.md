# Integración de entregas: 31 de octubre de 2026

Se combinaron los PR #14–#22 preservando los commits de sus autores y se añadieron
correcciones de unión. No se desplegó esta revisión en AWS ni se modificaron datos
operativos; todas las pruebas usan bases/archivos temporales.

## Correcciones necesarias

- Se define ConfirmarRetornoForm, importado por las vistas pero ausente en Lino.
- Se declara Pillow>=12.3,<13, validado con la instalación existente 12.3.0.
  No se instalaron ni actualizaron paquetes en este trabajo.
- El validador consume límites de settings; copia solo píxeles, conserva orientación
  y dimensiones y elimina EXIF/metadatos también en PNG. Comprueba tamaño final.
- La navegación conecta búsqueda/captura/retorno reales, manteniendo el alta y la
  confirmación del bloque inicial por compatibilidad.
- Storage local rechaza backend S3 hasta que exista el adaptador. Una foto con
  backend S3 nunca se lee del directorio local por accidente.
- Fallos de limpieza de huérfanos quedan en logs EVA_CAPTURE_ORPHAN con clave opaca,
  sin token ni nombre del archivo cliente. Todavía requieren reintento operativo;
  no se presenta como implementado un scheduler de limpieza.
- Las sesiones usan EVA_CAPTURE_LINK_TTL_SECONDS (300 por defecto) y revalidan plazo
  al completar la transacción para impedir aceptación después de la caducidad.
- Pruebas antiguas de permisos se adaptan a modelos ya migrados. Administración
  recibe exactamente anulación/reemplazo, sin captura general, edición ni borrado.

## Validación ejecutada

- manage.py check: sin incidencias.
- manage.py test: 142 aprobadas, 51.493 s, base SQLite temporal.
- node --test tests/frontend/*.test.cjs: 7 aprobadas.
- manage.py makemigrations --check --dry-run: sin cambios.
- git diff --check: correcto.

Se añadieron 12 pruebas de unión: dos operadores, autoría, liberación, privacidad
HTTP, confirmación histórica, CSRF/roles, retorno sin servido, duplicado, fallos
storage/BD/limpieza, S3 sin fallback, PNG sin EXIF, límites y carrera de expiración.
No se afirman pruebas reales de AWS ni de concurrencia simultánea del motor final.

## Alcance que sigue abierto

B2 funciona con almacenamiento privado local y pruebas HTTP. Falta el ensayo
físico de etiquetas/cámara, flujo de anulación/reemplazo por Administración,
protocolo/checklist versionado y política de conservación completa.

B3 integra modelos/servicios de Isaac y las interfaces preparadas de Jean, además
de la base de César y las pruebas de Eduardo. Lino todavía debe entregar el
adaptador S3 y los endpoints crear/cancelar/estado/captura vinculada, con login,
roles, CSRF, idempotencia y compensación. Las plantillas no se exponen mediante
rutas ficticias. La prueba real PC→teléfono→S3 sigue pendiente.

Los documentos del 28/29 se conservan como historial. Para desplegar hay que
versionar los ajustes de producción, respaldar la BD del servidor y seguir el
procedimiento operativo; un merge no equivale a despliegue.
