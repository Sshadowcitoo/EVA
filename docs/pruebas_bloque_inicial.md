# Plan de pruebas del bloque inicial

Responsable: Eduardo. Rama: `eduardo-pruebas-bloque-inicial`.
Fecha de preparación: 26 de octubre de 2026.

## Alcance y estado

Plan basado en `EVA_Guia_equipo_bloque_inicial.pdf` (25 de octubre, especialmente páginas 2, 3 y 7) y `EVA_Plan_y_decisiones_25_octubre_2026.pdf`. Ambos documentos contienen propuestas; este plan no sustituye el contrato definitivo del equipo ni acredita implementación.

Se comprobarán sesiones, permisos, catálogo, alta de servicios y conservación histórica. Fotografías, bandejas, QR, IA, S3, indicadores y recomendaciones quedan fuera de la ejecución de este bloque.

Base de partida: `a0c192c`, obtenida de `origin/main`. Eduardo ejecutó y compartió los siguientes resultados antes de modificar el bloque:

| Comando | Resultado observado |
|---|---|
| `manage.py check` | Sin problemas detectados |
| `manage.py test apps.captura` | 7 pruebas aprobadas; base temporal creada y eliminada |

Estos resultados corresponden al registro anterior. No certifican las funciones nuevas. Los casos siguientes están **planificados y no ejecutados**.

## Dependencias y decisiones pendientes

Antes de convertir los casos en pruebas de integración, César debe registrar el contrato de modelos, rutas, permisos y pantallas. Isaac y César deben cerrar la migración y la estrategia de instantáneas. Nombres como `cuentas:login` son propuestas de la guía, no rutas confirmadas.

| Decisión | Responsable de coordinación | Efecto sobre las pruebas |
|---|---|---|
| Modelos, campos, restricciones y comandos definitivos | César e Isaac | Preparación de datos y comprobación de integridad |
| Política de consulta de servicios y confirmaciones | César | Usuarios autorizados, alcance de consulta y respuesta de denegación |
| Rutas, métodos HTTP y permisos concretos | César y Lino | Peticiones GET/POST, redirecciones y denegaciones |
| Edición de composición e instantáneas históricas | César e Isaac | Verificación de que servicios previos no cambian |
| Contexto/horario requerido y porción estándar | César e Isaac | Datos obligatorios del alta |
| Comportamiento ante códigos duplicados o inactivos en la carga demo | César e Isaac | Repetibilidad sin sobrescribir cambios del usuario |
| Pantallas y variantes disponibles en Figma | César y Jean | Evidencias visuales y estados faltantes |

La rama publicada de Isaac no equivale a integración en la base compartida. No se incorporarán ramas ajenas por iniciativa de este plan.

## Matriz propuesta de permisos

Los permisos se verifican en el servidor. Ocultar botones no es suficiente. Los grupos son independientes; Administración no hereda Registro ni Cocina. `is_staff` por sí solo no concede permisos del producto.

La matriz describe usuarios con un único rol. Si tienen varios grupos, se comprobará la combinación explícitamente según el contrato.

| Operación | Anónimo | Registro | Cocina | Administración |
|---|---|---|---|---|
| Iniciar sesión | Disponible | Disponible sin sesión previa | Disponible sin sesión previa | Disponible sin sesión previa |
| Cerrar sesión | Según contrato, sin efectos indebidos | POST con CSRF | POST con CSRF | POST con CSRF |
| Crear servicio | Redirigir a login | Permitido | Denegado | Denegado salvo grupo Registro adicional |
| Consultar opciones activas necesarias para registrar | Requiere sesión | Permitido | Alcance por definir | Consulta dentro de gestión autorizada; alta de servicios no implícita |
| Listar y administrar catálogo | Redirigir a login | Denegado | Denegado | Permitido |
| Crear, editar o desactivar catálogo | Redirigir a login | Denegado | Denegado | Permitido |
| Consultar un servicio o su confirmación | Redirigir a login | Según política pendiente | Según política pendiente | Según política pendiente |

Para operaciones protegidas, comprobar GET y POST cuando correspondan. Un usuario autenticado sin permiso debe recibir denegación; el código exacto se fijará en el contrato. Ninguna petición GET debe crear, modificar o desactivar datos. Para UUID inválidos/inexistentes, comprobar el 404 con un usuario autorizado, sin confundirlo con una redirección por falta de sesión.

## Casos planificados

Cada caso debe comprobar respuesta, errores visibles cuando corresponda y efectos en la base. Los datos se crean en la base temporal de Django, sin cuentas ni servicios manuales y sin contraseñas reales en Git.

| ID | Escenario | Resultado esperado |
|---|---|---|
| SES-01 | Credenciales válidas | Sesión iniciada y destino conforme al contrato |
| SES-02 | Credenciales incorrectas | Error y sesión no autenticada |
| SES-03 | Logout por POST con CSRF válido | Sesión cerrada; recurso protegido vuelve a requerir login |
| SES-04 | Logout por GET o POST sin CSRF | No cerrar sesión mediante GET; rechazar POST sin token |
| PER-01 | Anónimo solicita GET/POST protegidos | Login y ninguna modificación de datos |
| PER-02 | Registro o Cocina intenta administrar catálogo por GET/POST | Denegación en servidor, sin modificaciones |
| PER-03 | Administración sin Registro intenta crear servicio | Denegación, sin servicio nuevo |
| PER-04 | Usuario con grupos Administración y Registro | Acciones de ambos grupos según política, sin privilegios adicionales |
| PER-05 | Usuario sin grupo o solo con is_staff | Sin autorización de negocio implícita |
| PER-06 | Usuario conoce UUID fuera de su ámbito | No puede recuperar servicio ni confirmación; política pendiente |
| CAT-01 | Administración crea plato, componente y porción válidos | Datos persistidos con códigos y estado acordados |
| CAT-02 | Campos obligatorios, códigos duplicados o referencias inválidas | Errores y ninguna escritura parcial |
| CAT-03 | Administración edita o desactiva elementos | Cambio permitido; historial anterior conservado |
| CAT-04 | GET sobre operaciones de cambio | Ninguna creación, edición o desactivación |
| CAT-05 | Carga demo en base preparada para el bloque | Tres platos y ocho tipos de componentes; arroz compartido |
| CAT-06 | Relación plato-componente duplicada | Restricción rechaza el duplicado |
| CAT-07 | Repetir carga demo tras cambios de usuario | Sin duplicados ni borrado/sobrescritura de cambios sin acción explícita |
| CAP-01 | Registro abre nueva bandeja | Solo opciones activas elegibles |
| CAP-02 | Registro envía alta válida | Exactamente un servicio, usuario creador, referencias e instantáneas correctas; redirección |
| CAP-03 | Campos vacíos, referencias inexistentes o valores manipulados | Errores y ningún servicio ni instantánea parcial |
| CAP-04 | Elemento desactivado después de abrir formulario | POST rechazado aunque el navegador conserve la opción |
| CAP-05 | Dos servicios válidos | UUID distintos y fechas automáticas |
| CAP-06 | Consultar y recargar confirmación autorizada | Servicio correcto, sin duplicación |
| CAP-07 | UUID inexistente o mal formado con sesión autorizada | 404, sin crear filas |
| HIS-01 | Editar nombre/composición después del alta | Instantánea anterior conserva significado y composición originales |
| HIS-02 | Desactivar elemento referenciado | Servicio anterior sigue legible y no se elimina |
| MIG-01 | Migraciones en base nueva | Esquema y restricciones reproducibles |
| MIG-02 | Migrar copia de prueba con servicios antiguos | UUID, fechas y etiquetas anteriores conservados; sin remapear arroz_con_pollo/lentejas por semejanza |
| MIG-03 | Fallo durante creación de instantáneas | Alta atómica: sin servicio o composición incompletos |

En CAT-05 se comprobará: encebollado (yuca/pescado), seco de pollo (arroz/pollo/maduro) y arroz con menestra y carne (arroz/menestra/carne/ensalada). El caldo no se mide. Las referencias exactas y la porción estándar dependen del contrato ratificado.

Para pruebas de CSRF usar `Client(enforce_csrf_checks=True)`: el cliente de pruebas normal no aplica estas comprobaciones. No aceptar una denegación por CSRF como evidencia de denegación por rol; probar los permisos con una petición válida en los demás aspectos.

## Organización de las pruebas

### Preparación contra la entrega de Isaac

Se revisó en modo lectura `origin/isaac-catalogo-datos`, commit `80f90d6`, sin incorporarlo a esta rama. Publica `Plato`, `Componente`, `PlatoComponente`, `TipoPorcion`, `Servicio.registrar`, `ServicioComponente`, migraciones y `cargar_catalogo_demo`. Isaac ya incluye pruebas en `apps/catalogo/test_models.py`: se conservarán y no se duplicará esa cobertura.

Se prepararon cinco pruebas complementarias en `apps/catalogo/tests.py`: usuario creador, rollback de un alta con escritura parcial de composición, etiqueta histórica de porción, relación desactivada conservada solo en la instantánea anterior y carga repetida que preserva datos personalizados. **No ejecutadas**: requieren los archivos de Isaac y la aplicación registrada. Los imports fallarán en la base anterior si se intenta ejecutar esta suite antes de integrar esas dependencias; no se oculta ese bloqueo mediante pruebas omitidas.

Estas pruebas cubren el servicio de dominio y el comando, no demuestran permisos HTTP, sesiones, migración de datos antiguos ni cumplimiento visual. Esas comprobaciones siguen pendientes. No se modificaron todavía las siete pruebas anteriores de captura.

- `apps/catalogo/tests.py`: catálogo, carga inicial, sesiones y permisos asociados a sus rutas, conforme a la estructura acordada.
- `apps/captura/tests.py`: alta, confirmación, permisos de captura e historial. Adaptar las siete pruebas previas cuando cambie el contrato, conservando sus garantías.
- Pruebas de migración: coordinar su ubicación y preparación con Isaac y César. Nunca experimentar sobre la única base local o compartida con datos útiles.

Usar `TestCase`, `Client` y `reverse` de Django. No instalar pytest ni crear otra colección duplicada. Si las pruebas de migraciones requieren herramientas o estructura distintas, coordinar su elección antes de implementarlas.

## Verificación y evidencias

Tras integrar las dependencias, ejecutar desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test apps.catalogo apps.captura
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

No ejecutar aún la suite nueva como si estuviera disponible: `apps.catalogo` y sus contratos deben estar integrados y registrados primero. `makemigrations --check --dry-run` comprueba migraciones faltantes, no prueba por sí solo una migración con datos antiguos.

Registrar por ejecución: fecha, commit, comando, resultado real y fallos o bloqueos concretos. Las capturas del terminal complementan la salida; no sustituyen pruebas no ejecutadas.

Evidencia manual pendiente: login/logout; Administración crea, edita y desactiva catálogo; Registro crea servicio y consulta confirmación; Registro/Cocina reciben denegación al administrar; un servicio anterior conserva sus datos. Revisar móvil de aproximadamente 390 px y escritorio, comparando con los marcos Figma acordados. No guardar contraseñas ni datos personales en capturas.

El README deberá explicar migraciones, comandos definitivos de catálogo y roles, creación/asignación de usuarios sin contraseñas en Git, rutas, pruebas y límites. No documentar un comando propuesto como si ya existiera.

## Criterio de entrega

Otro integrante puede reproducir el bloque siguiendo el README; las pruebas y evidencias cubren las funciones realmente entregadas. Declarar pendientes y dependencias en el Pull Request. No cerrar historias completas que todavía requieran fotografías, QR o análisis.

Cada integrante sube su rama y abre su Pull Request. César revisa e integra: Eduardo no realiza merge ni fuerza pushes. Las imágenes quedan a cargo de César según su mensaje al equipo.
