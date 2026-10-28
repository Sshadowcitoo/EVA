# Plan de pruebas del bloque 2: bandejas, QR y captura

Responsable: Eduardo. Rama: `eduardo-pruebas-bloque-2`. Fecha: 28/10/2026.
Base: `main` integrado en `8f685bf`. Referencia leída: `docs/contrato_bloque_2.md` de `origin/cesar-b2-contratos-permisos`; el contrato del bloque 3 se consultó para delimitar dependencias futuras. No se incorporaron esas ramas.

**Estado: planificación, no implementación ni pruebas ejecutadas del bloque 2.** La base inicial pasó 56 pruebas, según `cierre_bloque_inicial_28_octubre.md`.

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

## Dependencias y organización

Isaac publica modelos, migraciones, servicios atómicos y carga repetible de bandejas. Lino fija paths/parámetros y consume esos servicios, además de storage privado. Jean conecta las pantallas reales. No crear endpoints ficticios para que reverse pase ni importar modelos aún inexistentes en la suite funcional actual.

Reutilizar las pruebas existentes en `apps/captura/tests.py` y la estructura que el equipo acuerde si crece. Usar TestCase/Client/reverse; para carreras reales escoger pruebas transaccionales y conexiones independientes, conforme al motor. SQLite no garantiza exclusión con select_for_update: probar la restricción y el resultado observado, sin afirmar equivalencia con otro motor.

Almacenamiento: directorio temporal exclusivo, override de settings y dobles controlados para fallos; nunca escribir en la raíz privada real. Las migraciones se prueban en BD temporal, no sobre la única copia de datos útiles. El archivo y la BD necesitan compensación; una transacción no revierte por sí sola los bytes del disco.

## Pendientes que requieren contrato

- Paths, parámetros y respuesta de `resolver_bandeja`, `foto_servido`, `buscar_retorno`, `foto_retorno` e `imagen`.
- Formato estable de errores e identificador de idempotencia.
- Retorno de `storage.guardar` y excepciones de guardar/abrir/eliminar.
- Política de lectura de fotos históricas o servicios cerrados por otro operador.
- Autoridad para anular servicio o reemplazar etiquetas.
- Paquetes/versiones autorizados para QR y decodificación de imágenes.

Estos puntos no impiden preparar escenarios; sí impiden escribir aserciones definitivas contra interfaces inventadas.

## Cierre y siguiente bloque

Tras integrar dependencias: check, suite de catálogo/captura, migraciones sin cambios; recorrido de dos operadores, servido/retorno privado, liberación/reutilización e historia anterior conservada. Registrar commit, comandos, resultados, fallos y evidencias en 390×844 y 1440×900 con referencias Figma.

Bloque 3 separado: enlaces temporales autenticados con caducidad/cancelación/consumo, QR PC→teléfono, polling privado y S3 real. Preparar posteriormente pruebas de autorización, token, expiración e idempotencia con dobles. Un stub no demuestra AWS/HTTPS real; la evidencia real requiere cuenta/prefijo autorizados y dispositivo. No crear recursos ni guardar secretos para este plan.

Cada integrante entrega PR; solo César integra. No reutilizar la rama del bloque inicial ni mezclar ramas ajenas. No cerrar RF/HU completos por aprobar este bloque parcial.
