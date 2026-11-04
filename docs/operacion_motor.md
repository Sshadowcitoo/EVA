# Preparación operativa del motor visual

## Runtime ONNX para la demostración

La factory admite `.onnx` además de `.pt`, con la misma comprobación SHA-256 y
autenticación. Para ONNX solo se carga `onnxruntime`, NumPy (dependencia del runtime)
y Pillow; el servidor no necesita PyTorch, OpenCV ni Ultralytics. Dependencias en
`visual_service/requirements-onnx.txt`. El entrenamiento y la exportación ocurren
en el equipo local, nunca en EC2.

El adaptador admite la salida estática de YOLO11-seg sin NMS incorporado, nombres
de clase explícitos del catálogo y un único RGB de hasta 1024 px de lado de entrada
del modelo. Las fotos mantienen los límites de carga del proyecto. Para fotografías
grandes, los intermedios float se limitan a 1280 px de lado y la máscara binaria se
alinea después al tamaño original. Esto no certifica precisión geométrica. Se
conservan máscaras ausentes y el tratamiento no concluyente; no hay cero inventado.

La unidad limita memoria a 384 MiB (umbral blando 256 MiB) para proteger la web ante
un consumo inesperado. Medir memoria y tiempo del par en la instancia antes de
habilitar el worker. Si no cabe o excede el plazo, mantenerlo detenido y revisar
la causa: no crear otra instancia ni aumentar costos automáticamente.

El primer modelo es experimental, sin ejemplos de maduro, entrenado con una
preparación real del seco y fuentes sintéticas de los otros platos. Las variantes
de cada fuente permanecen en entrenamiento. No hay prueba real independiente:
los diagnósticos sobre esas fuentes no equivalen a precisión generalizable.
El validador estricto de datasets de producción no se modifica ni admite declarar
fuentes sintéticas como reales. La ruta de demostración conserva esa procedencia
y no publica mAP de entrenamiento como validación independiente.

Las ejecuciones de QA con material sintético usan origen SIMULADO, sin promoverlo
a evidencia real de histórico/recomendaciones. La comparabilidad y las aprobaciones
operativas permanecen desactivadas hasta validación independiente del montaje y
del modelo; la aprobación documental de los valores del perfil es otra decisión.

Los dos adaptadores filtran detecciones por puntuación 0.80, conforme al perfil
experimental aprobado. No es una probabilidad calibrada de acierto. El 03/11/2026
se ratificó retirar los píxeles compartidos entre clases de todas sus máscaras y
mostrar solo zonas sin conflicto, conservando comparable=False en los componentes
afectados. No se elige una clase ganadora ni se habilitan porcentajes concluyentes.
`EVA_ANALISIS_VERSION_CONFIGURACION` permite identificar esta configuración en cada
intento sin aprobar umbrales operativos ni alterar instantáneas anteriores.

Esta entrega prepara archivos y verificaciones; no instala dependencias ni activa
el motor/worker en AWS. No incluye pesos ni demuestra latencia o precisión real.
El motor usa un proceso CPU, privado en 127.0.0.1:8765. No abrir ese puerto en EC2
ni publicarlo en Nginx. La web continúa independiente del motor.

## Archivos y requisitos

- `visual_service/production.py`: factory WSGI; exige pesos locales absolutos `.pt`,
  token de al menos 24 caracteres y versión coincidente con su SHA-256. Rechaza
  configuración incompleta antes de cargar el modelo.
- `ops/analisis/eva-motor.service`: Gunicorn, un worker síncrono y un thread;
  reinicio ante fallo, límite de reinicios y directorio de estado separado del código.
- `ops/analisis/eva-analisis.service`: worker Django; comprueba salud/versión antes
  de consumir la cola. Un fallo del motor no detiene la aplicación web.
- `GET /v1/salud`: requiere el mismo Bearer; indica modelo cargado y versión.
  No ejecuta inferencia ni certifica exactitud o comparabilidad.

Se requieren dependencias del motor y Gunicorn en Linux, según
`visual_service/requirements.txt`, además de las del proyecto. Su instalación debe
autorizarse al activar; no se ha hecho en esta entrega. Seleccionar versiones
compatibles y registrar las versiones efectivamente evaluadas antes de presentar.
No entrenar en la instancia de la demo. Medir RAM y latencia con pesos reales:
la capacidad de la instancia actual todavía no está validada para inferencia.

## Configuración cuando existan pesos revisados

Guardar pesos versionados e inmutables, legibles por `eva`, fuera del repositorio,
por ejemplo `/var/lib/eva-modelos/piloto-01.pt`. No reutilizar un nombre modificando
su contenido durante la ejecución. En `/etc/eva/eva.env`, sin imprimir secretos:

```text
EVA_VISUAL_PESOS=/var/lib/eva-modelos/piloto-01.onnx
EVA_VISUAL_ENDPOINT=http://127.0.0.1:8765/v1/analizar-par
EVA_VISUAL_VERSION_MODELO=sha256-<primeros 40 caracteres del SHA-256 de los pesos>
EVA_VISUAL_TOKEN=<secreto interno de al menos 24 caracteres>
EVA_VISUAL_ORIGEN=SIMULADO
EVA_ANALISIS_VERSION_CONFIGURACION=piloto-demo-onnx-v1
```

El prefijo tiene 40 dígitos hexadecimales, además de `sha256-`. Ambos procesos usan
el mismo archivo de entorno. La unidad del motor configura `EVA_VISUAL_RUNTIME`
en `/var/lib/eva-motor/runtime`; sus cachés no escriben en el checkout protegido.
No copiar contraseñas de usuarios ni credenciales AWS al motor. Su proceso no
necesita acceder a S3: recibe bytes desde Django.

## Activación supervisada

1. Respaldar configuración y registrar SHA del código, pesos y versiones de
   dependencias. Mantener el worker detenido mientras se cambia la configuración.
2. Verificar pesos entrenados para las clases disponibles (maduro sigue pendiente), evaluación independiente y
   recursos disponibles. No usar COCO ni predicciones de tests como modelo final.
3. Revisar/copiar las unidades de `ops/analisis/` al administrador de servicios.
   Ejecutar `systemd-analyze verify` y `systemctl daemon-reload` en Linux. Verificar
   directorios/permisos; no ejecutarlas desde Windows.
4. Iniciar solo `eva-motor`. Comprobar `systemctl is-active eva-motor` y ejecutar
   `python -m visual_service.production` con el entorno privado cargado por el
   administrador, como usuario `eva`. Nunca pasar el token en argumentos ni pegar
   el contenido del archivo de entorno en un informe.
5. Medir un par real autorizado, memoria máxima y tiempo completo. Gunicorn mata
   workers síncronos bloqueados a los 25 s y los reemplaza; el cliente espera como
   máximo 25 s y el worker Django conserva su presupuesto total de 30 s incluyendo
   almacenamiento. Estos límites no garantizan que el modelo sea suficientemente
   rápido: si falla la carga o inferencia, no aumentar límites unilateralmente.
6. Revisar/aprobar explícitamente el perfil experimental y el montaje antes de
   habilitar resultados concluyentes/recomendaciones. Esta factory mantiene la
   comparabilidad deshabilitada; habilitarla requiere un cambio explícito y validado.
   Tener un motor saludable no equivale a criterios aprobados.
7. Reiniciar la web para cargar configuración y arrancar `eva-analisis`. Solo
   habilitar arranque automático tras comprobar el recorrido, sin dejar intentos
   pendientes accidentales. Registrar la evidencia, sin fotos ni secretos en Git.

Si se alcanzó el límite de reinicios, resolver la causa y usar
`systemctl reset-failed eva-motor eva-analisis` antes de un nuevo arranque supervisado.
La salud usa un timeout de 3 s; si el motor aún está cargando, el worker puede
fallar su comprobación. Confirmar primero la disponibilidad del motor y después
iniciar el worker. No vaciar ni modificar estados de la cola para forzar un arranque.

## Recuperación y reversión

- **Motor caído o respuesta inválida:** conservar el intento fallido y su motivo.
  Resolver la causa; reintentar desde el flujo autorizado. Nunca convertirlo en 0 %.
- **Tiempo agotado:** el proceso Django se cancela; el motor síncrono bloqueado es
  reemplazado por Gunicorn. Comprobar salud antes del reintento. Un resultado tardío
  no puede completar un intento vencido por las validaciones existentes.
- **Reinicio durante un análisis:** los intentos vencidos se cierran al reanudar el
  worker; no editar estados por SQL ni recrear servicios para ocultar el fallo.
- **Reversión:** detener primero `eva-analisis`, después `eva-motor`; restaurar el
  entorno anterior con endpoint vacío para desactivar o con la versión anterior
  coherente con sus pesos. Reiniciar la web. No borrar fotos, máscaras, análisis ni
  restaurar una base antigua para revertir únicamente la configuración del motor.
- **OOM o latencia excesiva:** suspender el motor y mantener la demo web operativa.
  Elegir una solución de capacidad explícitamente antes de crear recursos/costos.

## Entrega al QA del grupo

Sin modelo, comprobar que la ausencia del motor se explica y no crea resultados
simulados. Con modelo validado: par completo → análisis → revisión de Cocina →
histórico → evidencia suficiente/insuficiente. Probar token inválido, versión
incorrecta, caída/reinicio, timeout y reintento permitido; comprobar fotos privadas
y ausencia de secretos en respuestas/logs. Pruebas de carga, teléfonos, pantallas
y Figma corresponden a la revisión intensiva. Registrar límites observados, no
promesas de precisión. No activar el JSON experimental como parte de un test.

Referencia del servidor: [factory WSGI](https://gunicorn.org/run/) y
[configuración y timeout](https://gunicorn.org/reference/settings/).

## Verificación de esta preparación

Pasaron 42 pruebas con `manage.py test apps.analisis.test_jobs
apps.analisis.test_motor_visual_adapter visual_service --noinput`, incluidos
autenticación HTTP real en loopback, salud sin inferencia, rechazo de versiones
incompatibles y manejo de fallos de la cola. `git diff --check` sin errores.
Las unidades systemd/Gunicorn quedan pendientes de comprobación en Linux junto
con los pesos y dependencias reales; estas pruebas no validan capacidad de EC2.
