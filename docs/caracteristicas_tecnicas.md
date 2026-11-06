# Características técnicas

Estado de la demo: 6 de noviembre de 2026.

- Aplicación web Django con plantillas HTML, CSS y JavaScript. Se usa desde
  computadora y teléfono mediante HTTPS; no requiere una aplicación móvil nativa.
- Base SQLite en la instancia existente de AWS EC2. Los servicios conservan
  instantáneas de plato, porción, componentes y contexto, aunque cambie el catálogo.
- Fotografías y artefactos privados en Amazon S3; acceso mediante el servidor y
  permisos de usuario. No se entregan claves AWS al navegador. Se comprobó un
  objeto con acceso autorizado y rechazo HTTP 403 sin autenticación.
- Captura JPEG/PNG: máximo 10 MiB y 20 megapíxeles. Pillow valida y recodifica
  imágenes; las etiquetas usan qrcode y el lector usa jsQR. Existe entrada manual.
- QR permanente de bandeja y enlace temporal de captura son identificadores
  distintos. Los enlaces temporales exigen rol Registro y se cierran al aceptar
  la fotografía; no permiten sobrescribirla.
- Motor visual separado con inferencia ONNX en CPU; un worker gestiona análisis,
  intentos y tiempos de espera. La demo mantiene identificada la procedencia
  SIMULADO. El servidor no se amplió para este despliegue.
- Clases del piloto: arroz, pollo, yuca, pescado, carne, menestra y ensalada.
  El maduro fue retirado del catálogo del piloto; se conserva el historial previo.
- Los píxeles compartidos entre máscaras se excluyen y los componentes afectados
  permanecen no concluyentes. La concordancia con otra implementación no demuestra
  precisión real ni generalización a otras preparaciones.
- Roles Registro, Cocina y Administración, protección CSRF y validación en
  servidor. Operaciones de registro atómicas, restricciones de asignación y
  rechazo recuperable de bloqueos SQLite conocidos, sin reintentos automáticos.
- Retención configurada: fotografías de 90 días o más y cargas huérfanas de más
  de 24 horas, conservando el historial. Existen tareas programadas de limpieza
  y respaldo. Se verificó el respaldo y su restauración en una base temporal, con integridad
  y recuentos correctos; no se reemplazó la base productiva.

## Operación y límites

La instancia ejecuta web, motor y worker, con almacenamiento privado y configuración
externa al repositorio. Los secretos, pesos, fotografías y copias de la base no
se publican en GitHub. La actualización conserva el overlay de producción y las
cuentas; se respalda código, configuración y base antes de cambiar la versión.

El conjunto de entrenamiento contiene una sola preparación real de seco de pollo
y material generado para otros platos. No existe validación independiente en un
restaurante real. Los resultados no deben presentarse como precisión certificada,
porcentaje de masa consumida ni recomendaciones operativas ya validadas.
