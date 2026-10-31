# Revisión y bloqueos — 29/10/2026

## Versiones y entorno

Consulta remota completada. Main sigue en `8f685bf`; ya se publicaron Isaac B2 `6c6c097`, Lino B2 `7deb742` y las interfaces B2/B3 de Jean. Los nombres de rama pueden avanzar: los resultados de esta revisión no certifican cambios posteriores.

Se creó `.revision-b2-completa` desde Isaac con HEAD separado. Se copiaron solo `apps/catalogo/permissions.py` y `config/settings.py` de la base B2 de César `d375ba2`, `storage.py` de Lino y las pruebas nuevas de Eduardo. No se hizo merge ni se modificó código de producción en las ramas de origen. Base temporal Django y TemporaryDirectory para archivos; sin datos del piloto.

## Resultado ejecutado

| Ejecución | Resultado |
|---|---|
| `manage.py test apps.captura.test_bandejas apps.captura.test_fotografias apps.captura.test_permisos_bloque_2 --verbosity 2` | 14 pruebas: 13 aprobadas y 1 fallo, 1.038 s |
| `manage.py test apps.catalogo apps.captura --verbosity 1` | 96 pruebas: 94 aprobadas y 2 fallos, 35.667 s |
| `manage.py makemigrations --check --dry-run` | No changes detected |

Las cinco pruebas nuevas de dominio comprueban rollback ante fallo de metadatos, cierre de asignación o emisión de etiqueta, preservación de asignación operativa al repetir carga y auditoría después de anular. Todas pasaron. Complementan las pruebas de Isaac sin sustituirlas.

Los seis casos nuevos de almacenamiento comprueban guardar/leer/borrar, no sobrescribir, traversal, rutas absolutas, escritura parcial y errores de lectura/borrado. Cinco pasaron; el caso de ruta absoluta falló.

## Fallos que impiden declarar la suite aprobada

### B2-F01: almacenamiento acepta ruta absoluta dentro de la raíz

Responsable del código: Lino. `storage._ruta` resuelve y comprueba confinamiento, pero no rechaza previamente una clave absoluta. Al enviar como clave `str(raiz_temporal / 'absoluta.png')`, `guardar` escribe en vez de lanzar `ErrorAlmacenamiento`. El contrato requiere clave opaca relativa y rechazar rutas absolutas del cliente.

Reproducido por `AlmacenamientoPrivadoTests.test_ruta_absoluta_rechazada_aunque_este_dentro_de_raiz`. No demuestra acceso fuera de la raíz (el traversal sí fue rechazado). Corrección propuesta para Lino: validar clave relativa antes de resolver, mantener confinamiento y aplicar la regla coherentemente en guardar/abrir/eliminar. No se cambió storage ni se relajó la aserción para obtener verde.

### B2-F02: prueba anterior contradice los permisos nuevos

`apps/catalogo/test_permissions.py`, `RolesTests.test_sincroniza_sin_otorgar_borrado_o_registro_a_administracion`, exige que Administración no tenga ningún permiso de captura. Con los modelos nuevos existen y se asignan legítimamente `anular_servicio` y `reemplazar_etiquetabandeja`; falla esa aserción amplia.

Coordinar con César para actualizarla a la política vigente: Administración no hereda Registro ni recibe borrado/edición general de fotos, pero sí esas dos acciones concretas. No quitar los permisos aprobados para satisfacer la prueba antigua. Las pruebas nuevas de Eduardo ya verifican esa distinción. Esta copia conservó la suite existente para hacer visible la incompatibilidad.

## Interfaz de Jean

Se copiaron al entorno aislado sus plantillas de captura, JS/CSS, tests de presentación y frontend desde `origin/jean-b3-interfaz-vinculada`, sin modificar sus fuentes. Resultados:

- `node --test tests/frontend/captura.test.cjs tests/frontend/vinculacion.test.cjs`: **7 pruebas aprobadas**.
- `manage.py test apps.captura.test_interfaz apps.captura.test_interfaz_vinculada --verbosity 1`: **9 aprobadas en 0.344 s**.

Se comprueban DOM/red simulados y HTML renderizado con datos de prueba. No es evidencia de cámara real, Figma completo, carga persistida, HTTPS ni S3. Jean ya publica capturas ilustrativas y documenta que no equivalen a enlaces operativos.

## Qué sigue bloqueado en B2

Lino solo publica storage.py nuevo: su urls.py conserva nueva_bandeja y confirmacion; views.py sigue con el alta del bloque inicial sin bandeja. Faltan resolver_bandeja, buscar_retorno, foto_servido, foto_retorno e imagen, validador real de JPEG/PNG, límites/orientación y compensación entre archivo y BD. Pillow no está instalado en el entorno revisado; no se instaló por iniciativa de estas pruebas.

Por tanto no se inventó `test_integration_captura.py` con endpoints falsos ni se declara validada privacidad HTTP de las fotos o idempotencia del flujo completo. Las pruebas de concurrencia deberán usar las operaciones de creación/identificador de reintento definitivas y repetirse en el motor final, distinguiendo bloqueo de SQLite de rechazo de negocio correcto.

## Bloque 3

Se preparó rama separada `eduardo-b3-pruebas-nube` desde César `7121e21`, en `.revision-b3`. Añade tres pruebas complementarias de configuración y `docs/pruebas_bloque_3.md` con veinte escenarios. Las seis pruebas de configuración de César más las tres de Eduardo pasaron: **9 en 0.051 s**, sin red AWS ni creación de infraestructura.

No están publicados modelos/servicios de SesionCaptura ni adaptador S3/endpoints de Lino B3. Falta conservación/borrado real y entorno AWS/HTTPS autorizado. La interfaz de Jean usa datos simulados. La suite normal futura tendrá stubs, pero la evidencia real seguirá necesitando bucket/prefijo autorizado y teléfono/PC. No se ha usado la cuenta administrativa local del usuario ni se almacenaron nuevas credenciales.

## Entrega y siguiente paso

Los cambios de Eduardo permanecen locales en sus ramas; no hay commit/push de esta revisión. Compartir B2-F01 con Lino y B2-F02 con César, y pedir publicación de endpoints/validador B2. Preparar PR de B3 separado, declarando dependencia de César y los resultados limitados a configuración. No cerrar B2/B3 ni marcar suite completa como aprobada mientras persistan los fallos/bloqueos. Solo César integra.
