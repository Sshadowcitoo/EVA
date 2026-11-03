# Revisión del PR #51: contexto HTTP, dataset y endpoint

Base inmutable revisada: `3cff6347ffb08aeb315c18ba768862ea242f0406`, rama
`motor-contexto-recomendaciones`. Rama de esta entrega: `revision-http-motor-contexto`.
PR contra esa rama; sin merge, despliegue ni cambios en una base operativa.

## Hallazgos que requieren coordinación

### R-01 · Polígonos autointersectantes aceptados (calidad del dataset)

`visual_service/dataset.py`, función `leer_poligonos`, comprueba número de vértices,
clase, coordenadas finitas/en rango y área por la fórmula del cordón. No comprueba
que los segmentos no adyacentes se crucen. Este ejemplo autointersectante se acepta
porque su área calculada es positiva:

```text
0 0.1 0.1 0.9 0.9 0.1 0.9 0.7 0.1
```

Reproducción ejecutada: escribir esa línea en un TXT temporal y llamar
`leer_poligonos(ruta, 1)` devuelve una lista de polígonos en lugar de rechazarla.
Consecuencia: una anotación ambigua puede llegar a la exportación pese a pasar el
validador. No demuestra un fallo en todas las anotaciones, pero no debe interpretarse
«dataset válido» como garantía de geometría correcta.

Pendiente de acordar: exigir polígonos simples o especificar explícitamente el
tratamiento/rasterización de autointersecciones, con revisión de anotaciones y
pruebas de regresión. No se cambió el formato ni el validador unilateralmente.

### R-02 · Referencia manual superior a 100 % puede quedar EVALUABLE

`visual_service/evaluation.py`, función `evaluar_par`, agrega MAYOR_100 cuando el
porcentaje del modelo supera 100, pero no cuando lo supera la referencia manual.
La documentación dice de forma general que valores superiores a 100 quedan no
concluyentes. Se reprodujo con máscaras binarias de 20×20:

- Manual: servido de 25 píxeles, retorno de 100 → 400 %.
- Modelo: servido de 100 píxeles, retorno de 25 → 25 %.
- Geometría marcada como verificada solo en este ensayo de software.
- Resultado actual: `estado='EVALUABLE'`, `motivos=[]`, error absoluto de 375 pp.

Pendiente de acordar: si el límite aplica también a la referencia manual, o si ese
caso debe conservar una etiqueta diferenciada de revisión. No se recortó el dato,
no se modificaron criterios ni se cambió el cálculo para ocultar el caso.
Este hallazgo no acredita precisión del modelo: las máscaras son artificiales.

### R-03 · Ruta de registro básico distinta de la operación con bandeja

La ruta `captura:nueva_bandeja` conserva la compatibilidad histórica: crea un servicio
con estado de captura vacío y no habilita fotos (su URL de servido devuelve 404).
Puede guardar sede/modalidad/lote, pero la franja no se fija por crear el registro.
El circuito operativo que acepta fotos es `captura:resolver_bandeja`.

Se añade una indicación y enlace hacia «Capturar con bandeja» para evitar confundir
ambas rutas. No se fuerza el estado del servicio ni se cambia el modelo. Queda para
coordinar la consolidación de ese formulario básico y sus textos históricos.

## Ajustes de interfaz incluidos

- El alta distingue explícitamente datos completos, omisión total compatible y
  combinación parcial rechazada. No se cambia la validación del formulario.
- Confirmar un retorno ya no muestra una ayuda de alta con establecimiento vacío.
  Presenta la instantánea existente, sin campos para editar sede/modalidad/lote.
- La pantalla de fotografía muestra el contexto asociado antes de aceptar la foto.
- Los registros sin contexto muestran «Sin contexto histórico» y explican que no
  se reconstruye a partir de opciones actuales; no se inventa comparabilidad.

Solo se cambian cuatro plantillas, tres archivos nuevos de tests y este documento.
Contratos, modelos, migraciones, servicios, configuración, criterios experimentales
y herramientas productivas del dataset/motor quedan intactos.

## Pruebas HTTP con ORM real

`apps/captura/test_web_contexto.py`: diez casos nuevos, sin reemplazar servicios ni
almacenamiento. Usan SQLite temporal y un directorio privado temporal; las imágenes
PNG son artificiales y pequeñas, exclusivamente para verificar el circuito de captura.
El único reloj sustituido fija fechas reproducibles, no resultados ni permisos.

- GET no crea servicios; combinaciones parciales conservan selecciones y errores.
- Sede/modalidad desconocidas y lotes inválidos no crean servicio ni asignación.
- Ambas rutas de alta guardan sede, modalidad y lote canónicos. El establecimiento,
  franja, fecha y huella enviados por el navegador no sustituyen datos del servidor.
- Antes de aceptar SERVIDO, franja y fecha permanecen pendientes; después se toma
  la fecha real de FotografiaServicio, convertida a America/Guayaquil.
- Se comprueban 00:00, 12:59, 13:00 y 23:59 local, incluido cambio de día desde UTC.
- Foto inválida no fija contexto; reenvío posterior no reclasifica el servido.
- Retorno desde búsqueda/confirmación y subida real no cambia la instantánea ni
  la clave, aunque el POST mande otra modalidad/lote o cambie la configuración.
  Se conserva la franja del servido y se libera la bandeja al cerrar el par.
- Omisión total y registros anteriores conservan contexto vacío: no se rellenan
  retroactivamente. El registro básico sin captura conserva su 404 esperado.
- Rol incorrecto y POST sin CSRF se rechazan sin efectos. Las aprobaciones reales
  y el endpoint operativo continúan desactivados.

Los formularios HTML de captura mantienen su convención existente: entradas
inválidas responden 200 con errores y sin guardado; no se introdujo un contrato 400
nuevo para estas rutas.

## Herramientas del dataset

`visual_service/test_revision_herramientas.py`: seis casos nuevos. Se valida la
exportación sin entrenar: orden de clases/índices, copia exacta de etiquetas y
manifiesto original, bloqueo si faltan clases de train, advertencia de clases no
representadas en test, rechazo de enlaces externos, negativos vacíos con booleano
explícito y rechazo de pesos inexistentes antes de exportar o importar entrenamiento.

Se conservan las pruebas previas de fugas por preparación y píxeles, separación
REAL/SINTETICO, límites y anotaciones inválidas. Los grupos declarados requieren
revisión humana: ni la huella ni el nombre del grupo prueban independencia real.
No se ejecutó entrenamiento ni se cargó un modelo de Ultralytics.

## Compatibilidad del endpoint con EVA

`apps/analisis/test_endpoint_compatibilidad.py`: cinco casos nuevos que atraviesan
`motor.llamar` → HTTP local real → aplicación WSGI → adaptador → JSON/máscaras →
`motor.validar`. Se usa el protocolo multipart de EVA y archivos privados reales
del ensayo, con identificadores numéricos de ServicioComponente.

El único predictor es un doble determinista de test; no simula precisión real:

- Token, versión, request_id, origen y componentes atraviesan el contrato actual.
- Sin aprobación de criterios, la respuesta sigue sin ser comparable aunque el
  servidor de test marque identidad verificada. Esa marca no activa la demo.
- La falta de detección de retorno conserva área/confianza ausentes, sin convertirla
  en cero. SIMULADO no se promueve a REAL.
- Token incorrecto y versión no servida producen 401/422; fallo del predictor devuelve
  503 sin exponer token ni detalle interno. No se cargan resultados exitosos falsos.

No se modifican firmas/DTO ni se activa EVA_VISUAL_ENDPOINT. No se verifica todavía
la ejecución de PredictorYOLO con pesos entrenados, su memoria/latencia real ni el
entrenamiento Ultralytics: faltan imágenes, anotaciones y pesos revisados. El servidor
WSGI incorporado sigue siendo de desarrollo y no se despliega desde esta entrega.

## Comandos y resultados

Entorno virtual con las dependencias declaradas del proyecto (Django 5.2.19,
Pillow 12.3). No se instalaron Torch/Ultralytics ni se descargaron pesos.

| Comando | Resultado |
| --- | --- |
| python manage.py test apps.captura.test_web_contexto | 10 pruebas aprobadas |
| python manage.py test apps.analisis.test_endpoint_compatibilidad visual_service.test_revision_herramientas | 11 pruebas nuevas de herramientas/compatibilidad aprobadas |
| python manage.py test | 529 pruebas aprobadas |
| python -m unittest visual_service.test_dataset visual_service.test_revision_herramientas visual_service.test_inference visual_service.test_evaluation | 26 pruebas aprobadas |
| node --test tests/frontend/*.test.cjs | 42 pruebas aprobadas |
| python manage.py check | Sin incidencias |
| python manage.py makemigrations --check --dry-run | No changes detected |

La migración 0009 se aplica por el runner en su BD aislada. No se ejecutó migrate
contra una base operativa. Los dos hallazgos R-01/R-02 se reprodujeron por separado;
no se añaden tests que conviertan su comportamiento problemático en una garantía.
Que la suite pase NO cierra esos hallazgos ni acredita precisión científica.

## Alcance de la revisión de interfaz

Se revisaron plantillas y respuestas HTTP reales, conservación/escape de campos,
mensajes y ausencia de controles editables de contexto en el retorno. No se afirma
una comprobación gráfica nueva de escritorio/móvil: este entorno no dispone de un
navegador ejecutable y su provisión no se completó durante la revisión. El renderizado
visual queda pendiente, igual que Figma. No se reutilizan capturas anteriores como
si acreditaran los campos nuevos.

Para exportar HTML de los recorridos en un entorno local de QA, el test permite
EVA_CONTEXT_VISUAL_DIR como carpeta de salida; no cambia las vistas productivas.
Las fotografías de prueba se eliminan con el directorio privado temporal.

## Pendientes

- Coordinar R-01 y R-02 antes de dar por validada la cadena de anotación/evaluación.
- Fotografías reales, etiquetas revisadas, preparaciones independientes, pesos y
  evaluación separada de entrenamiento. No activar la propuesta experimental.
- Validación de geometría, memoria/latencia y despliegue por un proceso separado.
- Figma continúa pendiente hasta disponer de acceso o exportaciones autorizadas.
