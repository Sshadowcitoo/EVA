# Plan y evidencia inicial del bloque 4 — 02/11/2026

Responsable: Eduardo. Rama nueva `eduardo-b4-pruebas`, basada en main `1a22306`. Referencias: guías B4/B5 del 1 de noviembre y contrato publicado de César `1e416a5`; dominio de Isaac `50ff172`. No se mezclaron ramas ni se instaló motor IA.

## Primera cobertura

`apps/analisis/test_calculos.py` añade seis casos complementarios al dominio de Isaac: frontera de confianza, porcentaje 100/>100, redondeo, no finitos en todas las entradas, residuo cero con ocultación/incomparabilidad y total vacío/excluido sin cero ficticio. Los umbrales numéricos de pruebas son fixtures, no criterios aprobados para la demo.

La rama de Eduardo no incorpora modelos ni configuración ajenos. Estos tests requieren services/models de Isaac y registro de app de César; no ejecutar sobre main anterior como si las dependencias estuvieran integradas.

## Matriz pendiente

### Ampliación complementaria ya ejecutada

Se añadió `apps/analisis/test_jobs.py` con siete pruebas de dominio: rollback después de crear la primera fila de resultados; fallo al persistir metadatos de máscara; componente duplicado; respuesta antigua después de reclamar reintento; cierre exactamente en el límite de 30 s; rechazo un microsegundo después; selección de retención justo antes/en/después de vencer la foto padre.

El nombre sigue la organización propuesta, pero este módulo **no prueba el worker HTTP ni una cola de ejecución de Lino**. Se crean fotos y máscaras como metadatos sintéticos, sin leer/escribir archivos operativos. Los mocks provocan fallos de BD y controlan el reloj. La transacción de BD no demuestra compensación de bytes en almacenamiento.

En `.revision-b4-validacion`, con las mismas dependencias César/Isaac y copiando el archivo nuevo de Eduardo, se ejecutó:

```powershell
..\.venv\Scripts\python.exe -B manage.py test apps.analisis.test_calculos apps.analisis.test_jobs apps.analisis.test_dominio_analisis --verbosity 1
```

**Resultado 02/11/2026: 53 pruebas aprobadas en 2.512 s**, configuración sin problemas, base temporal creada y eliminada. Desglose: 40 de Isaac, 6 de cálculos y 7 nuevas de Eduardo. La evidencia de 46 pruebas más abajo corresponde a la ejecución anterior.

Se amplió posteriormente a toda la aplicación disponible en esa copia con `..\.venv\Scripts\python.exe -B manage.py test apps.analisis --verbosity 1`: **59 pruebas aprobadas en 6.350 s**, incluidos configuración e interfaz de la base de César; checks sin problemas y BD temporal eliminada. No es la suite global del proyecto ni integración de endpoints todavía ausentes.

Quedan pendientes cliente/worker HTTP, autorización de endpoints, máscara física y reconciliación/retención real, evaluación del motor y revisión de Cocina. La aceptación exactamente en `limite_en` refleja el guardia `>=` del dominio de Isaac; un microsegundo posterior se rechaza. Esto no mide duración de inferencia ni concurrencia simultánea de dos procesos.

| Área | Casos |
|---|---|
| Cliente | Esquema/request_id/versiones/origen, tamaño acotado, PNG real, dimensiones/ROI, componente ajeno/duplicado, URL arbitraria, NaN/infinito |
| Cola/worker | Par apto, fotos exactas/no vencidas, checklist y calidad, clic repetido, dos workers, presupuesto total 30 s desde reclamo, respuesta tardía, reintento con historial |
| Persistencia | Fallo de máscara/BD, compensación y reconciliación sin borrar máscaras válidas como huérfanas |
| Permisos | Cocina autorizada; Registro/Administración solos denegados, evidencia vinculada al caso sin abrir globalmente captura:imagen |
| Retención | Plazo de foto padre, límite y 410, bytes eliminados con metadatos preservados |
| Modelo | REAL/SIMULADO explícito; simulados excluidos; metas y umbrales ratificados con datos independientes |
| UI | Polling autorizado, timeout, pausas, estados conocidos; null no se presenta como 0, máscaras alineadas y leyenda |

No crear test_client/test_jobs de un cliente o worker inexistente. La rama de Lino del B4 no aparecía en la consulta; modelos/dominio de Isaac y contratos/interfaz sí están publicados. La guía antigua asignaba cobertura visual a César; el contrato actualizado confirma disponibilidad de Jean y propiedad de templates/JS/CSS.

## Puerta de cierre

### Primer intento de ejecución

Se creó `.revision-b4-validacion` desde César `1e416a5` y se copiaron models/services/migrations y test_dominio_analisis de Isaac `50ff172`, más test_calculos de Eduardo. El comando `..\.venv\Scripts\python.exe -B manage.py test apps.analisis.test_calculos apps.analisis.test_dominio_analisis --verbosity 1` descubrió **46 pruebas**, pero no las ejecutó: el check de URLs de la base importa `qrcode`, que falta en el entorno local (`ModuleNotFoundError`). La BD temporal fue eliminada. No son 46 pruebas aprobadas ni un fallo de cálculo. Se requiere instalar/verificar las dependencias declaradas del main nuevo antes de repetir. No se omitieron checks ni se sustituyeron rutas para ocultar el bloqueo.

### Repetición aprobada después de preparar dependencias

Eduardo instaló las dependencias declaradas mediante `pip install -r requirements.txt`: se añadieron qrcode 8.2 y colorama 0.4.6 al entorno existente. No se instaló YOLO/OpenCV ni un motor visual. Luego ejecutó desde `.revision-b4-validacion`:

```powershell
..\.venv\Scripts\python.exe manage.py test apps.analisis.test_calculos apps.analisis.test_dominio_analisis --verbosity 1
```

Salida compartida el 02/11/2026: **46 pruebas aprobadas en 5.165 s**, sin problemas detectados por los checks de Django. Base temporal creada y eliminada. Desglose: seis pruebas complementarias de Eduardo y cuarenta de dominio de Isaac. El bloqueo por qrcode del primer intento queda resuelto.

La ejecución valida el código combinado de los commits indicados arriba con fixtures. No acredita llamadas al motor, worker de Lino, endpoints, bytes reales de máscaras, limpieza física, inferencia REAL ni precisión. No se ha ejecutado aún la suite completa integrada del bloque 4, y el check efectuado por el runner no sustituye todas las comprobaciones del cierre.

La copia raíz presentaba un cambio local en apps/captura/tests.py antes de comenzar; se conservó intacto y el bloque 4 se preparó en otro worktree. No se hizo commit ni push en esta preparación.

Check, suite completa, migraciones sin cambios y pruebas frontend si se modifican scripts. Registrar commits, comandos, resultados y fallos. No certificar precisión ni IA real con pruebas numéricas, máscaras sintéticas o adaptador simulado. Motor, datos, criterios y entorno bajo presupuesto requieren evidencia separada de César. El bloque 5 exige además revisión exacta/versionada y elegibilidad, sin heredar aprobaciones entre resultados.
