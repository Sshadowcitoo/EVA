# Motor visual, contexto y criterios experimentales

## Estado real de la entrega

Se implementan validación de dataset, exportación YOLO, entrenamiento explícito,
adaptador de inferencia y endpoint HTTP interno; no se ha entrenado un modelo ni
configurado un motor operativo. No hay fotos guardadas/anotadas ni pesos disponibles
para evaluar. No se descargan pesos ni se instala ninguna dependencia en esta entrega.
Torch, Ultralytics, OpenCV y Pillow ya estaban presentes en el entorno local.

La inferencia se ejecuta como proceso separado; el servidor WSGI incorporado solo
escucha en 127.0.0.1 y es para desarrollo. No se entrenará automáticamente en EC2 ni
se han creado recursos de pago. Antes de desplegar hay que medir memoria/latencia
con pesos reales y respetar el plazo total de 30 segundos del worker.

## Fotografías y anotaciones

Carpeta local ignorada por Git: `data/piloto/fotos/`; anotaciones en
`data/piloto/anotaciones/`; manifiesto inicial vacío en `data/piloto/manifiesto.json`.
Copiar fotos ahí no inicia procesos ni las sube a terceros. Los pesos .pt/.onnx y
el directorio privado de configuración Ultralytics también se excluyen de Git.

Las fotos por sí solas no son etiquetas. Delimitar los alimentos visibles mediante
polígonos; nombres exactos: yuca, pescado, arroz, pollo, maduro, menestra, carne,
ensalada. Una preparación mantiene el mismo grupo aunque se retire comida, se cambie
el ángulo o se genere otra mesa/fondo. Los grupos completos se separan antes de
crear variantes. Capturas reales independientes para val/test; sintéticas solo train.
La cantidad de fotos no equivale a cantidad de preparaciones independientes.

Formato de una entrada del manifiesto (rutas relativas a data/piloto):

```json
{"archivo":"fotos/preparacion-01-servido.jpg",
 "etiquetas":"anotaciones/preparacion-01-servido.txt",
 "grupo":"preparacion-01","particion":"train","origen":"REAL"}
```

Los TXT tienen una línea por instancia: índice de clase desde cero y al menos tres
pares x/y normalizados en 0..1, siguiendo el orden de clases del manifiesto. Un TXT
vacío requiere vacio_confirmado=true y significa ausencia visible anotada, no una
foto sin revisar. No etiquetar caldo que oculta pescado/yuca como ausencia: ese
material requiere revisión y no puede utilizarse como negativo confiable.

El validador exige train/val/test con preparaciones separadas, verifica polígonos,
formatos, orientación, límites y duplicación exacta de píxeles entre particiones.
No demuestra por sí solo que dos grupos declarados sean preparaciones independientes
ni detecta todas las similitudes: la asignación de grupos requiere revisión humana.
Informa clases faltantes por partición; no iniciar el entrenamiento si falta alguna
clase declarada en train. Val/test sin una clase no validan esa clase.

```powershell
python -m visual_service.dataset data/piloto/manifiesto.json
python -m visual_service.train data/piloto/manifiesto.json data/exportacion-01
# Solo con anotaciones revisadas y pesos locales de segmentación:
python -m visual_service.train data/piloto/manifiesto.json data/entrenamiento-01 --pesos C:/ruta/pesos-segmentacion.pt --device cpu
```

Cada destino debe ser nuevo. No se sobrescriben originales ni exportaciones, ni se
borran carpetas ante fallos. Una exportación parcial se revisa y se usa otro destino.
La configuración de Ultralytics se guarda dentro del área de trabajo/entrenamiento,
no se modifica la configuración global del usuario. Los valores de epochs/imgsz son
un presupuesto ajustable, no una garantía de precisión.

Fuentes del formato/API: https://docs.ultralytics.com/datasets/segment/ y
https://docs.ultralytics.com/tasks/segment/ (consultadas 03/11/2026).

## Inferencia y conexión con Django

El modelo entrenado debe usar las clases del piloto. El adaptador rechaza pesos
COCO genéricos presentados como modelo final. No descarga .pt si falta el archivo.
Une instancias de la misma clase y conserva máscaras binarias con las dimensiones
originales. Solapamientos entre clases dejan los componentes ambiguos sin máscaras;
una detección ausente produce área None y resultado no concluyente, nunca cero.
La puntuación del detector no equivale a una probabilidad de acierto calibrada.

Endpoint POST /v1/analizar-par, multipart metadata/servido/retorno, Bearer interno,
límites de cuerpo y respuesta, sin rutas ni URL remotas de máscaras. Mantiene
REAL/SIMULADO del caso; no promueve un caso simulado. La versión del modelo se liga
a los primeros 160 bits del SHA-256 de los pesos, en una cadena de 47 caracteres
compatible con la columna existente. El token va en EVA_VISUAL_TOKEN, no en argv/logs.

```powershell
# Configurar EVA_VISUAL_TOKEN en el entorno del proceso sin publicarlo.
python -m visual_service.server --pesos C:/ruta/modelo-entrenado.pt --device cpu
```

Copiar la versión que imprime en EVA_VISUAL_VERSION_MODELO, configurar el endpoint
local y usar el worker procesar_analisis. Esa activación NO se ha realizado aquí.
El token debe coincidir con el del cliente y tener al menos 24 caracteres.

Comparabilidad permanece deshabilitada por defecto. --identidad-verificada solo
puede usarse tras validar el montaje fijo y la geometría; tener fotos del mismo
tamaño no demuestra que sean comparables. Django sigue exigiendo protocolo,
checklist y criterios aprobados. No se ha aprobado ese montaje ni su precisión.
La primera versión tampoco certifica plato vacío por mera falta de detecciones.

visual_service/evaluation.py calcula IoU, Dice y error absoluto en puntos porcentuales
frente a máscaras manuales. Casos sin detección conservan métricas ausentes; máscaras
ambas vacías no inflan la media de IoU. Más de 100 % se conserva como no concluyente.
Todavía no existe un informe de rendimiento sobre imágenes reales: faltan etiquetas,
pesos y la ejecución de la evaluación separada.

## Contexto aprobado por el usuario

La instantánea del servicio registra establecimiento/sede, modalidad, lote y franja
automática del servido. Configuración inicial: La Mesa Costeña, sede principal,
mesa/autoservicio, franjas de una hora de Ecuador (franja_minutos=60). Se puede
configurar otra duración que divida el día; versionar cambios de operación.

El código de lote se comparte entre porciones de una misma preparación. No es un
identificador de cliente ni de bandeja. No forma parte de la clave de comparación:
se comparan lotes distintos en contexto equivalente. La clave incluye versión,
establecimiento, sede, modalidad y franja, además de los separadores de plato,
porción, componente, modelo/configuración y protocolo ya existentes en histórico.

Sede/modalidad/lote se guardan juntos. Para compatibilidad se admite omitir los tres,
pero el registro queda explícitamente sin contexto, no comparable. El formulario
rechaza datos parciales. No se acepta el nombre del establecimiento desde el POST.
La franja solo se fija al aceptar la foto SERVIDO, no usando la hora del navegador
ni la fecha de creación del registro. El retorno no reclasifica el contexto.
Registros antiguos no se rellenan por inferencia. La migración 0009 solo agrega
columnas vacías; cambios de configuración no alteran instantáneas anteriores.

El filtro actual de hora permite escoger una franja. Si hay varias sedes/modalidades
compatibles en apariencia, se mantienen grupos separados y no se mezclan sus medias.
Un alcance con varios grupos requiere acotarlo; no se agregó un nuevo filtro público
por sede que cambiara unilateralmente los DTO del bloque 6.

## Propuesta de recomendaciones, sin activar

Archivo: ops/analisis/criterios_piloto.propuesta.json. No lo importa settings.
Todos los estados aprobada/comparabilidad_aprobada siguen false. Valores propuestos:

| Condición | Propuesta experimental |
| --- | --- |
| Puntuación mínima del detector | 0.80 por componente; calibrar con validación |
| Presencia visual de sobrante | más de 10 % |
| Muestra | al menos 5 servicios aptos por periodo |
| Persistencia | al menos 2 días completos con esa muestra |
| Preparaciones | al menos 2 lotes distintos conocidos |
| Cobertura | al menos 80 % de candidatos aptos |
| Calidad | revisión confirmada y un grupo/contexto comparable |

Mínimo resultante: 10 servicios distribuidos entre dos periodos, no 10 fotos de una
preparación. Es un punto inicial de piloto, no un tamaño de muestra validado ni una
promesa estadística. Los límites se revisan en validación y se fijan antes de abrir
la muestra final de prueba; si esta se usa para ajustar, deja de ser prueba final.

Reglas propuestas ordenadas: MANTENER solo con intensidad <=10 y prevalencia <=20;
REVISAR_PORCION desde intensidad 15 y prevalencia 40; los demás casos suficientes
proponen PRUEBA_CONTROLADA. Son sugerencias para decisión humana, no inferencia de
causas ni cambios automáticos de porciones. No se propone revisar preparación solo
por una imagen: requeriría definir evidencia adicional y su criterio.

La condición lotes_minimos se aplica cuando figura en el perfil versionado; no se
reinterpreta un perfil anterior que no la contenía. El nuevo snapshot de contexto
participa en la vigencia de la evaluación. No se activaron criterios reales.

## Verificación de la entrega

- 508 pruebas aprobadas mediante manage.py test, incluidas pruebas del dataset,
  inferencia, métricas, captura de contexto y conexión completa cliente/endpoint/
  validador. Las predicciones de estas pruebas son dobles identificados como tests,
  no una evaluación de pesos entrenados.
- 42 pruebas JavaScript aprobadas; check sin incidencias; makemigrations --check
  --dry-run sin cambios pendientes tras generar 0009.
- Migración aplicada por el runner solo en su BD aislada. No se ejecutó migrate
  sobre la base operativa ni se modificó AWS.
- La prueba cruzada encontró que los componentes usan IDs numéricos, además del
  soporte UUID de pruebas. El adaptador se corrigió para respetar el contrato
  existente; la suite completa posterior pasó.
- Validada la propuesta JSON: todos los flags de aprobación siguen false.
- No se entrenó ni descargó modelo, no se aprobó comparabilidad ni precisión.
