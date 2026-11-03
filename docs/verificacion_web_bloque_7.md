# Verificación HTTP e interfaz del bloque 7 conectado

Base exacta: `35906145a6b68497682657ad5b995b118d14f796`, rama
`dominio-recomendaciones-bloque-7`. Rama de entrega:
`verificacion-recomendaciones-bloque-7`; PR contra la rama de dominio.
No se hace merge, despliegue ni migración de una base operativa.

## Cambios y hallazgos

Se añaden diez pruebas HTTP con ORM real en
`apps/recomendaciones/test_web_orm_verificacion.py`. Ninguna sustituye funciones de
`apps.recomendaciones.services`. Se reutiliza la fábrica ORM del histórico y, solo
para alcanzar estados positivos hipotéticos de prueba, el helper de contexto de
los tests del dominio. No se importan DTO de fixtures como respuestas del backend.

Tres ajustes propios de la interfaz:

- Los 409 muestran el motivo concreto del dominio, escapado en HTML. Generar con
  evidencia insuficiente informa esa causa; ya no afirma incorrectamente que toda
  respuesta 409 significa que cambió una versión. Se mantiene el borrador, el
  bloqueo y la necesidad de refrescar antes de decidir otra vez.
- El detalle de prueba informa cuando su evidencia está desactualizada y cuando
  no está habilitado evaluar, para revisar la aceptación vinculada. Las mediciones
  e historial anteriores se conservan y no se habilita una acción prohibida.

- En respuestas con error, la operación sin confirmar aparece primero. Los mensajes
  de éxito que queden en sesión de solicitudes anteriores se agrupan en un bloque
  colapsado «Avisos de operaciones anteriores», sin presentarlos como éxito del
  borrador rechazado. El test HTTP verifica este orden con avisos reales de sesión.

No se modifican contratos, DTO, modelos, migraciones, reglas, criterios, selectores,
servicios ni configuración global. Los parámetros operativos siguen sin aprobar;
el contexto histórico sigue ausente.

## Recorridos HTTP comprobados

1. Evaluar dos veces con criterios operativos pendientes reutiliza la evaluación;
   al recuperarla sigue INSUFICIENTE, sin propuesta ni habilitación de generación.
   La intensidad descriptiva puede existir; prevalencia/t quedan no disponibles.
2. Treinta y una evaluaciones creadas por HTTP verifican filtros, límite inclusivo
   de fechas, categoría/decisión/suficiencia, paginación y contadores del conjunto
   completo. Códigos, origen o páginas inválidos devuelven 400 sin escrituras.
3. Una revisión posterior vuelve obsoleto el caso anterior, bloquea generación con
   409 y permite una evaluación nueva; el snapshot anterior permanece idéntico.
4. Fechas/versiones inválidas y UUID inexistentes no fabrican registros.
5. Cocina, Registro y staff sin rol se comprueban sobre recursos ORM existentes,
   en las cuatro lecturas y cinco escrituras. Cocina solo consulta; los intentos
   no autorizados no cambian los conteos de ninguna tabla del módulo.
6. Client(enforce_csrf_checks=True) rechaza las cinco escrituras sin token y permite
   recorrerlas con token válido y Administración; no se confía en ocultar botones.
7. GET repetido en los recursos existentes no escribe; las acciones POST rechazan
   GET y las respuestas de lectura tienen caché privada/no-store.
8. Doble envío de decisión del mismo actor no duplica. Un segundo operador con
   versión antigua obtiene 409, conserva texto escapado y versión enviada; el
   nuevo estado vigente se muestra sin sobrescritura. La corrección con versión
   actual añade una decisión enlazada a la anterior, visible en el historial.
9. Doble creación de prueba no duplica. Reenviar una evaluación con versión vieja
   produce 409; una reevaluación explícita con versión actual agrega resultado.
   Versiones 1 y 2 y el snapshot previo se conservan. Sustituir la aceptación exacta
   impide seguir evaluando la prueba original, aunque la decisión nueva sea ACEPTADA.
10. Justificaciones vacías/excesivas, responsable sin rol y periodos superpuestos
    no alteran el historial ni crean pruebas. Cambiar criterios/contexto invalida
    decisiones nuevas con 409 y conserva el borrador y la decisión histórica.

## Separación entre operación y escenarios hipotéticos

`OperacionRealHTTPTests` utiliza la configuración actual sin aprobar ni contexto
inventado. Confirma que la insuficiencia real se guarda y se muestra sin ocultarla.

`EscenariosHipoteticosHTTPTests` necesita alcanzar recomendaciones, decisiones y
pruebas para verificar su protocolo HTTP. Solo dentro de esos tests usa CONFIG y
PRESENCIA del dominio y su helper de contexto hipotético. Services, permisos,
transacciones y persistencia siguen siendo reales. No aprueba esos valores para
operación ni modifica settings del proyecto. El escenario de vigencia restaura
criterios sin aprobar/contexto ausente antes de comprobar el 409 y exportar capturas.

El historial de decisiones se comprueba en HTML y en ORM. Las versiones anteriores
**de resultados de pruebas** se verifican en ORM; el contrato v1 de DetallePrueba
expone el último resultado y la lista de pruebas del caso, no un navegador de todas
las versiones anteriores. No se amplía ese DTO para simular una pantalla de historial
que el contrato no proporciona.

## Comandos y resultados

Entorno virtual propio; SQLite de desarrollo local y base temporal de Django.
Se confirmó la aplicación local de `recomendaciones.0001_initial` con migrate.

| Comando | Resultado |
| --- | --- |
| python manage.py migrate --noinput | Migración de recomendaciones aplicada en SQLite local |
| python manage.py check | Sin incidencias |
| python manage.py makemigrations --check --dry-run | No changes detected |
| python manage.py test apps.recomendaciones.test_web_orm_verificacion | 10 pruebas aprobadas |
| python manage.py test apps.recomendaciones | 70 pruebas aprobadas |
| python manage.py test | 480 pruebas aprobadas |
| node --test tests/frontend/*.test.cjs | 42 pruebas aprobadas |

Los tests 503 existentes siguen usando dobles explícitos para probar la traducción
de fallos; no son los recorridos de conexión. Los tests nuevos no sustituyen services.
El doble envío sin JavaScript se verifica mediante POST reales del cliente Django;
el bloqueo preventivo con JavaScript conserva sus pruebas frontend. No se acredita
un despliegue ni inferencia con imágenes reales.

## Capturas de escritorio y móvil

Para reproducir la exportación HTML opcional de los ensayos locales:

```bash
EVA_VERIFY_VISUAL_DIR=/tmp/verify-b7-html python manage.py test apps.recomendaciones.test_web_orm_verificacion
```

Las capturas proceden de respuestas de las vistas globales con ORM real y datos de
prueba sintéticos, no de funciones services reemplazadas ni de datos operativos.
Las dos últimas filas representan casos históricos creados con hipótesis técnicas
exclusivas de test; al capturarlos, los criterios actuales vuelven a estar sin aprobar.
No se deben presentar sus snapshots anteriores como una recomendación operativa válida.

Chromium revisó 7 estados a 1440x900 y 390x844 (14 combinaciones), sin desbordamiento
horizontal global, identificadores DOM duplicados, campos sin etiqueta ni errores
JavaScript. Las tablas mantienen su desplazamiento local. Capturas de página completa:
su altura puede superar la del viewport. Se inspeccionó el renderizado en ambos tamaños.

| Recorrido / estado | Escritorio | Móvil |
| --- | --- | --- |
| Listado Administración, criterios pendientes | [1440](evidencias/verificacion_bloque_7/lista-operativa-1440.jpg) | [390](evidencias/verificacion_bloque_7/lista-operativa-390.jpg) |
| Listado Cocina, sin acciones administrativas | [1440](evidencias/verificacion_bloque_7/cocina-operativa-1440.jpg) | [390](evidencias/verificacion_bloque_7/cocina-operativa-390.jpg) |
| Evidencia insuficiente guardada | [1440](evidencias/verificacion_bloque_7/insuficiente-operativa-1440.jpg) | [390](evidencias/verificacion_bloque_7/insuficiente-operativa-390.jpg) |
| Generación rechazada por insuficiencia | [1440](evidencias/verificacion_bloque_7/generacion-rechazada-1440.jpg) | [390](evidencias/verificacion_bloque_7/generacion-rechazada-390.jpg) |
| Revisión nueva, snapshot obsoleto conservado | [1440](evidencias/verificacion_bloque_7/evidencia-obsoleta-1440.jpg) | [390](evidencias/verificacion_bloque_7/evidencia-obsoleta-390.jpg) |
| Conflicto sobre historial hipotético, criterios actuales sin aprobar | [1440](evidencias/verificacion_bloque_7/conflicto-historico-hipotetico-1440.jpg) | [390](evidencias/verificacion_bloque_7/conflicto-historico-hipotetico-390.jpg) |
| Prueba histórica hipotética, no evaluable y bloqueada | [1440](evidencias/verificacion_bloque_7/prueba-historica-no-evaluable-1440.jpg) | [390](evidencias/verificacion_bloque_7/prueba-historica-no-evaluable-390.jpg) |

## Pendientes explícitos

- Aprobar criterios/reglas con sustento y definir/persistir contexto histórico real.
  Mientras falten, mostrar insuficiencia y bloquear propuestas sigue siendo correcto.
- Evaluar el motor con fotografías reales y validar su precisión.
- Figma sigue pendiente hasta disponer de acceso funcional o exportaciones; no se
  acreditan node-id ni el objetivo aproximado del 70 %.
- No se realiza despliegue AWS ni se modifica una base operativa.
