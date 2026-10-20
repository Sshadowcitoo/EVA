# EVA: sistema de análisis visual de sobrantes alimentarios

Prototipo web para apoyar decisiones de porcionamiento y preparación en un establecimiento piloto, a partir de fotografías del plato servido y devuelto.

Proyecto de la asignatura Construcción de Software, Ingeniería de Software, UNEMI (Milagro, Ecuador). Período agosto a noviembre de 2026.

**Estado:** estructura base de Django, con la aplicación captura registrada y sus rutas conectadas al proyecto.
En la revisión del 19 de octubre de 2026 falta `manage.py` en la raíz; el modelo, formulario, vistas y pantallas están pendientes. Las pruebas de comportamiento están preparadas, pendientes de ejecución tras integrar sus dependencias.
Las instrucciones siguientes describen la ejecución prevista una vez integradas esas piezas; todavía no se ha validado el recorrido completo.

**Alcance del piloto:** un establecimiento, uno o dos platos y tres a cinco componentes. No incluye inventario, precios ni conversión a gramos.

**Informe:** ver la carpeta docs/informe/.

**Pendientes de validación:** P-01 a P-07, descritos en el apartado 6.6 y en el apartado 9.5 del informe.

## Primer avance de captura

El objetivo de este avance es abrir **Nueva bandeja**, seleccionar un plato y un tipo de porción, validar los datos y guardar un `Servicio` con UUID y fecha/hora automáticos. La confirmación debe mostrar los datos del registro guardado; recargarla no debe crear otro servicio.

Las opciones de demostración acordadas son:

| Campo | Valor interno | Etiqueta |
|---|---|---|
| Plato | `arroz_con_pollo` | Arroz con pollo |
| Plato | `lentejas` | Lentejas |
| Porción | `pequena` | Pequeña |
| Porción | `regular` | Regular |
| Porción | `grande` | Grande |

Son ejemplos de desarrollo, no un catálogo aprobado del piloto. Ambos campos son obligatorios y el servidor debe rechazar opciones inválidas.

La persistencia prevista es local, en SQLite. Fotografías, retorno, análisis visual con IA, autenticación propia, permisos por rol, catálogo editable, indicadores, recomendaciones y AWS S3 quedan pendientes. Este avance es parcial de RF-01/HU-02 y no representa la historia completa.

## Preparar el entorno en Windows

Instala Python 3.13 con el lanzador `py`, Git y un editor como VS Code. Abre PowerShell y comprueba:

```powershell
py --version
git --version
```

Para una copia nueva, ejecuta:

```powershell
git clone https://github.com/Sshadowcitoo/EVA.git
cd EVA
git switch main
git pull origin main
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si ya tienes una copia del proyecto, utiliza esa carpeta y conserva tus cambios antes de actualizarla. No vuelvas a crear el proyecto ni la aplicación con `startproject` o `startapp`.

Los comandos usan directamente el Python del entorno virtual: no es necesario activar `.venv` ni cambiar las políticas de PowerShell.

## Ejecutar en desarrollo local

**Bloqueo actual:** falta `manage.py`. Coordina su incorporación con César antes de ejecutar los comandos de esta sección y de pruebas. Para comprobar el flujo de captura también deben estar integrados el modelo y su migración, formulario, vistas, rutas y plantillas.

Una vez disponibles, ejecuta desde la raíz de EVA, donde debe estar `manage.py`:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Abre `http://127.0.0.1:8000/captura/nueva/` para registrar un servicio. Después de un envío válido se debe redirigir a `/captura/<uuid>/confirmacion/`, con el UUID del servicio creado.

El acceso de Django Admin está en `http://127.0.0.1:8000/admin/login/`; no necesitas crear un administrador para probar el formulario de captura. La portada `/` puede devolver 404 porque no tiene una vista definida. Detén el servidor con `Ctrl+C`.

SQLite se guarda localmente en `db.sqlite3`, que no debe subirse al repositorio. El avance es solo para desarrollo, sin control de acceso: no debe recibir datos reales ni publicarse como aplicación operativa.

## Pruebas y comprobaciones

Las pruebas de este avance están preparadas en `apps/captura/tests.py`, con `TestCase`, `Client` y `reverse` de Django. No se requiere pytest ni una segunda colección en `tests/`. Django debe crear automáticamente la base de pruebas; no se necesitan servicios creados a mano.

Cuando estén integradas las piezas del flujo y las pruebas, ejecuta:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test apps.captura
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

La cobertura prevista incluye:

- GET del formulario con respuesta 200 y ambos campos.
- POST válido que guarda exactamente un servicio y redirige a su confirmación.
- Datos vacíos, campos omitidos u opciones manipuladas que muestran errores sin guardar.
- UUID distintos y fecha automática para dos servicios.
- Confirmación del servicio correcto y recarga sin duplicados.
- Respuesta 404 para UUID inexistente o con formato inválido.

**Validación pendiente:** estas comprobaciones y el recorrido de captura no se han ejecutado en esta revisión. La ausencia de `manage.py` y de las funcionalidades indicadas impide el cierre final.

Para la demostración manual, abre el formulario, envíalo incompleto y comprueba los errores; después crea un registro válido, revisa su UUID y recarga la confirmación para verificar que no se duplica. Revisa también las pantallas en móvil (aproximadamente 390 px) y escritorio.

## Trabajo en equipo

Eduardo trabaja en la rama `eduardo-pruebas-documentacion` sobre `apps/captura/tests.py` y este README. La comprobación final depende del modelo de Isaac, el formulario y las vistas de Lino, y las plantillas y estilos de Jean. César revisa los Pull Requests y coordina la integración en `main`.

Cada entrega debe indicar qué se comprobó realmente y qué dependencias siguen pendientes. No subas `.venv/`, `.env`, `db.sqlite3`, cachés ni credenciales. Los cambios de configuración o dependencias deben coordinarse con César.
