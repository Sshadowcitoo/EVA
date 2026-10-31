# EVA: sistema de análisis visual de sobrantes alimentarios

Proyecto de Construcción de Software, Ingeniería de Software, UNEMI.

## Estado integrado al 31 de octubre de 2026

Integra las entregas de los bloques 2 y 3 de César, Isaac, Lino, Jean y Eduardo.
El alcance comprobado y los pendientes están en
[la revisión de integración](docs/integracion_31_octubre_2026.md).

Disponible sobre almacenamiento local privado:

- Login, roles independientes y catálogo editable del bloque inicial.
- Bandejas, etiquetas revocables, asignaciones y fotografías por etapa.
- Búsqueda por número o etiqueta, alta de servicio y captura servido/retorno.
- Vista previa y lector QR local, con alternativa manual.
- Retorno por otro operador de Registro, autoría por foto y liberación de bandeja.
- Lectura privada de imágenes y preservación de la confirmación histórica del creador.
- Re-codificación JPEG/PNG sin EXIF, límites compartidos y compensación de archivos.

Del bloque 3 se integran configuración, sesiones temporales de captura, servicios
de dominio, metadatos y plantillas/JavaScript. **Todavía faltan el adaptador S3 y
los endpoints de vinculación**: no se acredita captura real PC→teléfono→S3.
Seleccionar S3 sin su adaptador rechaza la carga; no escribe silenciosamente en local.

Cocina ve su pantalla pendiente: no dispone aún de análisis ni revisión de fotos.
Administración no hereda Registro ni recibe borrado genérico: conserva únicamente
las acciones aprobadas de anulación y reemplazo de etiqueta, además del catálogo.
Sus pantallas específicas de esas acciones todavía están pendientes.

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

Comprobación integrada del 31 de octubre de 2026:

- `check`: sin incidencias.
- **142 pruebas Django aprobadas**, sobre base temporal y archivos temporales.
- **7 pruebas JavaScript aprobadas**: `node --test tests/frontend/*.test.cjs`.
- `makemigrations --check --dry-run`: sin cambios.
- `git diff --check`: correcto.

La suite incluye un recorrido HTTP completo servido/retorno con dos operadores,
roles/CSRF, lectura privada, rechazo de duplicados y compensación ante fallos.
No mide precisión de IA ni acredita S3, cámara física o concurrencia simultánea real.
Las revisiones del 28 y 29 de octubre se conservan como evidencia histórica;
sus fallos y pendientes no sustituyen este estado integrado.

## Pendiente del proyecto

- Impresión/ensayo de etiquetas físicas y endpoints de vinculación entre dispositivos.
- Versionar protocolo/checklist y probar montaje/cámara física; el guardado local servido/retorno ya está integrado.
- Microservicio visual, conjunto de imágenes anotadas y evaluación independiente.
- Revisión de Cocina, histórico analítico y percepción del comensal.
- Recomendaciones, decisiones y seguimiento de pruebas controladas.
- Adaptador S3, conservación de imágenes/máscaras y publicación versionada del despliegue.
- Contexto/horario y demás decisiones de datos aún no ratificadas.

La configuración predeterminada del repositorio usa SQLite y ajustes de desarrollo.
Integrar Git no actualiza automáticamente el servidor público. Los ajustes operativos
que existen en ese servidor requieren su publicación y revisión separadas. S3 es
almacenamiento de archivos, no el servidor Django ni la IA.

## Trabajo en equipo

Cada integrante entrega en su rama mediante Pull Request. César revisa e integra;
los compañeros no hacen merge. El bloque inicial ya se integró en `main`.
Los bloques nuevos se entregan en ramas nuevas desde esa base.
Las imágenes quedan a cargo de César.

No subir `.venv/`, `.env`, `db.sqlite3`, cachés, imágenes del piloto ni credenciales.
Las migraciones sí se versionan. Los recursos gráficos propios de la interfaz
pueden incluirse explícitamente; no confundirlos con los datos fotográficos del piloto.
