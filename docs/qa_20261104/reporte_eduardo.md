# QA integral — Eduardo — 4 de noviembre de 2026

**Resultado de esta ronda: NO APTO PARA DEMO como cierre integral del equipo.**
La automatización y la lectura remota verificadas funcionan, pero faltan recorridos
físicos X01–X04 propios, evidencia de privacidad E08 y revisión cruzada. Este dictamen
indica evidencia incompleta; no significa que se haya demostrado una caída general.

Fuente: guía QA integral del equipo del 04/11/2026, leída completa (13 páginas).
Base local: `7615a24`; rama `eduardo-qa-integral-20261104`. La guía identifica ese
commit como despliegue vigente. El navegador verifica comportamiento remoto,
pero no acredita por sí solo el hash del proceso desplegado.

## Resultados ejecutados

| Comprobación | Resultado | Alcance |
|---|---|---|
| `python manage.py check` | Sin incidencias | Base local |
| `python manage.py test --noinput` | 566 descubiertas: 553 aprobadas, 13 omitidas; 399,957 s | Suite anterior a las pruebas nuevas |
| `python manage.py makemigrations --check --dry-run` | Sin cambios | Sin generar migraciones |
| `node --test tests/frontend/*.test.cjs` | 42 aprobadas, 0 fallos/omisiones | 1.462,6872 ms |
| `python manage.py test apps.recomendaciones.test_qa_integral_eduardo --verbosity 2 --noinput` | 5 aprobadas; 2,820 s | Pruebas nuevas ejecutadas aparte |
| Navegador real en HTTPS | 65 observaciones y 22 capturas | Tres roles aislados; lectura y denegaciones |

Las 13 omisiones se confirmaron ejecutando ambos módulos con `--verbosity 2`:
10 de `visual_service.test_onnx_inference` por runtime opcional ausente y tres de
`visual_service.test_paridad_privada` por paquete de diagnóstico privado ausente.
No se instalaron dependencias para convertir omisiones en aprobaciones.

Las cinco regresiones nuevas cubren credenciales vacías/inválidas, ausencia de
escrituras SQL al consultar los cuatro ejemplos, cifras exactas, umbral estricto
de presencia y acceso anónimo/Registro a demostración y foto ilustrativa.

## Evidencia remota

Entorno: `https://18.225.245.214`, certificado aceptado normalmente, sin excepción TLS.
Chrome `157.0.8103.39`, Windows, ejecución headless con perfil temporal separado.
La segunda ronda comenzó el 04/11/2026 a las 18:19:38 de Ecuador (UTC−05).
Ver [JSON completo](../evidencias/qa_20261104/eduardo/navegador_resultados.json).

| Rol | Captura | Catálogo | Análisis | Histórico | Recomendaciones/demo |
|---|---:|---:|---:|---:|---:|
| Registro | 200 | 403 | 403 | 403 | 403 |
| Cocina | 403 | 403 | 200 | 200 | 200 |
| Administración | 403 | 200 | 403 | 200 | 200 |

Se probaron además POST prohibidos por rol con token CSRF válido: todos 403.
Logout por GET devuelve 405. Después de logout por POST, navegar a una ruta
permitida antes de cerrar sesión termina en login para los tres roles.
Las seis rutas protegidas probadas anónimamente también terminan en login.
En el JSON, `status: 0, type: opaqueredirect` es la representación del navegador
para una redirección con `redirect: manual`, **no un código HTTP del servidor**.
La propiedad `destino` confirma la navegación posterior.

Los cuatro ejemplos dieron las mismas cifras con Cocina y Administración:

| Ejemplo | n | Media | Prevalencia | Categoría |
|---|---:|---:|---:|---|
| Poco sobrante | 10 | 4 % | 0 % | Mantener |
| Frecuente | 10 | 30 % | 100 % | Revisar porción |
| Intermedio | 10 | 12 % | 20 % | Realizar prueba controlada |
| Insuficiente | 2 | 35 % | 100 % | Evidencia insuficiente |

Todos conservaron el aviso ficticio. La ausencia de escrituras se comprobó en
SQLite temporal con las vistas reales, no inspeccionando la base compartida AWS.
No se generaron propuestas operativas ni se cambiaron criterios u orígenes.

## Matrices y trazabilidad

- [Matriz propia](matriz_eduardo.csv): E01–E25 y X01–X04; 24 aprobados dentro del
  alcance local/remoto indicado y cinco bloqueados (E08 y los cuatro X completos).
- [Consolidación provisional](consolidado_equipo.csv): 88 registros; incluye los
  cuatro X independientes para cada integrante. Los 59 registros de otros
  integrantes quedan NO EJECUTADO **en esta consolidación** hasta recibir su
  evidencia. No afirma que ellos no hayan hecho su trabajo.
- [Revisión cruzada de Jean](revision_cruzada_jean.csv): parcial y pendiente de
  matriz original, teléfono y marcos de Figma; no está certificada.
- [Pruebas disponibles por caso](trazabilidad_pruebas.json): archivos y métodos
  ejecutados en la suite. Es un índice para repetir y revisar, no una medición de
  cobertura ni afirmación de que cada método de un archivo prueba el mismo ID.
- [Observaciones y bloqueos](incidencias.md) y [pasos restantes](pendientes_manual.md).

El estado APROBADO de un caso local no aprueba hardware, despliegue ni IA real.
La aprobación sigue pendiente de revisión independiente de Jean. Las matrices
conservan ese campo pendiente, sin atribuirle una revisión que no hizo.

## Dispositivos y revisión visual

Capturas a 1440×900, 390×844 y 820×900 para captura de Registro e histórico,
recomendaciones y demo de Cocina/Administración. Ninguna de esas vistas presentó
overflow horizontal global en la medición. Se inspeccionaron visualmente el
histórico móvil y la demo de escritorio/móvil. Las capturas son del viewport,
no prueban todo el documento ni todos los estados de la aplicación.

Pendientes: menú móvil, teclado/zoom al 200 %, cámara Android real, Safari/iPhone
si está disponible, QR físico, vínculo simultáneo PC–teléfono y comparación con
marcos reales de Figma. No se asigna porcentaje de fidelidad visual certificado.

## Cierre y límites

No se verificaron servicios/timers, logs, respaldo/restauración o política física
de S3 desde acceso operativo. La evidencia de Lino e Isaac debe cubrirlos.
No se midió precisión independiente de IA ni comparabilidad física. El origen
SIMULADO y los criterios pendientes deben seguir bloqueando métricas operativas.

No hubo fallos en las pruebas ejecutadas. La observación de caché no demuestra
filtración y sigue abierta para investigación. No hay PR de corrección ni reensayo
de un fallo corregido que se pueda declarar aquí.

Siguiente paso: completar los bloqueos propios, recibir las matrices de Isaac,
Lino y Jean, repetir la revisión cruzada y recalcular el dictamen. No hacer merge
ni despliegue desde esta ronda de QA.
