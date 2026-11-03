# Integración del bloque 4 - 03/11/2026

Base: main a0d86054818d. Entregas combinadas conservando su historial:

- Isaac #31: 196b8d2df46816f8ee7c0bb50205028a46599cfc (modelos, migración y dominio).
- Jean #34: 880f5b76abc53961487f620ee0629a8212112812 (interfaz y pruebas).
- Eduardo #36: cdf65854bb5a3dc142506e24d7390d60e750cca1 (pruebas complementarias y documentación).

## Correcciones de integración

- `total_ponderado` devuelve porcentaje nulo si falta un componente válido. Conserva
  cobertura y exclusiones, pero no publica un subtotal como total de un servicio.
  Se mantiene el cálculo ponderado cuando todos los componentes son válidos.
- Solicitar, reclamar y completar un análisis rechazan fotografías con `eliminada_en`
  informado, aunque la fecha y la marca `vigente` todavía parezcan válidas.
- Pruebas de regresión de las tres transiciones y del cálculo completo/parcial.

## Verificaciones ejecutadas en la combinación

- `python manage.py check`: sin problemas.
- `python manage.py test --noinput`: 270 pruebas aprobadas.
- `python manage.py makemigrations --check --dry-run`: sin cambios.
- `node --test tests/frontend/analisis.test.cjs tests/frontend/camara_captura.test.cjs tests/frontend/captura.test.cjs tests/frontend/vinculacion.test.cjs`: 26 pruebas aprobadas.
- `git diff --check`: limpio.

Las pruebas usan base temporal y fixtures; no se modificó la base de producción.
La migración inicial se aplica al crear la base de pruebas. No se ejecutó migrate
contra la base operativa local ni contra AWS.

## Desbloqueo de Isaac para el bloque 5

La base incorpora modelos y migración `analisis.0001_initial`. Su rama del bloque 5
debe actualizarse con main, conservar esta corrección de total/fotos eliminadas y
resolver cualquier cambio en `services.py` antes de volver a probar. Después se
puede cambiar la base de su PR #38 a main. No se integra el bloque 5 en esta entrega.

## Pendientes: no acreditar el bloque completo

Faltan el cliente del motor, worker, endpoints, gateway autorizado y limpieza de
máscaras de Lino. Sin ellos las plantillas no se publican como rutas funcionales.
El selector de artefactos vencidos no constituye una limpieza de almacenamiento.
También quedan el motor real, aprobación/evaluación de criterios y datos, ensayo
de extremo a extremo y despliegue AWS. No se demuestra precisión de IA con fixtures.

La revisión visual móvil contra Figma sigue pendiente. Antes de conectar las rutas,
verificar en conjunto checklist, existencia física y comparabilidad de las fotos,
URLs de estado exclusivamente del mismo origen y plazo de lectura del cuerpo JSON
(no solo recepción de cabeceras). Los tests frontend actuales no cubren todos esos
casos. Las plantillas y scripts de Jean no se modificaron durante esta integración.
