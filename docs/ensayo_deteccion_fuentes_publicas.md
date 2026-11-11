# Ajuste de detección con fuentes públicas

Base `4d73878`, con los PR #80 y #81 integrados. El ZIP previo pasó la verificación de sus 2.937 hashes. El ensayo no modifica el motor, el orden de las siete clases, el umbral 0,80 ni el saneamiento de solapamientos.

## Datos y separación

Se revisaron 12 fotos públicas y se incorporaron 9 a un manifiesto con URL, autor, licencia, recorte y hash del original. Se anotaron polígonos de las partes visibles en siete recortes. Las dos imágenes de seitán o gluten imitador se marcaron como negativos confirmados. El plato de huesos de Shane Adams se reservó como diagnóstico cualitativo porque conserva restos. No se le asignó una máscara de referencia ni se contó como negativo. Los otros descartes presentaban límites o ingredientes ambiguos. El recorte de menestra proviene de un plato identificado como tal en su fuente.

| Partición nueva | Contenido |
| --- | --- |
| Entrenamiento | Dos preparaciones de pollo con salsa, una de yuca cocida, una de menestra ecuatoriana y un negativo de gluten |
| Validación | Una preparación de pollo con salsa de una autora independiente |
| Prueba | Una preparación de pollo, una de yuca y un negativo de seitán, de autores distintos al ajuste |
| Controles históricos reservados | Cinco fotos públicas anteriores y el par privado servido–retorno |

Los recortes seleccionados aíslan componentes visibles, con bordes manuales aproximados. No sustituyen la evaluación en platos completos. Para cuantificar falsos positivos, los negativos confirmados son la referencia más clara. La métrica de clase ausente en un recorte positivo se interpreta respecto de sus etiquetas y puede incluir un componente vecino no adjudicado. El conjunto nuevo no tiene suficientes referencias de menestra o de pollo parcialmente consumido para estimar generalización.

Las fuentes y preparaciones se asignaron antes del ajuste. El auditor verifica los originales, la ausencia de píxeles duplicados entre particiones nuevas y compara dHash de originales y recortes con las fotos nuevas, la base histórica y los controles reservados. El umbral de cuatro bits es un cribado. Preparaciones parecidas pueden quedar fuera de ese umbral. Los controles reservados y la prueba pública no se copian a la carpeta de entrenamiento.

## Reproducción privada

En un entorno virtual Linux con Python 3.12, instala primero Torch CPU y los requisitos de diagnóstico del repositorio.

```sh
python -m venv .venv-diagnostico
. .venv-diagnostico/bin/activate
pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.15.0' 'torchvision==0.29.2'
pip install -r visual_service/requirements-diagnostico.txt
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 YOLO_AUTOINSTALL=false
export EVA_PAQUETE_PRIVADO=/ruta/privada/EVA_Equipo_B
export EVA_ENSAYO_RAIZ=/ruta/privada/ensayo
export YOLO_CONFIG_DIR="$EVA_ENSAYO_RAIZ/config"
export EVA_DIAGNOSTICO_PRIVADO="$EVA_PAQUETE_PRIVADO/01_modelo_actual"
d="$EVA_ENSAYO_RAIZ/entrega"
p="$EVA_PAQUETE_PRIVADO"

python -m visual_service.experimento_publico preparar "$d/manifiesto.json" \
  "$p/03_ampliacion/dataset_132_train_20_val" "$p/04_evaluacion_reservada" "$EVA_ENSAYO_RAIZ/mixto"
for perfil in conservador completo; do
  python -m visual_service.experimento_publico entrenar "$EVA_ENSAYO_RAIZ/mixto/dataset.yaml" \
    "$d/pesos/vigente.pt" "$EVA_ENSAYO_RAIZ/runs" "$perfil"
done
python -m unittest discover -s visual_service -t .
python -m visual_service.ensayar_par "$d/pesos/modelo_demo_7_clases.onnx" \
  "$d/controles/servido.jpg" "$d/controles/retorno.jpg" "$EVA_ENSAYO_RAIZ/par.json" \
  --componentes arroz pollo --version vigente
```

Se ajustó desde el PT vigente con 137 imágenes de entrenamiento y 21 de validación, a 320 px. La etapa conservadora congela diez capas y usa una tasa inicial de 0,00015. El ajuste completo comienza de nuevo desde el vigente, sin congelar capas y con tasa de 0,0004. Ambos conservan la semilla 17 y guardan puntos de control. El ZIP incluye `medir.py` para repetir las comparaciones de máscaras por clase, omisiones, detecciones de clase ausente, tiempo y memoria con el manifiesto y la validación histórica.

## Par para ensayar la presentación

El paquete anterior contiene un par identificado como servido–retorno del simulacro. Se guardó como control privado y se comprobó con el ONNX vigente. Se detectó arroz en ambas etapas y se omitió pollo en ambas. La geometría del par quedó sin verificar y ningún componente se consideró comparable. En presentación, sirve para mostrar el flujo y el aviso de no concluyente. Las fotos públicas sueltas se usan para detección.

## Resultado a 0,80

En la validación histórica de 20 fotos, las detecciones con IoU de máscara ≥0,50 fueron:

| Componente | Referencias | Vigente | Conservador | Completo |
| --- | ---: | ---: | ---: | ---: |
| Yuca | 0 | — | — | — |
| Pescado | 8 | 0 | 0 | 0 |
| Arroz | 6 | 1 | 0 | 0 |
| Pollo | 1 | 0 | 0 | 0 |
| Menestra | 0 | — | — | — |
| Carne | 8 | 1 | 1 | 1 |
| Ensalada | 5 | 0 | 0 | 0 |

Ambos candidatos añadieron una detección de carne en una imagen sin esa etiqueta en la validación histórica. En la prueba pública nueva, los tres modelos omitieron el pollo y la yuca anotados y ninguno activó las clases del catálogo en el negativo de seitán. Ninguno recuperó el pollo en la validación pública. Tampoco se detectaron clases en la foto de huesos, cuya anotación quedó sin adjudicar. El ensayo no mide el rendimiento en una población representativa.

El ajuste conservador perdió arroz en el retorno reservado y el completo perdió arroz en ambos lados. El conservador se exportó a ONNX estático a 320 px, opset 17, sin NMS integrado ni simplificación. EVA cargó el exportado y reprodujo la regresión del retorno. El completo se conservó como PT experimental. **Se mantienen los pesos vigentes.** La mejora necesaria en pollo y la retención de arroz son condiciones que ninguno cumplió.

Pasaron 52 pruebas de `visual_service`, incluidas las tres de paridad privada del modelo vigente. La suite nueva comprueba la separación por fuente, la exclusión de controles y prueba, el cribado de similitud y la ausencia de comparabilidad o porcentaje en el ensayo privado.

### CPU y controles conocidos

Se midieron 30 inferencias por peso tras calentamiento, en procesos separados, con afinidad a dos CPU lógicas y con preprocesamiento y reconstrucción de máscaras incluidos. RSS es el pico del proceso con pesos y dependencias. La distribución local no representa los tiempos de producción.

| Peso | Mediana (ms) | P95 (ms) | RSS pico (MiB) |
| --- | ---: | ---: | ---: |
| Vigente PT | 54,9 | 72,0 | 418 |
| Vigente ONNX | 32,4 | 59,9 | 126 |
| Conservador PT | 58,7 | 64,6 | 427 |
| Conservador ONNX | 30,6 | 45,5 | 126 |
| Completo PT | 57,8 | 74,4 | 424 |

Los cinco pesos conservaron los mismos conjuntos de clases en tres fotos conocidas de los platos piloto. Este control de presencia no neutraliza la regresión en el par reservado. El detalle por imagen y la IoU media con omisiones se incluyen en los JSON privados.
