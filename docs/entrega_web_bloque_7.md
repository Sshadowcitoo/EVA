# Entrega web del bloque 7 (registro inicial)

Estado posterior: dominio y rutas globales ya conectados. La comprobación actual
se documenta en [verificación HTTP con ORM real](verificacion_web_bloque_7.md).
Lo siguiente conserva el registro de la entrega inicial del PR #47.

Rama: interfaz-recomendaciones-bloque-7.
Base exacta: 061f1fef62e878d40403c28023f162d90ca947e2,
base-recomendaciones-bloque-7, sobre main fb1e0684e48c80efbf97d4edf5aed90a9412cbfe.
El PR apunta a la rama base mientras siga abierta. Sin merge ni despliegue.
Estado: interfaz preparada; el dominio/persistencia del bloque 7 todavía está pendiente.

## Archivos y contrato consumido

- apps/recomendaciones/forms.py, views.py, urls.py y presenters.py.
- templates/recomendaciones/: base, lista, detalle, prueba y parciales de campos/evidencia.
- static/css/recomendaciones.css y static/js/recomendaciones.js.
- apps/recomendaciones/test_web_recomendaciones.py y tests/frontend/recomendaciones.test.cjs.
- Documentación de interfaz/entrega y capturas de ensayo.

Se consumen los cuatro normalizadores y las diez operaciones de datos de services:
opciones_recomendaciones, consultar_recomendaciones, evaluar_evidencia,
obtener_evaluacion, generar_recomendacion, obtener_recomendacion,
decidir_recomendacion, registrar_prueba, obtener_prueba y evaluar_prueba.
Se mantiene el import del módulo y la llamada por atributo.

No se modifican contratos, filtros de dominio, fixtures, modelos, migraciones,
selectores, configuración global, navegación común ni archivos de otros bloques.
Las fixtures se importan únicamente en los tests. Los presenters solo traducen
etiquetas y serializan el snapshot para presentarlo; no recalculan indicadores ni reglas.

## Integración compartida pendiente

1. Añadir path('recomendaciones/', include('apps.recomendaciones.urls')) en config/urls.py.
2. Añadir enlace recomendaciones:lista en navegación común para Cocina/Administración.
   No conceder acceso a Registro solo ni ampliar acceso a fotografías por este enlace.
3. Conectar el dominio manteniendo el contrato v1 y aplicar SUS migraciones únicamente
   a la base local correspondiente antes de probar el recorrido conjunto.
4. Repetir la suite conjunta y tres recorridos sin mocks: evaluación/generación,
   decisión justificada con conflicto/idempotencia y prueba controlada con comparación
   o NO_EVALUABLE. Esta entrega aislada no acredita persistencia ni suficiencia real.

## Verificación ejecutada

Entorno virtual aislado, dependencias existentes, SQLite temporal de pruebas.

| Comando | Resultado |
| --- | --- |
| python manage.py check | Sin incidencias |
| python manage.py test apps.recomendaciones | 36 pruebas aprobadas (7 de contrato, 29 web) |
| python manage.py test | 446 pruebas aprobadas |
| python manage.py makemigrations --check --dry-run | No changes detected |
| node --test tests/frontend/recomendaciones.test.cjs | 3 pruebas aprobadas |
| node --test tests/frontend/*.test.cjs | 42 pruebas aprobadas |

Las pruebas web sustituyen cada servicio de datos explícitamente, incluidos los getters
para los escenarios 503; no dependen de que el dominio continúe sin implementar.
Cubren roles aislados/múltiples, staff, inactivo, anónimo/superusuario, métodos sin
escritura GET, CSRF en las cinco operaciones POST, caché privada, capacidades,
filtros/paginación, etiquetas DOM únicas, ausencia de datos, insuficiencia/simulación,
obsolescencia, justificación obligatoria, periodos/responsables inválidos, borradores
escapados/conservados, conflictos, reenvío al backend y estados de pruebas.

Los dobles no prueban idempotencia, auditoría o concurrencia persistida: esas
propiedades siguen siendo responsabilidad del dominio y de la futura prueba conjunta.
La configuración y cifras de fixtures NO son parámetros aprobados para la operación.

## Evidencia visual

Se renderizaron las vistas Django con RequestFactory y dobles explícitos en un proceso
de ensayo separado. Chromium revisó 13 estados en 1440x900 y 390x844: 26 combinaciones,
sin desbordamiento horizontal global ni errores JavaScript. Las tablas conservan su
propio desplazamiento. Se adjuntan 14 capturas de página completa, de contenido sintético;
el alto final puede superar el viewport indicado.

| Pantalla/estado | Escritorio | Móvil |
| --- | --- | --- |
| Listado y evaluación | [1440x900](evidencias/bloque_7/lista-1440.jpg) | [390x844](evidencias/bloque_7/lista-390.jpg) |
| Evidencia insuficiente | [1440x900](evidencias/bloque_7/insuficiente-1440.jpg) | [390x844](evidencias/bloque_7/insuficiente-390.jpg) |
| Suficiente, sin propuesta | [1440x900](evidencias/bloque_7/sin_propuesta-1440.jpg) | [390x844](evidencias/bloque_7/sin_propuesta-390.jpg) |
| Decisión e inscripción de prueba | [1440x900](evidencias/bloque_7/aceptada-1440.jpg) | [390x844](evidencias/bloque_7/aceptada-390.jpg) |
| Prueba no evaluable | [1440x900](evidencias/bloque_7/prueba-no-evaluable-1440.jpg) | [390x844](evidencias/bloque_7/prueba-no-evaluable-390.jpg) |
| Backend pendiente | [1440x900](evidencias/bloque_7/pendiente-1440.jpg) | [390x844](evidencias/bloque_7/pendiente-390.jpg) |
| Conflicto y borrador | [1440x900](evidencias/bloque_7/conflicto-1440.jpg) | [390x844](evidencias/bloque_7/conflicto-390.jpg) |

También se ejercitaron listado vacío, Cocina sin acciones administrativas, criterios
pendientes, evidencia obsoleta y pruebas registrada/evaluada. Figma permanece PENDIENTE
hasta disponer de acceso o exportaciones; no se inventan node-id ni semejanza medida.
