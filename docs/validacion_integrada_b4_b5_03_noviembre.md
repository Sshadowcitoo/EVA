# Validación integrada B4/B5 — 3 de noviembre de 2026

Responsable: Eduardo. Rama: `eduardo-validacion-integrada-b4-b5`.
Base exacta: `24c305d46db24775d0bbb426f65771453d1ba022` de origin/main.
Se creó `.revision-03-noviembre` desde esa base, sin merge y sin alterar las ramas anteriores.

Entorno: Python 3.13.5, Django 5.2.18 y Pillow 12.3.0, entorno virtual existente de EVA. Sin nuevas instalaciones. No se aplicaron migraciones a una BD operativa ni se usaron recursos AWS. No se consultaron credenciales o datos reales.

## Estado que sustituye pendientes antiguos

Las entregas de Lino B4/B5, dominio de revisión de Isaac e interfaces ya están incorporadas. Existen cliente HTTP, supervisor con proceso hijo, cola, persistencia/retención de máscaras y gateways autorizados. Cocina tiene listado/detalle y decisiones con versión e historial. Las pruebas y documentación aisladas de Eduardo del 2 de noviembre se conservan como antecedentes, no como lista vigente de funciones ausentes.

No se afirma que esté disponible un modelo REAL evaluado, aprobados los criterios de confianza/comparabilidad o desplegado el worker. Histórico y recomendaciones también están en esta base, pero su aceptación académica y alcance no se redefinen por esta revisión de B4/B5.

## Comandos de verificación

Desde `.revision-03-noviembre`:

```powershell
..\.venv\Scripts\python.exe -B manage.py check
..\.venv\Scripts\python.exe -B manage.py test --noinput
..\.venv\Scripts\python.exe -B manage.py makemigrations --check --dry-run
node --test tests/frontend/*.test.cjs
..\.venv\Scripts\python.exe -B ops/analisis/smoke_integracion.py
```

La suite global incluye las aplicaciones posteriores y no debe interpretarse como un número de casos exclusivos de B4/B5. Se registran los resultados finales después de cada ejecución, sin convertir pruebas detenidas en aprobaciones.

### Resultados ejecutados en esta revisión

| Comprobación | Resultado real |
|---|---|
| `manage.py check` | System check identified no issues |
| `manage.py test --noinput` | **480 pruebas aprobadas en 271.153 s**, base temporal creada y eliminada |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `node --test tests/frontend/*.test.cjs` | **42 aprobadas**, ninguna fallida/omitida; 25290.1692 ms |

La ejecución completa se realizó en sandbox. Los mensajes EVA de fallos simulados durante tests no equivalen a fallos de suite; el resultado final fue OK. La duración local observada no es una medida de latencia del motor REAL. No se actualizó ninguna base operativa mediante migrate.

## Matriz de cobertura inspeccionada

| Requisito | Implementación de prueba disponible | Alcance y límite |
|---|---|---|
| Cálculos, nulos, >100, cobertura | test_calculos, test_dominio_analisis, test_integracion_b4 | Datos/áreas conocidas; no precisión de un modelo |
| Cliente, autenticación y respuesta | test_integracion_lino_b4 | HTTP de loopback y máscaras sintéticas; sin motor REAL |
| Worker y timeout | test_integracion_lino_b4; smoke_integracion | Supervisor/proceso hijo reales y fixtures; no rendimiento de inferencia REAL |
| Persistencia y reintentos | test_jobs, test_dominio_analisis, test_integracion_lino_b4 | Transacciones, cola, fallos y compensación controlados |
| Fotos/máscaras privadas y retención | test_integracion_lino_b4, test_web_revision | Pertenencia al caso, 410, archivos alterados y limpieza temporal; no auditoría del bucket operativo |
| Revisión/rectificación | test_dominio_revision y test_web_revision | Autoría, motivos, idempotencia, versión obsoleta e historia; bloqueo SQLite no certifica otro motor |
| Elegibilidad | test_elegibilidad, test_elegibilidad_complementaria, test_dominio_revision | REAL/validez/criterios/revisión exacta; fixtures de criterios no aprueban política real |
| Roles y CSRF | test_web_revision y test_integracion_lino_b4 | Roles aislados y peticiones a rutas reales |
| Interfaz | test_interfaz*, tests/frontend/*.test.cjs | HTML/DOM/red simulada; no comparación visual completa de Figma |

No se añadieron pruebas redundantes que copien la implementación para inflar métricas. Nuevos cambios o fallos deberán incorporar regresiones dirigidas.

## Ensayo aislado del recorrido

El script existente levanta un motor HTTP SIMULADO en 127.0.0.1 y crea SQLite/fotos/máscaras en TemporaryDirectory. Ejecuta solicitud HTTP, cola, supervisor con hijo Django, respuesta, persistencia, gateway privado, bloqueo de Confirmar para SIMULADO y rechazo guardado. No lanza entrenamiento, servidor público ni AWS.

Primer intento de esta revisión: la etapa `preparar` superó el timeout de 30 s del script mientras la suite global estaba activa. Se detuvo **antes** de ejecutar el análisis. No prueba un incumplimiento del presupuesto de inferencia ni se considera aprobado. No se cambió el límite del worker ni se omitieron checks para ocultarlo.

Segundo intento, sin suite concurrente: **aprobado, exit code 0**. El script devolvió `origen=SIMULADO`, `worker_real=true`, `motor_http_fixture=true`, `estado=COMPLETADO`, `resultados=3`, `revision=RECHAZADO`, `confirmacion_simulada_bloqueada=true` y `gateway_privado=true`. El POST de confirmación produjo 400 deliberadamente: se verificó que SIMULADO no se convirtiera en evidencia REAL confirmada. El rechazo con motivo sí se guardó. La base, archivos y token de fixture fueron temporales; no se alteraron límites, credenciales o configuración del servidor real.

Con este ensayo se acredita el recorrido técnico local con supervisor/proceso hijo y motor HTTP de prueba. No se certifica segmentación de alimentos, calidad de máscaras reales, precisión o rendimiento de un modelo REAL, ni conectividad de AWS.

## Evidencia externa pendiente

- Motor REAL, pesos, datos independientes y aprobación de criterios por componente/versiones: César y equipo.
- Ensayo autorizado del servidor/worker, permisos IAM/S3 y eliminación física/versiones/copias; esta ejecución local no lo certifica.
- Revisión de la UI en 390×844 y 1440×900 con acceso al Figma editable/exportaciones autorizadas. El entorno no dispone de Playwright ni herramienta de navegador; no se instalaron herramientas nuevas para inventar evidencia. No se certifica el 70 % de similitud.
- Teléfono/cámara/QR/HTTPS con dispositivo real, cuando corresponda; no se prueba con un navegador simulado.

El usuario no necesita repetir comandos locales que el asistente ejecute con éxito. Si se requiere acceso a Figma, dispositivo o decisiones de criterios, se solicitará explícitamente. Los cambios se entregan mediante PR: solo César integra.

## Entrega preparada

Se corrige README y se agregan avisos de estado a los planes B4/B5, conservando los resultados históricos. No se modificaron modelos, migraciones, motor, worker ni las interfaces de otros integrantes. La revisión no reabre los bloques 6/7 ni altera sus criterios. No se añadieron fixtures a la demo ni se aprobaron umbrales por conveniencia.

Próxima acción de equipo: revisar este PR de documentación/evidencias y decidir las pruebas operativas externas. Eduardo ya no depende de que Lino/Isaac publiquen B4/B5 para repetir la suite local; sí depende de César/equipo para motor REAL evaluado, acceso autorizado al despliegue y criterios, y de una persona con Figma/teléfono para las comprobaciones visuales/físicas pendientes.
