# EVA: sistema de análisis visual de sobrantes alimentarios

Proyecto de la asignatura Construcción de Software, Ingeniería de Software, UNEMI.

EVA busca apoyar decisiones sobre porciones y preparación mediante fotografías del plato servido y devuelto, revisión humana, indicadores y recomendaciones.

## Estado actual

Primer avance funcional del módulo de captura, integrado en `main` después de reunir y probar las entregas del equipo en `integracion-captura`.

El avance permite:

- Seleccionar un plato y un tipo de porción de demostración.
- Validar los campos antes de guardar.
- Crear un servicio con identificador UUID único y fecha automática.
- Guardar los datos en una base SQLite local.
- Consultar la confirmación del registro.
- Recargar la confirmación sin crear otro servicio.

Las pantallas toman como referencia el diseño de EVA en Figma y se adaptan a móvil y escritorio.

Este avance cubre una parte de RF-01/HU-02; no representa la historia completa ni el sistema terminado.

## Alcance del piloto

El proyecto contempla un establecimiento, uno o dos platos y entre tres y cinco componentes distinguibles.

No incluye inventario, precios ni conversión directa de imágenes a gramos.

## Opciones de demostración

| Campo | Valor interno | Etiqueta |
|---|---|---|
| Plato | `arroz_con_pollo` | Arroz con pollo |
| Plato | `lentejas` | Lentejas |
| Tipo de porción | `pequena` | Pequeña |
| Tipo de porción | `regular` | Regular |
| Tipo de porción | `grande` | Grande |

Estas opciones son ejemplos de desarrollo, no un catálogo aprobado para el piloto.

## Requisitos para desarrollo

- Python 3.13.
- Git.
- Un editor de código.
- PowerShell para los comandos de esta guía.

## Descargar y preparar el proyecto

Descarga la versión integrada:

```powershell
git clone https://github.com/Sshadowcitoo/EVA.git
cd EVA
git switch main
```

Crea el entorno virtual e instala las dependencias:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Los comandos utilizan directamente el Python del entorno virtual. No es necesario activarlo ni modificar las políticas de PowerShell.

Si ya tienes una copia del repositorio, conserva tus cambios antes de actualizarla:

```powershell
git switch main
git pull origin main
```

No vuelvas a crear el proyecto ni la aplicación `captura`.

## Ejecutar el proyecto

Desde la raíz de EVA, donde está `manage.py`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Abre:

- Formulario: http://127.0.0.1:8000/captura/nueva/
- Administrador de Django: http://127.0.0.1:8000/admin/login/

La dirección `/` puede devolver 404 porque todavía no tiene una página de inicio.

Para detener el servidor, pulsa `Ctrl+C`.

## Recorrido de demostración

1. Abre «Nueva bandeja».
2. Comprueba que no permite enviar los campos vacíos.
3. Selecciona un plato y una porción.
4. Pulsa «Guardar registro».
5. Revisa el identificador, plato, porción y fecha en la confirmación.
6. Recarga la confirmación y comprueba que mantiene el mismo identificador.

La sección de fotografía y las etapas posteriores se muestran como pendientes. Todavía no realizan captura ni análisis.

## Administrador local

No necesitas entrar al administrador para utilizar el formulario de captura.

Si necesitas una cuenta administrativa local:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Cada integrante crea su propia cuenta en su base local. Las cuentas de demostración de Figma no se crean automáticamente en Django.

La aplicación `captura` no aparece automáticamente en el administrador. Para gestionar sus registros allí, es necesario registrar el modelo `Servicio` en `apps/captura/admin.py`.

## Pruebas

Ejecuta:

```powershell
.\.venv\Scripts\python.exe manage.py test apps.captura
```

Las siete pruebas cubren:

- UUID distintos y fecha automática.
- Presentación del formulario vacío.
- Guardado válido y redirección a confirmación.
- Rechazo de campos omitidos y opciones inválidas.
- Confirmación del servicio correcto y recarga sin duplicados.
- Respuesta 404 para un UUID inexistente.
- Respuesta 404 para un UUID mal formado.

Validación realizada antes de integrar en `main`:

- `manage.py check`: sin errores.
- Migración inicial de `captura`: aplicada correctamente.
- Siete pruebas automatizadas: aprobadas, repetidas después de los ajustes visuales.
- `makemigrations --check --dry-run`: sin cambios detectados antes de los ajustes visuales.
- Creación de un registro y consulta de su confirmación: comprobadas en el navegador antes de los últimos ajustes visuales.

## Organización de este avance

| Ubicación | Responsabilidad |
|---|---|
| `config/` | Configuración y rutas principales de Django |
| `apps/captura/models.py` | Modelo `Servicio` |
| `apps/captura/migrations/` | Cambios de estructura de la base de datos |
| `apps/captura/forms.py` | Formulario y validación |
| `apps/captura/views.py` | Guardado y consulta de confirmación |
| `apps/captura/urls.py` | Rutas del módulo |
| `apps/captura/tests.py` | Pruebas automatizadas |
| `templates/` | Pantallas de EVA |
| `static/css/eva.css` | Estilos de la interfaz |
| `docs/informe/` | Documentación del proyecto |

Las carpetas restantes conservan la estructura prevista para siguientes etapas.

## Funciones pendientes

- Catálogo editable.
- Fotografía inicial y fotografía del retorno.
- Recuperación del servicio por identificador.
- Autenticación propia y permisos por rol.
- Análisis visual con IA y revisión de Cocina.
- Histórico e indicadores.
- Recomendaciones y decisiones de Administración.
- Integración con AWS S3.
- Validaciones operativas y técnicas del piloto.

## Trabajo en equipo

- César: base del proyecto e integración.
- Isaac: modelo `Servicio` y migración inicial.
- Lino: formulario, vistas y rutas.
- Eduardo: pruebas y documentación.
- Jean: pantallas.

Cada integrante trabaja en su rama y entrega sus cambios mediante un Pull Request. Para este avance, las partes se reunieron en `integracion-captura`, se comprobaron conjuntamente y después se incorporaron a `main`.

## Bloque inicial: preparación de catálogo, sesiones y permisos

El primer avance descrito arriba sigue siendo la base de esta rama. El bloque nuevo no está integrado aquí: las pruebas nuevas requieren modelos/migraciones de Isaac y los helpers/configuración de César. El [plan y evidencias](docs/pruebas_bloque_inicial.md) distingue comprobaciones aisladas de la validación final pendiente.

Catálogo propuesto: encebollado (yuca/pescado), seco de pollo (arroz/pollo/maduro) y arroz con menestra y carne (arroz/menestra/carne/ensalada); ocho componentes compartidos y porción estándar. Los platos anteriores se conservan como históricos sin remapearlos por semejanza.

Después de integrar las dependencias, desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py cargar_catalogo_demo
.\.venv\Scripts\python.exe manage.py configurar_roles
.\.venv\Scripts\python.exe manage.py test apps.catalogo apps.captura
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Estos comandos de catálogo/roles existen en las entregas de Isaac/César, no en la base anterior por sí sola. La carga demo normal conserva ediciones; `--restablecer` modifica explícitamente nombres, estados y relaciones de demostración. Revisar sus efectos antes de usarlo sobre un catálogo personalizado. No borrar bases ni reescribir migraciones compartidas.

`configurar_roles` crea/sincroniza grupos `Registro`, `Cocina` y `Administración`; no crea usuarios ni asigna membresías. Ejecutarlo después de migrar los modelos; reporta permisos aún inexistentes. Conserva membresías y permisos ajenos a captura/catálogo, pero retira permisos extra de esas dos aplicaciones en los grupos gestionados.

Para usuarios locales, usar la administración autorizada de Django: crear un superusuario con `manage.py createsuperuser`, entrar a `/admin/` y crear usuarios de prueba asignando expresamente sus grupos. Introducir contraseñas de forma interactiva; nunca guardarlas en Git. Los usuarios de Registro/Cocina/Administración no necesitan ser staff. El superusuario es una cuenta técnica extraordinaria y no sirve para demostrar restricciones por rol.

Los grupos no se heredan: Administración gestiona catálogo, Registro crea servicios y Cocina no administra catálogo. `is_staff` no concede permisos del producto. El helper permite superusuarios activos y deniega usuarios inactivos. La política de consulta de servicios concretos sigue pendiente de ratificación.

Contrato de sesión publicado: `/cuentas/login/`, destino de Registro `captura:nueva_bandeja` y logout de vuelta al login. Las rutas y pantallas reales de sesiones aún dependen de Lino; no afirmar que están disponibles. Falta acordar el destino de los otros roles. El cierre de sesión deberá usar POST con CSRF.

Las pruebas nuevas incluyen migración histórica, atomicidad e instantáneas, y pruebas aisladas de autenticación estándar de Django y helpers por rol. Las rutas de prueba están definidas solo en el módulo de tests: no validan las vistas reales pendientes. Consultar el documento de evidencias para resultados y alcance. Fotografías, QR, IA y S3 no se completan en este bloque.

## Archivos locales y revisión aislada

No subir al repositorio:

- `.venv/`
- `.env`
- `db.sqlite3`
- Cachés de Python.
- Credenciales o archivos personales.

Las migraciones sí se incluyen en Git.

Esta versión está preparada para desarrollo local con datos de demostración. La configuración de despliegue y el control de acceso del producto siguen pendientes.
