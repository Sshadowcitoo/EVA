# Demostración separada de porcentajes y recomendaciones

Ruta: `/recomendaciones/demostracion/`. Disponible para Cocina y Administración; sin escrituras y solo GET. Acceso desde Recomendaciones → Demostración.

## Alcance

Los porcentajes se calculan con áreas preparadas (10 000 px² iniciales), usando `apps.analisis.services.evaluar_componente`. La media y prevalencia usan `apps.historico.indicadores.calcular`; la suficiencia y categoría usan las funciones de `apps.recomendaciones.selectors`. Se reutiliza el perfil experimental aprobado de `ops/analisis/criterios_piloto.propuesta.json`, sin modificar su activación ni los settings operativos.

Cuatro escenarios: poco sobrante (Mantener), sobrante frecuente (Revisar porción), intermedio (Prueba controlada) y muestra insuficiente (ninguna recomendación). Los tres primeros suponen diez ejemplos, cinco por cada uno de dos días completos, dos lotes, revisión y contexto comparables y confianza 0,90. Son supuestos didácticos, no observaciones del restaurante ni predicciones del modelo. No se guardan servicios, evaluaciones, decisiones ni recomendaciones en el ORM.

Una foto privada opcional se selecciona exclusivamente mediante `EVA_DEMO_SERVICIO_ID` en el servidor. El endpoint no permite elegir otro servicio por URL; valida vigencia, hash y bytes de la foto. Se identifica como imagen ilustrativa y no se atribuyen a ella las cifras preparadas. Si caduca por retención, deja de estar disponible; no se evade la limpieza.

## Qué se valida y qué sigue pendiente

Se verifican el cálculo de porcentajes, los límites de presencia, la selección de reglas, la insuficiencia y la separación de datos. Esto no certifica la segmentación ni la comparabilidad física de fotografías reales. El modelo continúa generando resultados simulados no concluyentes y las recomendaciones operativas permanecen protegidas.

El diagnóstico de las 79 fuentes de entrenamiento frente a anotaciones asistidas es descriptivo; no es prueba independiente. No convierte IoU en precisión generalizable ni autoriza resultados operativos.

## Retiro de maduro

El catálogo nuevo incluye seco de pollo con arroz y pollo. La migración `catalogo.0002_retirar_maduro_piloto` desactiva la relación anterior sin tocar instantáneas de servicios, análisis o revisiones. Desactiva el componente solo si ningún otro plato activo lo utiliza. No elimina registros históricos ni altera las clases heredadas que permiten leerlos. La reversión del esquema no reactiva datos de catálogo automáticamente.

## Presentación

Abrir la sección Demostración, elegir cada escenario y explicar servido/retorno, porcentaje de área, media y prevalencia. Mostrar que el ejemplo insuficiente no produce recomendación. Para la inferencia auténtica, abrir por separado un análisis del motor y explicar sus máscaras y limitaciones. No presentar las cifras didácticas como inferidas de las fotos.
