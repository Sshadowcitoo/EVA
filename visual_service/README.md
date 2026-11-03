# visual_service

Motor separado YOLO/Pillow y herramientas del piloto. Incluye dataset, exportación/
entrenamiento, inferencia, endpoint interno y métricas contra máscaras manuales.
No contiene pesos, anotaciones ni resultados de precisión real. No está activado.

Leer [preparación, contexto y límites](../docs/motor_contexto_piloto.md).
Para el arranque privado, ver [operación y recuperación](../docs/operacion_motor.md).
El servidor incorporado solo se usa en desarrollo local; antes de desplegar se
verifican capacidad, tiempo total, autenticación, geometría y criterios aprobados.

```powershell
python -m unittest visual_service.test_dataset visual_service.test_inference visual_service.test_evaluation
```
