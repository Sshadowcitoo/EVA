# Bloque 3: base compartida de César

Depende del PR #14 (Bloque 2). Esta rama parte de ese PR para no duplicar el
trabajo; integrar primero Bloque 2. No confundir estos bloques de entrega con
los módulos académicos: se mantiene el calendario de la guía del equipo.

## Alcance implementado por César

- Variables de entorno explícitas para backend local/S3, bucket, región, prefijo
  y origen HTTPS de captura. TTL propuesto de enlace: 300 segundos.
- Comprobaciones Django sin llamadas a AWS ni creación de archivos: backend
  conocido, ruta local privada absoluta fuera del checkout/estáticos, configuración
  mínima de S3, prefijo sin traversal y origen de captura HTTPS sin secretos.
- Permisos futuros `add_sesioncaptura` y `view_sesioncaptura` para Registro.
  `configurar_roles` solo los asigna al existir los permisos de las migraciones;
  no crea ContentTypes, usuarios ni secretos para simular disponibilidad.
- `.env.example` sin credenciales. Sus valores se establecen en el entorno del
  proceso: actualmente Django no carga `.env` automáticamente.

Esto **no implementa el adaptador S3 ni los enlaces de captura**. Tener settings
válidos no garantiza un bucket existente, privado o accesible, un certificado
válido, resolución DNS ni conectividad desde el teléfono. El backend local sigue
siendo el valor predeterminado. Activar `s3` solo al integrar el adaptador real.
No se han creado recursos, habilitado cargos, configurado IAM ni llamado a AWS.

## Contratos con Isaac y Lino

`SesionCaptura` propuesta: UUID, servicio, etapa, usuario emisor, digest del token,
creación/caducidad, estado y fotografía resultante. Token aleatorio criptográfico
con al menos 128 bits; guardar solo su digest. Estados: PENDIENTE, COMPLETADA,
CANCELADA y EXPIRADA. Enlace válido por `EVA_CAPTURE_LINK_TTL_SECONDS`.

El QR de bandeja identifica soporte físico; este QR temporal identifica una
solicitud de fotografía para una etapa y un servicio. Ninguno autentica al usuario.
Cualquier usuario activo con Registro puede capturar según la decisión del bloque 2;
el emisor no se convierte en propietario exclusivo del enlace. Registrar el autor
real de la fotografía y conservar creador del servicio y emisor de la solicitud.

Escaneo y GET no guardan archivos ni completan solicitudes. En cada carga POST,
comprobar sesión, rol, solicitud vigente, servicio, etapa y CSRF. Conocer el token
no basta. Permisos de modelo no sustituyen estas verificaciones. No conceder
`change_sesioncaptura` ni `delete_sesioncaptura` genéricos para cancelar/consumir;
operar mediante servicios de dominio con reglas específicas.

Después de expirar/cancelar/usar un enlace, no acepta otra foto. Regenerar invalida
la solicitud pendiente anterior para esa etapa. La repetición del mismo envío debe
ser idempotente; una carga distinta no sobrescribe la aceptada. Comprobar en servidor
la expiración al usar/consultar, sin depender de que una tarea periódica se ejecute.
Isaac y Lino coordinan transacciones, exclusividad y compensación de objetos huérfanos.

Rutas propuestas dentro de `captura`: `crear_vinculo` y `cancelar_vinculo` por POST;
`captura_vinculada` GET/POST autenticado; `estado_vinculo` GET privado. Lino confirma
paths y parámetros antes de que Jean enlace pantallas. La ruta global `/captura/`
ya existe: no se registra ningún endpoint ficticio en la configuración global.

El estado consultado por PC no revela token, nombres de personas, claves S3 ni rutas
locales. Campos mínimos propuestos: estado, etapa, foto_id cuando esté completado
y error de negocio estable. Polling de referencia cada 3 segundos, detenido cuando
finaliza, expira o se oculta/abandona la pantalla; no incorporar WebSockets aún.

## Almacenamiento y autorización

Arquitectura conservada: navegador -> Django -> S3. No usar carga directa desde el
navegador ni URLs prefirmadas como cambio implícito del diseño. Django valida y sirve
las imágenes mediante vistas autorizadas; no entregar credenciales AWS al cliente.
Reutilizar `apps/captura/storage.py` del bloque 2: guardar, abrir y eliminar.

Configurar `EVA_STORAGE_BACKEND=s3`, `EVA_S3_BUCKET`, `EVA_S3_REGION` y un prefijo
específico como `eva/capturas/`. Usar claves opacas por servicio/etapa/UUID. No aceptar
rutas arbitrarias del cliente. Evitar sobrescrituras. Si hay versionado, conservar
VersionId para gestionar correctamente cada archivo/versiones y su eliminación.

La cadena estándar del SDK resuelve credenciales; al desplegar, preferir rol del
entorno. No agregar claves a settings, `.env.example`, PDFs, QR, logs o JS. IAM se
limita al bucket/prefijo y operaciones que requiera el adaptador (escritura, lectura,
eliminación; listar o gestionar versiones solo si el procedimiento lo necesita).
No usar permisos administrativos de toda la cuenta para hacer funcionar una subida.

Antes de operar AWS: confirmar cuenta autorizada, región, bucket/prefijo, permisos,
cifrado, Block Public Access y costes con César. Esta entrega no elige una cuenta
ni crea infraestructura. El SDK usa HTTPS con validación TLS habilitada; no agregar
endpoints personalizados ni desactivar verificación para sortear errores.

Si S3 falla, no pasar silenciosamente a disco local ni marcar captura completada.
Si sube pero falla la BD, borrar el huérfano o registrar limpieza reintentable.
Conservar imágenes previas con su backend local; migrarlas requiere procedimiento
separado con dry-run/verificación y sin borrar el origen antes de confirmar copia.

## Entorno PC y teléfono

`EVA_CAPTURE_BASE_URL` es el origen HTTPS accesible a ambos dispositivos, sin ruta,
query, fragmento ni credenciales. Ejemplo documental: `https://eva.example`.
Debe provenir de configuración del servidor, no de un Host manipulable de la petición.
El token no se incorpora a logs ni a recursos externos; usar no-store y política
Referrer-Policy que no exponga el enlace. Tras login conservar solo destinos locales
validados; no permitir redirecciones abiertas usando el token como argumento.

No usar `127.0.0.1`/localhost en un QR para el teléfono: apunta al propio teléfono.
No se han abierto puertos ni configurado túneles/dominio. Para cámara en vivo se
requiere contexto seguro y compatibilidad del navegador. El origen HTTPS no otorga
por sí solo permisos de cámara; se solicitan al usarla. Jean mantiene alternativa
para seleccionar archivo y estados de error reales.

César configurará `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con el dominio autorizado
cuando exista. No usar `*` ni desactivar CSRF. En el despliegue HTTPS revisar cookies
Secure, DEBUG desactivado, SECRET_KEY externa, certificado y proxy confiable. No
activar `SECURE_PROXY_SSL_HEADER` sin conocer y controlar el proxy: cambia qué
cabeceras se consideran confiables. Estos ajustes de despliegue siguen pendientes;
la configuración local de desarrollo no se convierte en producción por este PR.

## Conservación y evidencias

Conservar fotos y futuras máscaras un máximo documentado de 90 días desde captura,
incluidas versiones y copias recuperables; no reiniciar plazo por cambiar estado.
Planificar borrado con margen, verificación y alertas de fallo antes del límite.
Lifecycle es respaldo y no una garantía de ejecución instantánea. Con versionado,
borrar la clave puede dejar un marcador y conservar bytes de versiones anteriores.
Revisar versiones no vigentes, temporales, multipart incompletos y copias autorizadas.
Implementar el procedimiento y probarlo con objetos de prueba; no borrar datos del
piloto para demostrarlo. No se ha creado scheduler ni regla Lifecycle en esta parte.

## Reparto, integración y aceptación

- César: este contrato, settings, checks, permisos, ejemplo de entorno e integración.
- Isaac: modelo/migración SesionCaptura, metadatos y operaciones atómicas.
- Lino: adaptador S3, endpoints, validación, compensación e idempotencia.
- Jean: QR temporal, captura móvil, espera/errores y actualización de PC, fiel a Figma.
- Eduardo: pruebas con stub, autorización, expiración, fallos y evidencia AWS/HTTPS real.

Integrar Bloque 2 -> base César Bloque 3 -> Isaac -> Lino/Jean -> verificación Eduardo.
Cada integrante abre PR sin merge; César integra y ejecuta la suite completa.

Aceptación real pendiente: PC emite QR -> teléfono con Registro confirma servicio y
etapa -> captura -> Django guarda en S3 privado -> PC refleja foto real. Probar otro
operador, usuario ajeno a Registro, token expirado/cancelado/usado, duplicados y
fallos de red/S3. La suite normal usa dobles sin conexión a AWS; la evidencia real es
opt-in, con prefijo de prueba y acceso autorizado. Un bucket falso o stub no acredita
integración real, y este bloque tampoco acredita precisión de IA.
