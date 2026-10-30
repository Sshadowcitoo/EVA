# Plan de pruebas del bloque 2: bandejas, QR y captura

Responsable: Eduardo. Rama: `eduardo-pruebas-bloque-2`. Fecha: 28/10/2026.

Revisión de guías: se leyeron las ocho páginas de `EVA_Guia_equipo_bloque_2.pdf` y las ocho de `EVA_Guia_equipo_bloque_3.pdf` (27/10). Se mantiene esta rama ya publicada; `eduardo-b2-pruebas` es el nombre propuesto en la guía, no una segunda entrega que deba duplicarse. La consulta remota del 28/10 encontró el contrato de César actualizado en `d375ba2`, sin ramas publicadas `isaac-b2-bandejas-fotos` o `lino-b2-flujos-captura` y con main aún en `8f685bf`.
Base: `main` integrado en `8f685bf`. Referencia leída: `docs/contrato_bloque_2.md` de `origin/cesar-b2-contratos-permisos`; el contrato del bloque 3 se consultó para delimitar dependencias futuras. No se incorporaron esas ramas.

**Estado: planificación, no implementación ni pruebas ejecutadas del bloque 2.** La base inicial pasó 56 pruebas, según `cierre_bloque_inicial_28_octubre.md`.

**Actualización 29/10:** ya hay implementación parcial de pruebas de dominio y almacenamiento. La [revisión actual](revision_bloques_29_octubre.md) sustituye el estado anterior para esta entrega: 96 pruebas combinadas, 94 aprobadas y dos fallos documentados. No declarar el bloque ni la suite completa aprobados. Los estados/ausencias indicados más abajo corresponden a la preparación inicial salvo actualización explícita.

## Accesos: dos políticas distintas

- Confirmación anterior: solo Registro creador. Conservar el 404 para servicios ajenos o históricos sin creador.
- Flujo operativo nuevo: cualquier usuario activo de Registro puede localizar bandeja y registrar servido/retorno, aunque no sea creador. La fotografía guarda su autor real; no cambia `Servicio.creado_por`.
- QR físico identifica bandeja; no autentica, no concede rol y no es el UUID permanente del servicio.
- Anónimos van al login con next; usuarios sin Registro reciben 403; etiqueta revocada/desconocida o servicio no localizable reciben 404.
- GET no asigna, libera ni guarda. POST requiere CSRF. Superusuario es excepción técnica; comprobar roles con usuarios normales.

## Casos para implementar al publicarse los contratos ejecutables

Todos los casos siguientes están pendientes. Verificar estado HTTP/errores, filas, estados de dominio y efectos en archivos. Usar datos y archivos pequeños generados en pruebas, sin fotos personales ni conexión AWS.

| ID | Situación | Resultado esperado |
|---|---|---|
| B2-01 | Resolver número/etiqueta vigente exactos | Servicio abierto correcto y datos mínimos, sin listados generales ni datos de usuarios |
| B2-02 | Etiqueta desconocida, revocada o bandeja sin asignación abierta | 404 sin cambios |
| B2-03 | Crear y asignar servicio | Una asignación abierta por bandeja y por servicio, instantáneas conservadas |
| B2-04 | Bandeja ocupada, doble clic o peticiones concurrentes | Sin dos asignaciones abiertas; respuesta estable, sin altas parciales |
| B2-05 | Capturar servido válido | Foto y metadatos privados; transición PENDIENTE_SERVIDO → EN_ESPERA_RETORNO |
| B2-06 | Segundo operador Registro captura retorno | Mismo servicio, autor de foto distinto; creador original intacto |
| B2-07 | Retorno aceptado | PAR_COMPLETO, asignación liberada; no implica análisis ni aprobación de Cocina |
| B2-08 | Reutilizar bandeja | Servicio/asignación nuevos, historial y fotos anteriores intactos |
| B2-09 | Retorno sin servido, etapa desconocida o servicio anulado | Rechazo sin foto aceptada, avance ni liberación indebida |
| B2-10 | Reintentar el mismo envío | Idempotencia según identificador contractual; ninguna duplicación |
| B2-11 | Segundo archivo distinto para etapa aceptada | Rechazo sin sobrescribir foto anterior |
| B2-12 | JPEG/PNG reales dentro de límites | Aceptados con tipo real, bytes y dimensiones verificados |
| B2-13 | Corrupto, extensión/MIME engañoso, formato no permitido | Rechazo sin captura válida falsa |
| B2-14 | Archivo >10 MiB o imagen >20 millones de píxeles | Rechazo conforme a settings, incluyendo límites y valores inmediatamente superiores |
| B2-15 | Clave con traversal, ruta absoluta o nombre manipulable | Rechazo; ninguna escritura/lectura fuera de raíz privada |
| B2-16 | Fallo de almacenamiento | No éxito, no avance de estado ni liberación; reintento posible |
| B2-17 | Archivo guardado y fallo posterior de BD | Compensación elimina huérfano o registra limpieza reintentable |
| B2-18 | Lectura de foto por anónimo, Cocina o Administración sin Registro | Denegación sin bytes, claves ni rutas privadas |
| B2-19 | GET sobre asignación, liberación o captura | Ninguna mutación; método rechazado cuando corresponda |
| B2-20 | POST sin CSRF con sesión autorizada | 403 sin cambios; separar esta prueba de las de rol |
| B2-21 | Foto de servicio/etapa equivocados | No asociación cruzada ni filtración de archivos |
| B2-22 | Servicio anterior al bloque | Sigue legible; sin inventar fotos, bandejas o estados operativos nuevos |
| B2-23 | Acceder a confirmación antigua desde otro Registro | Conserva 404 aunque el nuevo flujo operativo permita retorno por otro operador |
| B2-24 | Reemplazo de etiqueta/anulación | Historial y exclusividad preservados; endpoints pendientes de ratificar operador autorizado |

### Ajustes al contrato vigente y cobertura adicional

En B2-24 la autoridad ya está ratificada: **solo Administración**, con motivo, autor y fecha, POST y CSRF. Registro/Cocina no reciben esas acciones. Los permisos personalizados son `captura.anular_servicio` y `captura.reemplazar_etiquetabandeja`, declarados por Isaac mediante modelos/migraciones; no crearlos artificialmente en la base operativa. El reemplazo conserva bandeja, asignación y servicio, revocando el código anterior.

| ID | Situación adicional de guía/contrato | Resultado esperado |
|---|---|---|
| B2-25 | Anulación con motivo vacío o usuario sin Administración | Error/denegación sin liberar asignación ni cambiar estado |
| B2-26 | Administración anula correctamente | ANULADO terminal, motivo/autor/fecha; libera bandeja y conserva historia |
| B2-27 | Administración reemplaza etiqueta | Una etiqueta vigente; anterior revocada, mismo servicio y asignación |
| B2-28 | Repetir cargar_bandejas_demo | Lote demo acordado (propuesta: 10), sin duplicar ni sustituir etiquetas/datos operativos |
| B2-29 | PNG/JPEG vacío o con orientación EXIF | Vacío rechazado; orientación corregida según contrato, dimensiones coherentes |
| B2-30 | Subida interrumpida o archivo rechazado para etapa ocupada | Sin éxito falso ni eliminación/sobrescritura de la foto aceptada |

Límites de tamaño: el contrato concreto usa **10 MiB = 10.485.760 bytes**, frente al texto genérico de 10 MB de la guía. Probar el valor exacto del setting, uno menos y uno más; tamaño en bytes y máximo de píxeles son restricciones independientes. Probar tipo real incluso cuando el nombre/extensión y MIME del navegador sean engañosos; el resultado de aceptar/rechazar un archivo válido mal etiquetado debe quedar fijado por la política del validador, sin confiar en el dato del navegador.

## Archivos de prueba y preparación de datos

La guía propone separar dentro de Django, sin otra herramienta ni suite duplicada:

| Archivo | Cobertura a implementar | Dependencia concreta |
|---|---|---|
| `apps/captura/test_bandejas.py` | Exclusividad, etiquetas, carga repetible, estados/liberación, históricos y concurrencia | Modelos, migraciones y firmas services de Isaac |
| `apps/captura/test_fotografias.py` | JPEG/PNG, bytes/píxeles, orientación, privacidad y compensación | Validador, excepciones y almacenamiento de Lino |
| `apps/captura/test_integration_captura.py` | Dos operadores, permisos GET/POST/CSRF, búsqueda y par servido/retorno | Rutas/vistas reales, datos de Isaac y plantillas de Jean |

No se crearán archivos con imports de modelos inexistentes ni pruebas vacías que aparezcan aprobadas. Preparar usuarios Registro A, Registro B, Cocina, Administración y sin rol; un usuario mixto adicional comprueba permisos explícitos. Crear los archivos sintéticos solo en la base/raíz temporal de pruebas; las fotos de César para IA no son un prerrequisito.

Para fallos de almacenamiento, provocar error de escritura/lectura y fallo de BD después de guardar, verificando filas, bytes y estado. Para concurrencia, barreras coordinadas y conexiones independientes; distinguir conflicto de negocio de bloqueo SQLite, sin aceptar un error técnico genérico como prueba de exclusión correcta. El motor final debe repetir los casos.

Manual pendiente: 390×844 y 1440×900, cámara denegada, selección de archivo alternativa, pérdida de red, previsualización/repetición antes de guardar, datos de servicio/bandeja correctos y éxito únicamente tras respuesta real. Guardar referencia de Figma y capturas sin credenciales. Un retorno vacío puede ser una fotografía válida; no confundirlo con un archivo vacío ni inferir porcentaje de sobrante.

## Dependencias y organización

Isaac publica modelos, migraciones, servicios atómicos y carga repetible de bandejas. Lino fija paths/parámetros y consume esos servicios, además de storage privado. Jean conecta las pantallas reales. No crear endpoints ficticios para que reverse pase ni importar modelos aún inexistentes en la suite funcional actual.

Reutilizar las pruebas existentes en `apps/captura/tests.py` y la estructura que el equipo acuerde si crece. Usar TestCase/Client/reverse; para carreras reales escoger pruebas transaccionales y conexiones independientes, conforme al motor. SQLite no garantiza exclusión con select_for_update: probar la restricción y el resultado observado, sin afirmar equivalencia con otro motor.

Almacenamiento: directorio temporal exclusivo, override de settings y dobles controlados para fallos; nunca escribir en la raíz privada real. Las migraciones se prueban en BD temporal, no sobre la única copia de datos útiles. El archivo y la BD necesitan compensación; una transacción no revierte por sí sola los bytes del disco.

## Pendientes que requieren contrato

- Paths, parámetros y respuesta de `resolver_bandeja`, `foto_servido`, `buscar_retorno`, `foto_retorno` e `imagen`.
- Formato estable de errores e identificador de idempotencia.
- Retorno de `storage.guardar` y excepciones de guardar/abrir/eliminar.
- Política de lectura de fotos históricas o servicios cerrados por otro operador.
- Paths concretos de anulación/reemplazo; la autoridad Administración ya está aprobada.
- Versiones compatibles de los paquetes aprobados: qrcode, Pillow y jsQR local con licencia. La aprobación no implica que estén instalados; no instalar por iniciativa de esta suite.

Estos puntos no impiden preparar escenarios; sí impiden escribir aserciones definitivas contra interfaces inventadas.

## Cierre y siguiente bloque

### Primer código ejecutable de Eduardo — 28/10/2026

Se añadió `apps/captura/test_permisos_bloque_2.py` con tres pruebas complementarias a las de César. No importa modelos futuros ni inventa endpoints. Los ContentTypes/permisos que representan migraciones futuras se crean solo en la BD temporal de Django:

- La sincronización repetida retira privilegios indebidos en Registro, Cocina y Administración, conservando únicamente captura o acciones privilegiadas según su matriz.
- Conserva contraseña, grupos ajenos y permisos directos del usuario; el comando no puede usarse para retirar permisos directos extraordinarios que no gestiona.
- Retirar la membresía Registro elimina el permiso efectivo de captura, consultando una instancia nueva para evitar caché de has_perm.

Ejecución en `.revision-b2`, worktree aislado sobre la base de César `d375ba2`, copiando únicamente el archivo de pruebas nuevo:

```powershell
..\.venv\Scripts\python.exe -B manage.py test apps.captura.test_permisos_bloque_2 --verbosity 2
```

**Resultado real: 3 pruebas aprobadas en 0.139 s**, configuración sin problemas y BD temporal creada/eliminada. Esta evidencia no demuestra endpoints, restricciones reales de modelos futuros, flujo servido/retorno o AWS. En main sin la nueva matriz de César no se espera aprobar el caso de asignación de permisos futuros; debe declararse esa dependencia en el PR.

Se amplió luego a `manage.py test apps.catalogo apps.captura --verbosity 1` en esa misma copia: **63 pruebas aprobadas en 26.100 s** (56 integradas anteriores, 4 de César para bloque 2 y 3 complementarias de Eduardo). `makemigrations --check --dry-run`: `No changes detected`. No equivale a 63 escenarios completos del bloque 2: la mayoría corresponde al bloque inicial y a contratos de permisos.

No se crearon archivos vacíos `test_bandejas.py` o `test_fotografias.py` para simular progreso. Su implementación empieza al publicarse contratos ejecutables de Isaac/Lino. No se instalaron paquetes ni se hizo merge.

Tras integrar dependencias: check, suite de catálogo/captura, migraciones sin cambios; recorrido de dos operadores, servido/retorno privado, liberación/reutilización e historia anterior conservada. Registrar commit, comandos, resultados, fallos y evidencias en 390×844 y 1440×900 con referencias Figma.

Bloque 3 separado: enlaces temporales autenticados con caducidad/cancelación/consumo, QR PC→teléfono, polling privado y S3 real. Preparar posteriormente pruebas de autorización, token, expiración e idempotencia con dobles. Un stub no demuestra AWS/HTTPS real; la evidencia real requiere cuenta/prefijo autorizados y dispositivo. No crear recursos ni guardar secretos para este plan.

Cada integrante entrega PR; solo César integra. No reutilizar la rama del bloque inicial ni mezclar ramas ajenas. No cerrar RF/HU completos por aprobar este bloque parcial.
