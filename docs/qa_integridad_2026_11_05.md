# Revisión de integridad tras los informes de QA

Base revisada: `7615a24be096128564008201de4a527bfd5d37e7`.
Cambios locales en `qa-datos-integridad`; sin merge ni despliegue.

## Hallazgos reproducidos y corregidos

- Isaac H03: el formulario aceptaba platos sin composición y `Servicio.registrar`
  creaba servicios sin componentes. Ahora el formulario exige un componente activo
  y el dominio rechaza tanto el registro básico como el asociado a bandeja si no
  existe composición activa. No se modifican servicios históricos ni sus instantáneas.
- Isaac H04: reproducido con dos conexiones concurrentes y una base SQLite temporal
  en archivo, sincronizando ambas altas antes de crear el servicio. Antes: una alta
  correcta y `OperationalError: database is locked`; después: una alta correcta y
  `ValidationError` con indicación de reintentar. En ambos casos se conserva un solo
  servicio y una asignación abierta. No se demostró corrupción de datos.
  La traducción solo reconoce códigos SQLite BUSY/LOCKED, después del rollback;
  otros errores operativos siguen propagándose. No hay reintentos automáticos.

## Pruebas de regresión

`apps.catalogo.test_qa_integridad` cubre alta y edición sin composición, componentes
inactivos, ausencia de filas parciales, conservación de instantáneas, rollback ante
bloqueo y propagación de otros errores de base de datos.

Verificación dirigida: 92 pruebas Django aprobadas. Suite completa: 571 pruebas,
568 aprobadas y 3 omitidas; sin fallos. Frontend: 42 aprobadas.
La primera ejecución completa tuvo siete errores WinError 10013 por bloqueo de
conexiones locales; se repitió con permiso de red y terminó correctamente.
`makemigrations --check --dry-run`: sin cambios. `git diff --check`: sin incidencias.

## Pendientes y límites

- El test de filtros reportado por Lino pasa aquí con Python 3.13. No se dispone
  de Python 3.14 en este equipo; hace falta su traceback completo para reproducir
  exactamente el fallo. No se cambió el contrato de filtros por una causa supuesta.
- Bandeja 7: falta verificar el servicio y su trazabilidad en AWS por identificador
  o lote; una bandeja libre o un par incompleto ausente de Cocina no demuestra
  pérdida de datos. No se modificaron registros de producción.
- Cámara física, cierre de pestaña/desconexión, permisos S3, restauración de respaldo
  y revisión visual/Figma siguen necesitando evidencia manual o del entorno objetivo.
- El equipo B tiene asignados validación HTTP, formularios de captura, navegación,
  plantillas y sus regresiones. No se han tocado esos archivos en esta entrega.
- Ninguna de estas pruebas certifica precisión independiente del modelo visual.

## Compatibilidad con PR #62

Revisado el PR #62 en `753d133495d44d7d15de55064218867f17614582`; se aplicó su diff únicamente en
el árbol de trabajo para verificarlo junto con las correcciones de dominio.
No se hizo merge, commit, push ni despliegue. No hay archivos de dominio
compartidos entre ambas entregas.

Verificación conjunta: 214 pruebas de captura y catálogo aprobadas, 42 de
frontend aprobadas y migraciones sin cambios. Las pruebas físicas de cámara
y QR siguen pendientes.

## Actualización del 6 de noviembre

Los PR #62 y #63 fueron integrados y desplegados. El estado actual y las pruebas
físicas y de respaldo se detallan en [el cierre de QA](qa_cierre_2026_11_06.md).
Las notas anteriores describen el estado de cada verificación antes de integrar.
