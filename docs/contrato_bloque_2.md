# Contrato del bloque 2: bandejas, QR y captura

Base: `main` en `8f685bf`, bloque inicial integrado. Responsable de este contrato:
César. Los modelos, almacenamiento y endpoints descritos a continuación todavía
los implementan Isaac y Lino; este documento no los presenta como terminados.

## Decisión de acceso confirmada el 28/10/2026

Cualquier usuario activo, autenticado y con el grupo **Registro** puede localizar
una bandeja por su etiqueta o número y registrar el servido o retorno, aunque no
haya creado el servicio. Cada fotografía guarda su propio autor y fecha;
`Servicio.creado_por` no cambia al registrar un retorno.

El identificador permite localizar; no autoriza por sí solo. Un QR no inicia
sesión ni otorga un rol. Cocina y Administración no heredan Registro, y `is_staff`
no lo sustituye. Se conserva el acceso técnico del superusuario activo que ya
existe en los helpers; probar las restricciones con cuentas operativas normales.

Esta decisión se aplica a los **nuevos endpoints de captura**. La ruta existente
`captura:confirmacion` conserva su política de solo creador. No ampliar esa vista
como efecto secundario ni modificarla para resolver el retorno: usar la pantalla
operativa del nuevo flujo. Registrar esta distinción en las pruebas.

No crear un listado general de servicios de otros operadores para localizar un
retorno. Resolver una etiqueta/número exacto y devolver únicamente el servicio
con asignación abierta y los datos necesarios: bandeja, plato, porción, estado y
referencias autorizadas de sus fotos. No devolver nombre del cliente, listado de
usuarios, rutas físicas de archivos ni secretos. Etiqueta revocada o servicio no
localizable: 404; usuario autenticado sin Registro: 403; anónimo: login con next.
Todas las mutaciones requieren POST y CSRF; un GET nunca asigna o libera bandejas.

## Propiedad de archivos y ramas

| Responsable | Archivos / entrega |
| --- | --- |
| César | Este contrato, `config/settings.py`, `config/urls.py`, `apps/catalogo/permissions.py`, comando de grupos y pruebas de sus garantías. |
| Isaac | `apps/captura/models.py`, migraciones, `services.py` y carga repetible de bandejas. |
| Lino | `apps/captura/forms.py`, `views.py`, `urls.py`, `storage.py`; consume los servicios de Isaac. |
| Jean | `templates/captura/`, JS de captura y CSS; `base.html` coordinado con César. |
| Eduardo | Suite funcional del bloque, matriz de errores, README y evidencias integradas. |

Rama de César: `cesar-b2-contratos-permisos`. Crear las ramas nuevas del equipo
desde `main` actualizado. Abrir PR sin hacer merge; César integra. No reabrir ni
reutilizar las ramas del bloque inicial. No reescribir migraciones compartidas.

## Contrato de datos para Isaac

Estos nombres concretan la guía y son la interfaz propuesta para coordinar PR;
si requieren un cambio de arquitectura o datos, resolverlo antes de migrar.

- `Bandeja`: UUID, número visible único y activo.
- `EtiquetaBandeja`: código aleatorio único, bandeja, emisión y revocación.
  Una etiqueta vigente por bandeja; no codificar un UUID de comida como etiqueta
  permanente. Reemplazar revoca la anterior sin borrar historial ni cambiar el servicio.
- `AsignacionBandeja`: servicio, bandeja, inicio y fin. A lo sumo una asignación
  abierta por bandeja y por servicio. La búsqueda por etiqueta resuelve la vigente.
- `FotografiaServicio`: UUID, servicio, etapa `SERVIDO`/`RETORNO`, backend,
  clave opaca, tipo real, tamaño, dimensiones, autor y fecha. Una fotografía
  aceptada por etapa. La recaptura posterior a aceptación no se habilita aún.
- `Servicio`: conservar UUID, creador e instantáneas. No remapear datos históricos
  ni inventar fotos para servicios anteriores. Incorporar estado de captura
  compatible con los registros anteriores mediante migraciones nuevas.

Estado nuevo: `PENDIENTE_SERVIDO` -> `EN_ESPERA_RETORNO` -> `PAR_COMPLETO`.
`ANULADO` es terminal y conserva motivo/autor. Un registro anterior sin datos
nuevos se trata como histórico, no como un servicio operativo incompleto.
No confundir `PAR_COMPLETO` con análisis o revisión de Cocina.

Aceptar retorno o anular libera la asignación; un error no libera. Reutilizar la
bandeja crea otra asignación y servicio sin tocar fotos o composición anteriores.
Decisión aprobada el 28/10/2026: solo Administración puede anular servicios y
reemplazar etiquetas. Exigir motivo, responsable y fecha, con POST y CSRF.
Registro no recibe estas acciones. Usar los permisos personalizados
`captura.anular_servicio` y `captura.reemplazar_etiquetabandeja`; Isaac los declara
en Meta.permissions y migraciones de Servicio y EtiquetaBandeja, respectivamente.
El comando de grupos los asigna cuando existan, sin crearlos artificialmente.
No conceder borrado genérico ni edición de fotos. Reemplazar una etiqueta
conserva bandeja, asignación y servicio; revoca el código anterior sin perder historial.

Proteger exclusividad con restricciones y actualizaciones condicionales dentro
de transacciones. `select_for_update` por sí solo no garantiza exclusión en SQLite.
No mantener una transacción de BD abierta durante una subida de archivo larga.
Un doble clic/reintento debe ser idempotente; un segundo envío distinto de la
misma etapa se rechaza sin sobrescribir la captura aceptada.

## Permisos compartidos

Registro conserva los permisos existentes y prepara estos permisos estándar:

- `captura.view_bandeja`
- `captura.view_etiquetabandeja`
- `captura.view_asignacionbandeja`
- `captura.add_fotografiaservicio`
- `captura.view_fotografiaservicio`

`configurar_roles` no inventa ContentTypes ni permisos. Informa los pendientes;
se ejecuta de nuevo tras integrar las migraciones de Isaac. No asigna usuarios a
Registro ni modifica contraseñas. Conserva permisos de aplicaciones ajenas y
sincroniza únicamente catálogo/captura como en el bloque inicial.

Los permisos de modelo no sustituyen los controles de rol, etapa, archivo y
servicio de cada endpoint. El rol se comprueba también en la lectura de imágenes,
no solamente en sus botones. Reutilizar `roles_required(REGISTRO)` y `tiene_rol`.
No introducir otro sistema de roles ni un modelo de usuario distinto.

## Configuración privada para Lino

`config/settings.py` prepara:

| Ajuste | Valor de partida |
| --- | --- |
| `EVA_CAPTURE_PRIVATE_ROOT` | Directorio `eva-private/capturas` hermano del checkout; reemplazable por variable de entorno del proceso. |
| `EVA_CAPTURE_MAX_BYTES` | 10 MiB por archivo. |
| `EVA_CAPTURE_MAX_PIXELS` | 20 millones de píxeles por imagen. |
| `EVA_CAPTURE_ALLOWED_TYPES` | JPEG y PNG. |

Estos valores son un punto de partida configurable en código para el piloto;
**declararlos no implementa su validación**. Antes de aceptar cargas, Lino debe
consumirlos y comprobar contenido decodificable, tipo real, dimensiones y tamaño.
No confiar en extensión ni MIME aportado por el navegador. No cargar imágenes
grandes completamente sin límites de decodificación.

Si se establece `EVA_CAPTURE_PRIVATE_ROOT`, usar una ruta absoluta y comprobar
que no está dentro del repositorio, `STATIC_ROOT`, `STATICFILES_DIRS` ni una ruta
servida públicamente. Resolver rutas y comprobar confinamiento de las claves;
rechazar traversal y nombres absolutos del cliente. No crear el directorio al
importar settings. No usar FileSystemStorage con URL pública por defecto.

No se publica `MEDIA_URL`, no se agregan rutas `static(...)` y no se conecta
ninguna vista inexistente en `config/urls.py`. `/captura/` ya está registrado;
Lino amplía el `urls.py` de esa app con endpoints implementados.

Interfaz propuesta en `storage.py`: `guardar(archivo, clave)`, `abrir(clave)` y
`eliminar(clave)`. Generar claves internas por servicio/etapa/UUID. Definir antes
del PR el valor de retorno de guardar (backend, clave, tipo, bytes, dimensiones)
y los errores estables que recibirán las vistas y pruebas. El bloque 3 cambia el
adaptador a S3 sin cambiar la identidad del servicio/foto.

Guardar archivo y metadatos con compensación: no mostrar éxito hasta tener ambos.
Si falla la BD tras guardar, eliminar el objeto huérfano o registrar limpieza
reintentable; si falla almacenamiento, no avanzar estado. Leer solo desde una
vista Django autorizada; no devolver una ruta absoluta al navegador.

## Rutas, pantallas y contratos de integración

Namespace existente: `captura`. Conservar `nueva_bandeja` y `confirmacion`.
Nombres nuevos propuestos: `resolver_bandeja`, `foto_servido`, `buscar_retorno`,
`foto_retorno`, `imagen`. Lino fija paths y parámetros en el PR de contrato antes
de que Jean conecte botones; no crear endpoints vacíos para que reverse pase.

`resolver_bandeja` no asigna al escanear; la creación/asignación se confirma en
POST. El retorno debe confirmar plato y bandeja antes de aceptar la foto.
Variables: `servicio`, `bandeja`, `form`, `etapa` y URL de imagen autorizada;
no pasar rutas del disco a plantillas. Formularios multipart con CSRF.

Errores visibles: desconocido/revocado, bandeja ocupada, etapa inválida, retorno
sin servido, duplicado, archivo inválido, fallo de guardado, sesión caducada y
permiso denegado. Seleccionar/repetir antes de aceptar no sobrescribe fotos previas.

Jean usa W06/W07 y M02-M06 de Figma como referencias; comprueba marcos concretos,
390 x 844 y 1440 x 900. Mantener referencia visual del 70 % y navegación móvil.
La selección de archivo es alternativa; no prometer cámara/escaneo en vivo en
cualquier teléfono. HTTPS y la vinculación temporal se resuelven en bloque 3.

## Herramientas y límites aprobados el 28/10/2026

Selección aprobada: `qrcode` para generar QR, `jsQR` para leerlos en el navegador
y `Pillow` para validar/decodificar imágenes en Django. Se mantienen JPEG/PNG,
10 MiB y 20 megapíxeles; ofrecer ingreso manual del número si falla el escaneo.
La selección no instala paquetes ni implementa funciones. Al integrarlas, fijar
versiones compatibles y conservar licencia de jsQR como recurso estático local,
sin CDN ni servicios externos para generar QR con datos operativos.
Pillow no sustituye la IA: comprobar bytes, formato real y dimensiones antes de
aceptar; corregir orientación y tratar archivos corruptos y límites de descompresión.
César prepara las imágenes del piloto por separado; probar el flujo con archivos
pequeños de prueba no requiere tener entrenado el modelo IA.

## Verificación y puerta de cierre

Parte de César: `manage.py check`, suite completa, `makemigrations --check --dry-run`
y `git diff --check`. Sus pruebas de permisos pueden simular la disponibilidad de
ContentTypes en la base temporal de test; nunca crearlos en la base operativa para
ocultar migraciones faltantes.

Eduardo verifica específicamente que un segundo operador Registro capture retorno
sin cambiar el creador, sin ampliar la confirmación histórica, y que otros roles o
anónimos no puedan acceder por conocer el QR/UUID. Añadir casos de etapa/archivo,
duplicación, concurrencia y fallo de almacenamiento cuando existan las vistas.

Integración: contrato/configuración -> modelos Isaac -> funciones Lino -> pantallas
Jean -> pruebas/evidencias Eduardo. Tras cada integración ejecutar el conjunto.
No cerrar bloque 2 hasta completar servido-retorno privado con dos operadores,
liberación/reutilización de bandeja y conservación de servicios anteriores.

Esta parte prepara al equipo: no implementa modelos, capturas, S3, IA, QR ni sus
pantallas, y no declara ejecutadas pruebas funcionales de componentes aún ausentes.
