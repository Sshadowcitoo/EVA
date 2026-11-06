# EVA: sistema de análisis visual de sobrantes alimentarios

Proyecto de Construcción de Software, Ingeniería de Software, UNEMI.

## Entrega y QA — 6 de noviembre de 2026

La demo de AWS incluye las correcciones de captura e integridad de los PR #62 y
#63. Consulta la [documentación del software](docs/documentacion_software.md), el
[manual de usuario](docs/manual_usuario.md), las
[características técnicas](docs/caracteristicas_tecnicas.md) y el
[cierre de QA](docs/qa_cierre_2026_11_06.md).
El motor ONNX está conectado en modo de demostración SIMULADO; esto no certifica
precisión real. Las secciones fechadas más abajo son antecedentes del desarrollo.

## Preparación del motor y contexto

[Motor, fotografías, contexto y propuesta experimental](docs/motor_contexto_piloto.md).
Implementación preparada; sin entrenamiento ni activación de criterios reales.

## Registro de validación integrada — 3 de noviembre de 2026

Main `24c305d` ya incluye modelos, revisiones versionadas, cliente HTTP,
supervisor/worker, gateways privados y vistas de Cocina de los bloques 4 y 5.
También integra histórico y recomendaciones. Tener el código no equivale a motor
REAL evaluado, criterios aprobados ni despliegue operativo del worker.

Las secciones «Preparación de Eduardo» conservan antecedentes del 2 de noviembre,
no dependencias aún ausentes en esta versión. Consultar la
[validación integrada actual](docs/validacion_integrada_b4_b5_03_noviembre.md)
para comandos, resultados y pendientes. No interpretar las cifras históricas de
46/53/59/9 o 156 pruebas como total de esta base.

Verificación repetida el 3 de noviembre en copia aislada: **480 pruebas Django
aprobadas** y **42 JavaScript aprobadas**, check sin problemas y migraciones sin
cambios. La suite usa fixtures y bases/archivos temporales; no acredita precisión
de IA REAL ni despliegue operativo en AWS.

También pasó `python ops/analisis/smoke_integracion.py` ejecutado en aislamiento:
worker/proceso hijo reales, motor HTTP SIMULADO, máscaras privadas y rechazo
humano persistido; se bloqueó Confirmar la simulación. No habilita motor ni worker
en el servidor. El primer intento se detuvo por tiempo de preparación mientras
la suite estaba activa; el segundo pasó sin cambiar límites. Véase el registro.

## Base de recomendaciones (bloque 7)

[Contrato v1](docs/contrato_bloque_7.md) e [instrucciones de interfaz](docs/inicio_bloque_7.md).
Bloque 6 integrado. El bloque 7 implementa evaluaciones, recomendaciones, decisiones
y pruebas controladas con ORM y auditoría, sin datos falsos en producción.
Ver [dominio, configuración y límites](docs/dominio_bloque_7.md).
Sin criterios aprobados o contexto histórico, la evidencia permanece insuficiente.

## Base del histórico (bloque 6)

Preparación: [inicio y reparto](docs/inicio_bloque_6.md),
[contrato v1](docs/contrato_bloque_6.md) y [referencia Figma](docs/figma_referencia.md).
DTO y fixtures publicados; la rama `dominio-historico-bloque-6` implementa consultas
y percepción versionada conservando el contrato. Ver [dominio y verificación](docs/dominio_bloque_6.md).
La interfaz se conecta en una entrega independiente, sin datos de muestra en producción.


## Antecedente: preparación de Eduardo del bloque 4

Esta rama, `eduardo-b4-pruebas`, parte de main `1a22306` y añade pruebas numéricas
complementarias y el [plan/evidencias del bloque 4](docs/pruebas_bloque_4.md).
En esa preparación no se incorporaron modelos de Isaac ni configuración de César;
ambas dependencias ya están incluidas en el main actual.

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
el entorno de la carpeta EVA. El main de partida `1a22306` no contenía la aplicación
de análisis; esta advertencia histórica ya no aplica a la base integrada actual.
No se sustituyen rutas ni se omiten checks para aparentar una integración completa.

Estas pruebas verifican cálculos y dominio con datos controlados. No certifican
inferencia real, precisión, cliente del microservicio, worker ni permisos HTTP del
bloque 4 por sí solas. La integración actual añade esas pruebas y la revisión
de Cocina; véanse las entregas de Lino. No instalar YOLO/OpenCV ni cambiar infraestructura
para ejecutar estas pruebas de cálculo.

## Antecedente: preparación de Eduardo del bloque 5

Esta rama `eduardo-b5-pruebas-revision` añade el
[plan y evidencias del bloque 5](docs/pruebas_bloque_5.md) y pruebas de la regla
de elegibilidad publicada por César `2479f9e`. En aquel main de partida `1a22306`
no existía revisión operativa; la base actual ya incorpora esa regla y el flujo.

No confundir validación de una función pura con decisiones humanas persistidas.
El modelo/servicio versionado de Isaac y los endpoints/evidencia de Lino ya están
integrados. La evidencia aislada anterior no equivale por sí sola al recorrido real.
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
Los endpoints de vinculación PC–celular están integrados; su existencia no acredita
el ensayo físico de dos dispositivos en el entorno AWS/HTTPS.
La configuración de desarrollo continúa local hasta activar el entorno autorizado.

Cocina accede a `/analisis/revision/`, con análisis y revisión de evidencia privada
por caso; sin motor evaluado y criterios aprobados no se acreditan resultados REAL.
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
- Cocina/revisión: <http://127.0.0.1:8000/analisis/revision/>. `/cuentas/cocina/` redirige de forma compatible.

El login prioriza Registro, luego Administración y luego Cocina cuando se asignan
varios grupos; el menú permite cambiar entre sus funciones autorizadas. Una cuenta
sin rol no inicia sesión en EVA. La raíz `/` aún puede responder 404.

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Comprobación histórica del 1 de noviembre de 2026 (no total de esta versión):

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

- Ensayo físico de etiquetas y vinculación entre dispositivos en el entorno autorizado.
- Probar montaje/cámara y comparabilidad; el protocolo/checklist ya está versionado.
- Microservicio visual, conjunto de imágenes anotadas y evaluación independiente.
- Validación operativa de revisión, histórico, percepción y recomendaciones implementados; criterios y contexto reales aprobados.
- Verificación de eliminación física de imágenes/máscaras y copias en el entorno autorizado; código de conservación ya integrado.
- Publicación versionada del despliegue y habilitación autorizada del worker.
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
