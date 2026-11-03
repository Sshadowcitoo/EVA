# EVA: sistema de análisis visual de sobrantes alimentarios

Proyecto de Construcción de Software, Ingeniería de Software, UNEMI.


## Preparación de Eduardo: pruebas del bloque 4

Esta rama, `eduardo-b4-pruebas`, parte de main `1a22306` y añade pruebas numéricas
complementarias y el [plan/evidencias del bloque 4](docs/pruebas_bloque_4.md).
No incorpora por su cuenta modelos de Isaac ni configuración de César.

Se validaron en una copia aislada la base de César `1e416a5`, el dominio de Isaac
`50ff172` y `apps/analisis/test_calculos.py`: **46 pruebas aprobadas**, seis de
Eduardo y cuarenta de Isaac. El entorno utiliza las dependencias declaradas,
incluido qrcode 8.2. Los umbrales numéricos de fixtures no son criterios aprobados
para el modelo real.

Ampliación del 2 de noviembre: `apps/analisis/test_jobs.py` añade siete casos de
persistencia, reintentos y límites temporales. La ejecución conjunta pasó
**53 pruebas en 2.512 s**: 40 de Isaac y 13 de Eduardo. Este módulo comprueba
servicios de dominio, no el worker HTTP pendiente. El selector de retención no
acredita eliminación física de máscaras.

La ejecución posterior de toda `apps.analisis` disponible en la copia aislada
pasó **59 pruebas en 6.350 s**, agregando configuración e interfaz de César.

Cuando esas dependencias estén disponibles en la copia utilizada, ejecutar:

```powershell
.\.venv\Scripts\python.exe manage.py test apps.analisis.test_calculos apps.analisis.test_jobs apps.analisis.test_dominio_analisis --verbosity 1
```

En `.revision-b4-validacion` se usa `..\.venv\Scripts\python.exe` porque comparte
el entorno de la carpeta EVA. No ejecutar el comando sobre esta rama sin las
dependencias: main de partida aún no contiene la aplicación de análisis operativa.
No se sustituyen rutas ni se omiten checks para aparentar una integración completa.

Estas pruebas verifican cálculos y dominio con datos controlados. No certifican
inferencia real, precisión, cliente del microservicio, worker ni permisos HTTP del
bloque 4. Dichas comprobaciones y la revisión de Cocina del bloque 5 siguen según
las dependencias del equipo. No instalar YOLO/OpenCV ni cambiar infraestructura
para ejecutar estas pruebas de cálculo.

## Preparación de Eduardo: revisión de Cocina (bloque 5)

Esta rama `eduardo-b5-pruebas-revision` añade el
[plan y evidencias del bloque 5](docs/pruebas_bloque_5.md) y pruebas de la regla
de elegibilidad publicada por César `2479f9e`. Requiere esa dependencia; el main
de partida `1a22306` todavía no tiene la regla ni la revisión de Cocina operativa.

No confundir validación de una función pura con decisiones humanas persistidas.
Faltan el modelo/servicio versionado de Isaac y los endpoints/evidencia de Lino.
No se amplía el gateway de Registro ni se incorpora una app Cocina paralela.
Los datos simulados nunca se convierten en evidencia real por pulsar Confirmar.

Validación aislada el 2 de noviembre: **9 pruebas aprobadas en 0.018 s**,
seis complementarias de Eduardo y tres de César. No acredita el bloque completo.

En una copia que incluya la base de César y este archivo de pruebas:

```powershell
.\.venv\Scripts\python.exe manage.py test apps.analisis.test_elegibilidad apps.analisis.test_elegibilidad_complementaria --verbosity 1
```

En worktrees de revisión se usa `..\.venv\Scripts\python.exe`. Solo César integra
los PR; esta preparación no instala IA ni modifica infraestructura.


## Estado integrado: actualización del 1 de noviembre de 2026

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

El adaptador S3 ya está conectado al guardado y lectura de fotografías, mediado por
Django. Conserva el backend y las versiones de cada archivo; las fotos locales
anteriores siguen accesibles. Un fallo S3 no cae a disco ni confirma el guardado.
Faltan los endpoints de vinculación PC–celular: no se acredita ese recorrido completo.
La configuración de desarrollo continúa local hasta activar el entorno autorizado.

Cocina ve su pantalla pendiente: no dispone aún de análisis ni revisión de fotos.
Administración no hereda Registro ni recibe borrado genérico: conserva únicamente
las acciones aprobadas de anulación y reemplazo de etiqueta, además del catálogo.
Las pantallas de anulación y reemplazo están disponibles en Bandejas y servicios,
con motivo/confirmación, auditoría y descarga del QR vigente.

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

Comprobación actualizada el 1 de noviembre de 2026:

- `check`: sin incidencias.
- **156 pruebas Django aprobadas**, sobre base temporal/archivos temporales y S3 simulado.
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
- Conservación de imágenes/máscaras y publicación versionada del despliegue.
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

## Administración y S3

## Integración de análisis (bloque 4)

Ver [cliente, worker y evidencia privada](docs/entrega_lino_bloque_4.md).
La cola se ejecuta fuera de la web; no hay resultados ficticios si el motor está
sin configurar. Instalar el código no activa el worker ni valida la IA.

## Revisión de Cocina (bloque 5)

Ver [revisión conectada y comprobación de evidencia](docs/entrega_lino_bloque_5.md).
Tras migrar, ejecutar `python manage.py configurar_roles`. El ensayo aislado
`python ops/analisis/smoke_integracion.py` usa un motor HTTP SIMULADO, base y archivos
temporales; no toca producción ni acredita segmentación REAL.

### Captura y almacenamiento existentes

Ver [operación y permisos](docs/administracion_y_s3.md) para anulación, etiquetas,
lectura mixta local/S3 y prueba explícita del bucket mediante el rol del servidor.
