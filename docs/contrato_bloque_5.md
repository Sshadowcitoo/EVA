# Bloque 5: contrato de revisión de César

Depende del PR de César del bloque 4 y de los modelos de Isaac. Mantener apps/analisis para ambos bloques: no crear una segunda app cocina. Esta base no implementa el guardado de revisiones de Isaac ni las vistas/endpoints de Lino.

## Revisión propuesta para Isaac

RevisionAnalisis: UUID, FK protegida al IntentoAnalisis exacto, decisión CONFIRMADO/RECHAZADO/NO_CONCLUYENTE, motivo, autor Cocina, fecha automática, referencia a revisión sustituida y versión de concurrencia. Original técnico inmutable; rectificaciones crean otro evento y conservan el anterior. No vincular una aprobación solo a Servicio.

Servicio propuesto `revisar_resultado(resultado, decision, motivo, usuario, version_esperada)`: verificar autorización y resultado/versión vigentes, transacción y actualización condicional. Rechazo, no concluyente y rectificación exigen motivo. Confirmación inicial puede tener motivo opcional. Doble POST no duplica decisiones; dos revisores reciben conflicto legible sin sobreescritura silenciosa. Nuevo intento necesita su revisión: no hereda aprobación del anterior.

## Regla compartida

`apps.analisis.elegibilidad.evaluar_elegibilidad` recibe datos verificados del servidor, nunca valores del formulario: origen REAL, intento COMPLETADO, configuración histórica aprobada y todos los componentes concluyentes. Una confirmación humana no convierte SIMULADO, fallo, baja confianza o MAYOR_100 en evidencia apta.

`puede_confirmar` exige además evidencia disponible ahora. `apto_historico` requiere decisión CONFIRMADO ligada al mismo intento y validez técnica. La retención posterior no borra una decisión válida anterior ni obliga a tener los bytes para siempre. Si faltan imágenes no se pueden emitir nuevas confirmaciones a ciegas. El bloque de histórico deberá usar esta regla, contar solo el resultado vigente de cada servicio y anonimizar salidas según requisitos.

Persistir la configuración/criterios que realmente se aplicaron; no evaluar la validez histórica contra una configuración mutable posterior. Los resultados parciales no habilitan un total completo de servicio. Si se admite un indicador por componente en el siguiente bloque, su cobertura y exclusiones se documentan aparte.

## Vistas y contrato de interfaz para Lino

namespace analisis: `pendientes_revision` GET /analisis/revision/, `revision_detalle` GET /analisis/revision/<uuid>/ y `revisar` POST /analisis/revision/<uuid>/decidir/. Incluir en apps/analisis/urls.py; César añadirá el include global al integrar ese módulo real. No importar vistas inexistentes en main para aparentar navegación terminada.

La entrada /cuentas/cocina/ y el login de Cocina se redirigen a analisis:pendientes_revision cuando la ruta esté registrada. Mientras tanto conservan la pantalla provisional sin bucles ni links rotos. No cambia la prioridad de Registro para cuentas mixtas ni next seguro.

Contexto de templates/analisis/revision.html: contrato del bloque 4 más `mascaras` [{url,componente,etapa}], `revision_actual` {decision,autor,fecha,motivo}, `decision_url`, `version_esperada`, `puede_confirmar`. Usar URLs privadas del caso. Si no hay endpoint no se muestra un formulario operativo; si no hay criterio/evidencia, Confirmar deshabilitado. El backend vuelve a validar todo: HTML deshabilitado no es autorización.

## Permisos

Cocina recibe view/add_revisionanalisis cuando exista el modelo; ejecutar configurar_roles después de migrar. No dar change/delete genéricos: rectificar mediante el servicio auditado. Registro y Administración solos no heredan Cocina. Validar usuario activo, rol y caso en cada lectura/POST, con CSRF. No abrir captura:imagen a todos para resolver las fotos: Lino entrega un gateway de evidencia específico del análisis con autorización del caso y control de retención.

## Reparto e integración

César publica contratos, configuración, regla de elegibilidad, permisos, navegación e integración; Isaac modelos/servicio de revisión; Lino listado, detalle, formulario/endpoints y gateway; Eduardo casos de concurrencia, permisos, elegibilidad y pruebas de recorrido. Jean tiene disponibilidad confirmada y se encarga de la interfaz de revisión de Cocina del bloque 5, además de la interfaz del bloque 4. Cada uno abre PR; César integra, nadie hace merge directo.

### Propiedad de interfaz: Jean

- Archivos: `templates/analisis/*`, `static/css/analisis.css` y `static/js/analisis.js`. César no vuelve a editarlos sin coordinarlo con Jean; Lino entrega vistas, contextos y URLs, sin pisar sus plantillas.
- Alcance: mapeo Figma, listado/detalle de revisión, comparación de servido/retorno y máscaras, tabla de resultados, acciones confirmar/rechazar/no concluyente, errores, evidencia vencida y estados de guardado. Adaptación móvil/escritorio y accesibilidad. El backend conserva la validación y los permisos.
- Punto de partida: `templates/analisis/revision.html` y estilos ya publicados en PR #33; adaptar la base, no duplicarla ni eliminar trabajo previo sin acuerdo.
- Rama propuesta: `jean-b5-interfaz-cocina`, basada en `cesar-b5-contratos-interfaz`. Su PR depende del #33 y de su interfaz compartida del bloque 4; llevar esos cambios primero y describirlos para evitar duplicar diffs o sobrescribir estilos. Cuando se integren las bases, pasar el PR a main.
- Entrega: referencia/nodos de Figma, capturas en 390x844 y 1440x900, estados vacíos/error/no concluyente y comprobación sobre vistas reales de Lino. Un prototipo o contexto de prueba no acredita conexión real.

Estos cambios preparan la revisión; no afirman que el bloque 5 esté operativo, que Figma se haya medido al 70 %, ni que la IA esté validada. Antes del cierre: combinar ramas, revisar pantallas en 390x844 y 1440x900 frente a Figma, comprobar roles aislados, repetición/concurrencia, conservación de decisiones y fallo/retención de evidencias.
