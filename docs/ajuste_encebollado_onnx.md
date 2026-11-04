# Concordancia del adaptador ONNX en encebollado

Base: `main` en `46a286a64dbe328c10170804f5640315ac05b531`, con #58 integrado. No se reentrena ni se sustituyen pesos. No se modifican contratos, catálogo, criterios, recomendaciones ni la política de solapamientos.

## Reproducción y causa

Se verificaron las 69 sumas SHA-256 del paquete privado. Se usó la PNG exacta de encebollado de 768×429, el ONNX desplegado y su checkpoint PT del mismo entrenamiento. SHA-256 del ONNX: `e93312070293e4d65d0bf9f46f6436d72ca5beb52eef19eb5976bbfa35551efe`.

Primero se comparó el adaptador y Ultralytics ejecutando **el mismo ONNX** sobre la misma imagen: RGB, entrada estática 320, `rect=False`, CPU, confianza 0,80, IoU NMS 0,70, `max_det=32`, `retina_masks=True`. Se reprodujeron exactamente los IoU originales. La comparación es entre uniones por clase **antes** de quitar píxeles compartidos, no contra anotaciones.

| Cambios acumulados en el adaptador | Yuca | Pescado |
| --- | ---: | ---: |
| Base | 0,6148843931 | 0,8472919079 |
| Entrada con OpenCV INTER_LINEAR | 0,8653904588 | 0,8518757252 |
| Además, padding del prototipo como scale_masks | 0,9863908547 | 0,9876230661 |
| Además, recorte de cajas fraccionarias como crop_mask | 1,0000000000 | 1,0000000000 |

Causas comprobadas:

- Pillow BILINEAR aplica antialias al reducir la entrada. Ultralytics usa OpenCV INTER_LINEAR. Los tensores de entrada distintos cambian scores, instancias y máscaras: en el control había ocho detecciones del adaptador frente a siete de referencia; al igualar la entrada quedan siete.
- El padding del prototipo se calculaba sin redondear antes el tamaño sin padding. En la imagen de encebollado, los prototipos 80×80 deben recortarse en filas `[17:62]`, frente a `[18:62]` en la base. Esa fila desplazaba las fronteras al ampliar a 429 píxeles.
- `rint` redondeaba las cajas al entero más próximo. El recorte de referencia conserva índices enteros `x >= x1` y `x < x2`: se necesita `ceil` en ambos extremos de los slices.

Revisiones adicionales:

- Se mantuvo Pillow para ampliar logits: sustituir solo esa ampliación por INTER_LINEAR de OpenCV no cambió los IoU de los controles. No se añadió un cambio sin efecto reproducible.
- NMS por clase e IoU 0,70, clipping anterior a NMS y límite de 32 se conservaron. No explican el diagnóstico: tras corregir entrada y máscaras hay igualdad de las uniones en los controles. Esto no demuestra equivalencia universal de NMS en cajas fuera de imagen o empates.
- El límite intermedio de 1280 no interviene en estas fuentes; se conserva para acotar memoria. La prueba de imagen grande conserva tamaño/binario; no certifica paridad por encima de ese límite.
- Se corrigió la frontera exacta del filtro de confianza de `>= .8` a `> .8`, como la referencia. No explica el diagnóstico original; tiene una regresión sintética específica y no cambia el valor del umbral.

## Corrección y dependencia

La corrección se limita al adaptador y añade `opencv-python-headless` al runtime ONNX para reproducir la reducción de entrada. No incorpora PyTorch ni Ultralytics al runtime de producción. Se mantiene el tamaño original y el formato binario L de las máscaras.

`visual_service/inference.py` permanece intacto: elimina de **todas** las clases los píxeles compartidos. Los componentes afectados conservan `comparable=False`; sus zonas restantes sirven para revisión y no habilitan porcentajes válidos. La prueba privada verifica las máscaras saneadas contra las uniones originales y confirma que los dos componentes quedan no comparables aun solicitando identidad verificada.

## Resultados

- Suite completa Django: **566 pruebas OK, sin omisiones**, ejecutada con el paquete privado habilitado.
- Frontend: **42 pruebas OK**, sin omisiones.
- `manage.py check`: sin incidencias. `makemigrations --check --dry-run`: sin cambios.
- Cuatro regresiones sintéticas nuevas: las cuatro fallan sobre el adaptador base y pasan con la corrección (tensor sin antialias/letterbox, padding impar, cajas fraccionarias y frontera 0,80).
- Tres pruebas privadas optativas: mismo ONNX, checkpoint PT y conservación de la regla de conflictos. Sin el paquete, se omiten explícitamente; las pruebas ordinarias no necesitan fotos o pesos privados.
- PNG exacta: IoU **1,0 para yuca y pescado**, tanto con referencia ONNX como PT. Los controles de arroz/carne/menestra/ensalada y seco también dan 1,0 en todas sus clases.
- Comprobación adicional de las 23 JPG conocidas de encebollado: 41 pares imagen/clase en la unión de detecciones corregidas y referencia, todos con IoU 1,0. Antes había 43 pares, mínimo 0 y media 0,83981, incluyendo clases detectadas solo por una implementación. Son fuentes conocidas por entrenamiento: **no es una validación independiente**.

Entorno de reproducción: Linux, Python 3.12.14, Ultralytics 8.4.150, ONNX Runtime 1.31.1, OpenCV 5.0.0, NumPy 2.5.3, Pillow 12.3.0 y Torch 2.15.0+cpu. Python/Torch difieren del paquete Windows (3.13.7/2.14.0); pese a ello se reprodujeron exactamente los resultados base y la referencia PT coincide en las máscaras binarias de los controles. No se afirma igualdad universal de los tensores entre plataformas.

## Repetición privada y comparación visual

Instalar el runtime ONNX actualizado y las dependencias de diagnóstico en un entorno aislado, sin descargar modelos. Situar el paquete fuera del repositorio y desactivar la instalación automática de Ultralytics:

```bash
export EVA_DIAGNOSTICO_PRIVADO=/ruta/privada/entrega_equipo_b_encebollado
export YOLO_AUTOINSTALL=false
export YOLO_CONFIG_DIR=/ruta/privada/runtime
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
python -m unittest visual_service.test_paridad_privada -v
python manage.py test
node --test tests/frontend/*.test.cjs
```

El `reproducir.py` del paquete permite guardar las máscaras binarias antes/después, indicando el checkout base y el corregido con `--repo`, y directorios privados distintos con `--salida`. Repetir con `--referencia pt`; las condiciones ya están fijadas por ese script. No usar superposiciones como entrada ni las etiquetas de entrenamiento como validación independiente.

La lámina **comparacion_encebollado_privada.png**, entregada por adjunto privado, muestra dos filas (yuca/pescado) y tres columnas (adaptador base/corregido/referencia con el mismo ONNX), con los IoU y la advertencia de que no mide precisión real. Se inspeccionó visualmente junto con las máscaras binarias. No se incluye en GitHub ni se enlazan allí fotos, pesos o archivos privados.

## Pendientes concretos

1. QA del grupo en el entorno objetivo con estas versiones, el runtime actualizado y sus pesos privados; no se hizo despliegue.
2. Validación real con anotaciones independientes: el encebollado del control es sintético y las 23 referencias fueron usadas en entrenamiento. IoU 1 entre implementaciones no prueba que el alimento esté bien segmentado.
3. Si se necesita paridad fuera de este diagnóstico, acordar pruebas específicas de imágenes >1280, cajas fuera de imagen, empates de NMS y más de 32 instancias antes de ampliar el parche. No se ocultan esos límites ni se modifica la política de memoria/detecciones.
4. No proponer reentrenamiento por esta discrepancia del adaptador: primero queda corregida y reproducida. Evaluar necesidades del modelo por separado con evidencia independiente.
