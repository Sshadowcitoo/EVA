# EVA: sistema de análisis visual de sobrantes alimentarios

Proyecto de Construcción de Software, Ingeniería de Software, UNEMI.

## Estado de esta rama

Integra los aportes del bloque inicial de Isaac (modelos), César (roles y configuración),
Lino (funciones), Jean (pantallas) y Eduardo (pruebas), y corrige sus puntos de conexión.
El bloque inicial quedó integrado en `main` mediante el PR #13, commit `8f685bf`.
No equivale al sistema completo. Esta rama prepara su cierre documental y el plan
de pruebas del bloque 2; todavía no implementa fotografías, bandejas ni QR.

Funciones disponibles:

- Login y logout por POST, con destino por rol.
- Roles independientes Registro, Cocina y Administración; `is_staff` no concede un rol.
- Catálogo editable de platos, componentes y porciones; activar/desactivar sin borrar.
- Registro con opciones activas, usuario creador y composición histórica.
- Confirmación accesible solo al usuario de Registro que creó el servicio.
- Pantallas conectadas al servidor, tomando como base los componentes de Figma.

Cocina puede iniciar sesión y ve una página de funciones pendientes. No dispone aún
de análisis ni revisión de fotografías. Administración no hereda Registro: asignar
ambos grupos expresamente si una persona debe cumplir ambas funciones.

## Catálogo inicial del escenario ficticio

| Plato | Componentes |
| --- | --- |
| Encebollado | Yuca, pescado |
| Seco de pollo | Arroz, pollo, maduro |
| Arroz con menestra y carne | Arroz, menestra, carne, ensalada |

Tres platos, ocho componentes distintos y una porción `estandar`, sin gramos.
El arroz se comparte entre platos. El caldo no se mide. Las imágenes, su evaluación
y la validación en un restaurante real siguen pendientes.

Los servicios anteriores conservan UUID, fecha y etiquetas; no se remapean al nuevo
catálogo. Los registros históricos sin creador no se muestran como confirmaciones
de un usuario cualquiera. Editar el catálogo no reescribe las instantáneas existentes.

## Preparación

Requisitos: Python 3.13, Git y las dependencias de `requirements.txt`.
Si ya existe una copia, conservar los cambios antes de actualizar y cambiar de rama.
No ejecutar otra vez `startproject` ni `startapp captura`.

```powershell
git clone https://github.com/Sshadowcitoo/EVA.git
cd EVA
git switch main
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

En un entorno ya preparado no es necesario recrear `.venv` ni instalar de nuevo.
No se necesita activar el entorno ni modificar políticas globales de PowerShell.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py cargar_catalogo_demo
.\.venv\Scripts\python.exe manage.py configurar_roles
.\.venv\Scripts\python.exe manage.py check
```

La carga demo normal es repetible y conserva las modificaciones del usuario.
`--restablecer` es una acción explícita que puede sobrescribir nombres y estados
del catálogo demo; no usarla sobre datos útiles sin revisar su efecto.

`configurar_roles` sincroniza los permisos de captura/catálogo en los tres grupos;
no crea usuarios ni asigna membresías. Conserva permisos de otras aplicaciones.
Puede avisar de permisos de Contexto pendientes: ese modelo no tiene todavía
contrato y no se crea en este bloque.

## Cuentas locales y ejecución

Crear la cuenta técnica local solo si es necesaria para administrar usuarios:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

En `/admin/`, crear cuentas operativas y asignarles los grupos correspondientes.
No dar `is_staff` a los operadores por necesidad del producto ni guardar contraseñas
en Git. El superusuario conserva acceso técnico extraordinario; no usarlo para
comprobar restricciones entre roles. No hay contraseñas demo predefinidas.

- Login: <http://127.0.0.1:8000/cuentas/login/>
- Registro: <http://127.0.0.1:8000/captura/nueva/>
- Administración: <http://127.0.0.1:8000/catalogo/platos/>
- Cocina: <http://127.0.0.1:8000/cuentas/cocina/>

El login prioriza Registro, luego Administración y luego Cocina cuando se asignan
varios grupos; el menú permite cambiar entre sus funciones autorizadas. Una cuenta
sin rol no inicia sesión en EVA. La raíz `/` aún puede responder 404.

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test apps.catalogo apps.captura
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Comprobación de la integración el 27 de octubre de 2026, con Django 5.2.17:

- `check`: sin problemas.
- 56 pruebas aprobadas en una base temporal, incluidas migraciones históricas.
- `makemigrations --check --dry-run`: sin cambios detectados.

Revisión repetida el 28 de octubre sobre `8f685bf`, en un worktree aislado:
`check` sin problemas, **56 pruebas aprobadas en 29.464 s** y
`makemigrations --check --dry-run` sin cambios. No se alteró la base local del usuario.
La aceptación visual móvil/escritorio sigue pendiente; véase el
[registro de cierre](docs/cierre_bloque_inicial_28_octubre.md).

El siguiente trabajo de Eduardo se organiza en el
[plan de pruebas del bloque 2](docs/pruebas_bloque_2.md). Los contratos de César
para bloques 2 y 3 están publicados en ramas separadas; no deben confundirse con
funciones integradas en `main` ni con uso real de AWS.

La rama de Eduardo añade `apps/captura/test_permisos_bloque_2.py`, que requiere
la matriz nueva de César (`d375ba2`). Sus tres casos se aprobaron en copia aislada
con esa dependencia. Simulan permisos futuros solo en la BD temporal: no acreditan
modelos de bandejas, fotos ni endpoints que todavía no estén implementados.
No ejecutar esta rama como una entrega integrada antes de incorporar la base de
César; el caso de permisos nuevos detectará correctamente su ausencia.

Actualización del 29 de octubre: se añadieron `test_bandejas.py` y
`test_fotografias.py` contra servicios Isaac y storage Lino, en copia aislada.
La suite combinada ejecutó 96 pruebas: **94 aprobadas y 2 fallos**. No es un
bloque terminado. Consultar [fallos y evidencia](docs/revision_bloques_29_octubre.md)
para las dependencias, reproducción y funciones que todavía faltan.

La suite incluye modelos y carga demo de Isaac, helpers de permisos de César,
pruebas complementarias de Eduardo y recorridos reales de integración: sesiones,
redirecciones, acceso por rol, CSRF, catálogo, captura y privacidad de confirmaciones.
Las siete pruebas del avance se adaptaron al contrato de catálogo y sesión.
La integración final de las pantallas con móvil/escritorio debe revisarse también
visualmente; las pruebas HTTP no certifican una coincidencia exacta con Figma.

## Pendiente del proyecto

- Identificación física de bandejas y QR; vinculación de captura entre dispositivos.
- Fotografías inicial/retorno, protocolo y controles de calidad.
- Microservicio visual, conjunto de imágenes anotadas y evaluación independiente.
- Revisión de Cocina, histórico analítico y percepción del comensal.
- Recomendaciones, decisiones y seguimiento de pruebas controladas.
- AWS S3 privado, política de conservación de imágenes/máscaras y despliegue.
- Contexto/horario y demás decisiones de datos aún no ratificadas.

La configuración actual usa SQLite y ajustes de desarrollo; no es un despliegue
operativo. S3 será almacenamiento de archivos, no el servidor Django ni la IA.

## Trabajo en equipo

Cada integrante entrega en su rama mediante Pull Request. César revisa e integra;
los compañeros no hacen merge. El bloque inicial ya se integró en `main`.
Los bloques nuevos se entregan en ramas nuevas desde esa base.
Las imágenes quedan a cargo de César.

No subir `.venv/`, `.env`, `db.sqlite3`, cachés, imágenes del piloto ni credenciales.
Las migraciones sí se versionan. Los recursos gráficos propios de la interfaz
pueden incluirse explícitamente; no confundirlos con los datos fotográficos del piloto.
