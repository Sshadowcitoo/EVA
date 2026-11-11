# Auditoría de detección y protocolo de evaluación del piloto

Base `c3404ff`. El paquete privado incluye el checkpoint actual, el ONNX operativo, el candidato descartado y sus informes. Se verificaron los 2.937 hashes declarados. El manifiesto de hashes se excluye de su propia lista. El orden del dataset ampliado y la secuencia serializada en el ONNX son **yuca, pescado, arroz, pollo, menestra, carne y ensalada**. El evaluador exige esa misma secuencia al abrir cada peso; esa ejecución queda pendiente. Las anotaciones antiguas de ocho posiciones no se reutilizan sin remapeo y maduro queda fuera de esta evaluación.

## Evidencia disponible a 0,80

Datos archivados, a 320 px y con `rect=False`. En las columnas de resultados, **actual → candidato**. «IoU ≥ 0,50» cuenta coincidencias de máscara por componente visible, uniendo los fragmentos por clase.

| Componente | Referencias externas | Detectados externos | IoU ≥ 0,50 externo | Falsos positivos de clase ausente externos | Retención conocida detectados |
| --- | ---: | --- | --- | --- | --- |
| Yuca | 0 | Sin referencia | Sin referencia | 0 → 0 | 21 → 20 de 23 |
| Pescado | 8 | 0 → 0 | 0 → 0 | 0 → 0 | 20 → 19 de 23 |
| Arroz | 6 | 1 → 1 | 1 → 1 | 0 → 0 | 56 → 50 de 56 |
| Pollo | 1 | 0 → 0 | 0 → 0 | 0 → 0 | 31 → 31 de 31 |
| Menestra | 0 | Sin referencia | Sin referencia | 0 → 0 | 23 → 22 de 23 |
| Carne | 8 | 1 → 0 | 1 → 0 | 0 → 2 | 24 → 19 de 24 |
| Ensalada | 5 | 0 → 0 | 0 → 0 | 0 → 0 | 19 → 19 de 19 |

Ejemplos del informe privado: el actual reconoce arroz y carne en un caso público de arroz con menestra y carne; el candidato no supera el umbral en ninguna de las cinco fotos públicas reservadas. En el servido del simulacro ambos omiten el pollo. El candidato elimina una detección espuria de menestra, pero el arroz del retorno cae de 0,8313 a 0,3522. La mejora agregada de mAP no compensa esas regresiones. Retener detecciones sobre imágenes ya entrenadas mide conservación del comportamiento. Las fotos sueltas públicas miden reconocimiento, sin medición de sobrante entre servicios distintos.

## Datos, separación y siguiente adquisición

Se volvieron a comprobar los polígonos de las 132 imágenes de entrenamiento y 20 de validación. No hay imágenes negativas anotadas en esas particiones. Entre train, val y las 7 reservadas no se hallaron píxeles idénticos ni distancias dHash de hasta 4 bits en la orientación normalizada. dHash es un cribado y no demuestra independencia de preparación. El pollo de validación tiene una sola referencia asistida y la única preparación real conocida del piloto no equivale a muchas preparaciones. Yuca y menestra siguen sin referencias externas cuantitativas.

- [Seco de pollo ecuatoriano, JONAVIAG, CC BY-SA 4.0](https://commons.wikimedia.org/wiki/File:IMa20180428_162330.jpg) es una fuente candidata identificada para revisión visual y anotación. Sin descargar, transformar ni incorporar a ninguna partición.
- [FoodSeg103](https://github.com/LARC-CMU-SMU/FoodSeg103-Benchmark-v1) es una fuente de máscaras de ingredientes. Para nuevas incorporaciones, verificar licencia del archivo y semántica. Conservar la exclusión de pollo/pato mixto y frijol sin preparación identificada.
- Antes de aumentar imágenes, registrar fuente, licencia, preparación, transformación, clase y visibilidad. Agrupar variantes por preparación y fuente, revisar candidatos de duplicado por hash y separación visual. Reservar preparaciones distintas, incluidas fotos de retorno, y conservar intactas las siete reservadas. Añadir negativos con alimentos fuera del catálogo y casos ambiguos sin adjudicar contornos ocultos.

## Reproducción privada

Con un entorno ya habilitado, el punto de partida del ZIP es `05_herramientas/ejecutar_experimento.py`; los argumentos portátiles están en su README. Para un dataset ampliado, usar el manifiesto de `visual_service.dataset` con train, val y test separados y anotaciones revisadas. Comparar, como mínimo, el checkpoint vigente ajustado sobre el conjunto ampliado frente a una inicialización desde los pesos de segmentación preentrenados del paquete, con la misma semilla y particiones. Usar puntos de control de validación y detener si no hay mejora por componente al umbral de uso. Mantener test sellado hasta elegir el candidato.

```sh
YOLO_AUTOINSTALL=false python -m visual_service.train /privado/dataset/manifiesto.json /privado/ejecuciones/ajuste --pesos /privado/pesos/best.pt --imgsz 320 --device cpu
python -m visual_service.evaluar_candidato /privado/dataset/manifiesto.json /privado/pesos/best.pt /privado/resultados/pt.json --particion test --imgsz 320
```

Solo cuando un candidato esté justificado, exportar YOLO11-seg a ONNX estático `imgsz=320, batch=1, dynamic=False, nms=False, simplify=False` con el comando de exportación de Ultralytics en el entorno autorizado. Confirmar previamente que el exportador y sus dependencias ya estén disponibles. Ejecutar `evaluar_candidato` con el ONNX usando el mismo manifiesto y parámetros. Usar `01_modelo_actual/reproducir.py --repo … --salida … --referencia pt` del ZIP para los controles actuales de concordancia; para un nuevo candidato comparar sus pares de pesos en una copia privada, con las mismas entradas y tamaños. Concordancia PT/ONNX y calidad contra anotación son verificaciones separadas.

El evaluador informa por imagen y clase, omisiones, máscaras, clases ausentes, solapamientos que sugieren confusión, tiempo de inferencia y RSS pico del proceso cuando el sistema lo ofrece. Las uniones se miden antes del saneamiento; validar además la eliminación de solapamientos y estados no concluyentes con `visual_service.test_paridad_privada` y pares revisados. Una omisión no se convierte en 0 % y la confianza no representa precisión.

## Estado

25 pruebas unitarias ejecutadas con éxito, 10 de ONNX omitidas por dependencias ausentes. No hubo inferencia nueva, entrenamiento, exportación, medición de CPU sobre pesos ni cambio del motor. Se conservan las barreras actuales de comparabilidad y el umbral operativo. Queda pendiente ejecutar con PyTorch/Ultralytics y OpenCV/ONNX Runtime ya disponibles o autorizados, y reunir máscaras independientes revisadas, prioritariamente pollo con salsa/restos, yuca y menestra. Mantener los pesos vigentes hasta superar retención, evaluación nueva, negativos, pares y paridad. El ZIP privado ya contiene hashes y versiones de los pesos entregados.

## Segunda ejecución privada

Se verificó de nuevo el ZIP y se instaló el entorno virtual CPU sin modificar Python global. Se comprobó el orden de las siete clases de los pesos vigentes y los dos candidatos. A 320 px, `rect=False`, `retina_masks=True`, confianza 0,80, IoU NMS 0,70 y máximo 32, las tres pruebas privadas pasan con Ultralytics 8.4.150. La prueba del encebollado comprueba que se eliminan los píxeles compartidos y que los componentes siguen sin porcentaje.

Ultralytics 8.4.210 utiliza una interpolación intermedia para el recorte del padding en la reconstrucción nativa. Con esa versión, incluso al usar el mismo archivo ONNX en ambos lados, la IoU entre implementaciones fue 0,883 para yuca y 0,887 para pescado en el encebollado. En arroz con menestra y carne fue 0,974–0,989 y en seco fue 1,000. Esto mide concordancia antes del saneamiento. Se fija la versión de referencia en los requisitos de diagnóstico y se conserva el runtime operativo.

```sh
python -m venv .venv-diagnostico
. .venv-diagnostico/bin/activate
python -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.15.0' 'torchvision==0.29.2'
python -m pip install -r visual_service/requirements-diagnostico.txt
export YOLO_AUTOINSTALL=false OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
export EVA_DIAGNOSTICO_PRIVADO=/ruta/privada/EVA_Equipo_B/01_modelo_actual
python -m unittest discover -s visual_service -t .
python "$EVA_DIAGNOSTICO_PRIVADO/reproducir.py" --repo "$PWD" --salida /ruta/privada/paridad-pt --referencia pt
python "$EVA_DIAGNOSTICO_PRIVADO/reproducir.py" --repo "$PWD" --salida /ruta/privada/paridad-onnx --referencia onnx
```

### Ensayo con un contorno nuevo

Se revisaron tres fuentes adicionales. Se anotó manualmente el pollo visible de [Seco de Pollo. Tabacundo 2026, TupakAmaruIshkay, CC BY-SA 4.0](https://commons.wikimedia.org/wiki/File:Seco_de_Pollo._Tabacundo_2026.jpg) en un recorte que evita componentes vecinos. Se excluyeron de entrenamiento la preparación de JONAVIAG y el [encebollado de Maryte Peralta](https://commons.wikimedia.org/wiki/File:Encebollado..jpg), donde el caldo y la salsa no permiten adjudicar contornos con suficiente confianza. Esta última autora ya aparece en las reservadas y no cuenta como nueva fuente independiente. Las siete fotos reservadas originales quedaron intactas.

Se ajustó el checkpoint vigente con 133 imágenes de entrenamiento y las mismas 20 de validación. El ensayo guardó cuatro puntos de control, con semilla 17 y AdamW. Se detuvo al constatar que ninguno recuperaba el pollo al umbral operativo y que todos perdían el arroz detectado en validación. La preparación, los argumentos, los hashes y el checkpoint descartado están en la entrega privada.

| Componente | n de validación | Vigente detecciones / IoU ≥0,50 | Descartado anterior | Nuevo ajuste |
| --- | ---: | ---: | ---: | ---: |
| Yuca | 0 | — | — | — |
| Pescado | 8 | 0 / 0 | 0 / 0 | 0 / 0 |
| Arroz | 6 | 1 / 1 | 1 / 1 | 0 / 0 |
| Pollo | 1 | 0 / 0 | 0 / 0 | 0 / 0 |
| Menestra | 0 | — | — | — |
| Carne | 8 | 1 / 1 | 0 / 0 | 3 / 2 |
| Ensalada | 5 | 0 / 0 | 0 / 0 | 0 / 0 |

El descarte anterior añadió dos detecciones de carne sin etiqueta de referencia y dos puntos intermedios del nuevo ajuste añadieron una detección de yuca sin etiqueta. En el par reservado del simulacro, el vigente reconoce arroz en servido y retorno y el nuevo ajuste pierde ambas detecciones. Ninguno recupera el pollo. En la foto pública reservada con menestra, el vigente detecta arroz y carne y el nuevo ajuste solo detecta arroz. Las fotos nuevas sin contorno se usaron para revisar presencia, sin estimar precisión ni porcentajes de sobrante.

Se mantiene el modelo vigente y el umbral 0,80. El candidato no pasa a ONNX porque no conserva el reconocimiento en el par reservado. Sigue faltando una evaluación independiente con máscaras revisadas de pollo con salsa y restos, yuca y menestra, pares completos de la misma bandeja, negativos y preparaciones separadas por fuente.

### Coste de inferencia en CPU

Proceso nuevo por peso, dos hilos de inferencia, tres fotos conocidas con calentamiento y 30 predicciones medidas por peso. El tiempo incluye preprocesamiento y reconstrucción de máscaras. RSS es el pico de proceso, incluidas bibliotecas y pesos. Resultados locales sin extrapolar a producción.

| Peso | Mediana (ms) | P95 (ms) | RSS pico (MiB) |
| --- | ---: | ---: | ---: |
| Vigente PT | 24,2 | 49,4 | 416 |
| Vigente ONNX | 30,3 | 39,3 | 122 |
| Descartado anterior PT | 27,6 | 51,4 | 415 |
| Nuevo ajuste PT | 29,1 | 39,4 | 414 |

Pasaron 50 pruebas de `visual_service`, incluidas las tres privadas de paridad.
