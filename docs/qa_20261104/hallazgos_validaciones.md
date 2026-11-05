# Auditoría adicional de entradas y mensajes

Fecha: 04/11/2026. Responsable: Eduardo, con diagnóstico local automatizado.
Código funcional revisado: base `7615a24`; rama QA, sin correcciones del producto.

Se ejecutaron **49 observaciones locales** en SQLite temporal con `DEBUG=False`:
captura de servido/retorno, envíos vacíos, histórico, comparación, recomendaciones
y altas de catálogo. Se obtuvieron cuatro respuestas 500, correspondientes a dos
causas reproducidas en dos rutas cada una. No son 49 pruebas aprobadas.

No se enviaron estas entradas límite a AWS. La evidencia del usuario en la demo
y la reproducción local están diferenciadas. No se confirmó el commit del servidor
durante los fallos reportados por el usuario. Cámara real, QR físico, S3 y otros
dispositivos siguen pendientes; este informe no garantiza encontrar todos los
defectos del sistema.

## Inventario confirmado localmente

| ID | Prioridad provisional | Entrada o acción | Observado | Esperado |
|---|---|---|---|---|
| QA-INC-02 | P2 | `numero=2322`, `0` o etiqueta desconocida | 404 genérico en servido y retorno | Mensaje de bandeja/etiqueta no disponible y recuperación dentro del flujo |
| QA-INC-03 | P2 | `numero=` o solo espacios | 200 sin error visible, igual que apertura inicial | Distinguir envío vacío de entrada inicial y pedir un identificador |
| QA-INC-04 | P2 | `numero=²` | 500 / `ValueError` en servido y retorno | Rechazar o normalizar de forma controlada, sin error interno |
| QA-INC-05 | P2 | Número de 5000 dígitos enviado por petición directa local | 500 / `ValueError` en servido y retorno | Límite de longitud/rango también en servidor; respuesta controlada |
| QA-INC-06 | P2 | POST vacío para confirmar bandeja libre o guardar foto | Formulario no enlazado al envío (`is_bound=False`), sin errores | Campos obligatorios con errores de servidor, sin simular apertura inicial |
| QA-INC-07 | P3 | `numero=abc` | Mensaje correcto, pero el campo vuelve vacío | Conservar la entrada inválida para corregirla |
| QA-INC-08 | P3 | Abrir identificación del servido, sin búsqueda | Ayuda dice «Busca una bandeja pendiente» y promete foto inicial | Diferenciar identificar una bandeja para servido de buscar un retorno pendiente |

Las prioridades son propuestas para revisión, no una decisión final de cierre.
Ningún hallazgo tiene aún PR de corrección ni repetición sobre código corregido.
No se observó creación de servicios causada por estas entradas: el diagnóstico
comparó el número de servicios antes y después de cada petición. Esto no equivale
a una auditoría completa de todos los efectos de base de datos.

## Reproducción y causa identificada

Rutas comunes: `/captura/bandeja/` y `/captura/retorno/`, con usuario local de rol
Registro. Los valores de prueba quedan definidos en
`ops/qa/auditar_validaciones.py`; el JSON conserva cada resultado.

**QA-INC-02 y QA-INC-03.** Coinciden con lo reportado por Eduardo en la demo.
`_localizar_bandeja` trata vacío/espacios como primera apertura y lanza `Http404`
para un número o etiqueta no encontrado. Un identificador inexistente debe seguir
sin permitir una operación; la incidencia es la falta de una respuesta útil.

**QA-INC-04.** `str.isdigit()` acepta `²`, pero `int('²')` lanza `ValueError`.
La excepción no está controlada. Este caso cabe dentro del límite de 64 caracteres
del campo y no depende de saltarse ese límite del navegador.

**QA-INC-05.** El campo HTML limita a 64 caracteres; la petición de 5000 dígitos
se hizo exclusivamente en local para probar la validación del servidor. La
conversión `int()` supera el límite de conversión decimal de Python y lanza
`ValueError`. Una entrada de 64 dígitos devuelve 404 en este entorno; no se declara
que esa variante produzca 500. No ejecutar la entrada larga en la demo compartida.

**QA-INC-06.** `request.POST or None` convierte un POST vacío en formulario no
enlazado. Se reprodujo con bandeja libre y con un servicio local pendiente de foto
servido. No se guardó una foto ni se aceptaron datos inválidos. En la interfaz
normal, `required` o JavaScript pueden impedir el envío; el caso prueba servidor
mediante petición directa, sin enforcement CSRF para aislar validación de campos.
Esto no demuestra un bypass de CSRF ni de permisos. Retorno presenta el mismo
patrón en código, pero no se declara reproducido ese POST en esta ronda.

**QA-INC-07 y QA-INC-08.** Confirmados en el HTML de respuesta. El input no tiene
valor enviado ligado al contexto; la ayuda de búsqueda se usa sin distinguir
`es_retorno`. La confusión entre servido y retorno no era solo del usuario: ese
texto puede inducirla. La revisión de JavaScript no encontró código que restaure
el valor de búsqueda después de recibir la página.

Área propuesta: Lino para manejo HTTP/validaciones; Jean para textos, conservación
de entrada y presentación. Eduardo conserva evidencia y verifica tras corregir.
Asignación definitiva y revisión cruzada pendientes de coordinación del equipo.

## Controles que sí respondieron adecuadamente

- Letras, negativos y decimales muestran «solo puede contener dígitos».
- Número y etiqueta a la vez muestran una indicación de usar solo uno.
- Bandeja existente libre en retorno explica que no tiene servicio pendiente.
- Histórico y recomendaciones rechazan páginas inválidas, fecha imposible,
  fechas/horas invertidas y plato desconocido con 400 y errores de formulario.
- Comparación sin fechas muestra errores obligatorios.
- Altas vacías de plato, componente y porción muestran errores obligatorios.
- El alta básica de servicio vacía muestra errores de plato y porción.
- Evaluación sin campos responde 400; escenario de demo desconocido responde
  404 por diseño. No se cuentan automáticamente como defectos estos estados.

## Evidencia y repetición

- [49 observaciones JSON](../evidencias/qa_20261104/diagnostico_validaciones_local.json).
- Diagnóstico: `ops/qa/auditar_validaciones.py`.
- Reportes iniciales y variantes del usuario: [registro de incidencias](incidencias.md).

Repetir desde la carpeta del worktree, con el entorno existente:

```powershell
..\.venv\Scripts\python.exe -B ops/qa/auditar_validaciones.py
```

Crea y destruye una base de pruebas; no usa la base de la demo ni toca AWS. El
script registra observaciones incluso si el producto responde 500: su terminación
correcta no significa ausencia de fallos. Repetir después de corregir y comparar
los resultados con las expectativas de cada incidencia antes de cerrarla.
