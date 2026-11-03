# Preparación y pruebas del bloque 5 — 02/11/2026

Rama `eduardo-b5-pruebas-revision`, desde main `1a22306`. Dependencia explícita: regla y contrato de César `2479f9e`. Esta rama no incorpora modelos ni endpoints de revisión ajenos; no se hizo merge.

## Código preparado

`apps/analisis/test_elegibilidad_complementaria.py` amplía la suite de César sin reemplazar `test_elegibilidad.py`. Verifica 32 combinaciones de precondiciones técnicas/evidencia, booleanos estrictos, resultado parcial, revisión de otro intento, motivos acumulados e inmutabilidad de datos de entrada.

Las funciones son puras con datos sintéticos: no prueban revisiones persistidas, autorización HTTP, concurrencia real o IA. La regla recibe información ya verificada por el servidor; el navegador no puede concederse aprobación o evidencia disponible.

## Contrato importante

`puede_confirmar` exige origen REAL, intento COMPLETADO, configuración histórica aprobada, componentes concluyentes y evidencia disponible ahora. `apto_historico` requiere además confirmación asociada al mismo intento; la retención posterior no borra una revisión históricamente válida. No confirmar a ciegas después de vencer imágenes. Un reintento nuevo no hereda aprobación.

## Matriz aún pendiente de implementación real

| Área | Casos |
|---|---|
| Decisión | Confirmar, rechazar y no concluyente; motivos obligatorios según contrato |
| Versionado | Doble POST, dos revisores, versión obsoleta, rectificación como evento nuevo |
| Integridad | Resultado original inmutable; nuevo intento requiere revisión exacta |
| Permisos | Cocina aislada permitida; anónimo login; Registro/Administración solos denegados; sin herencia |
| Evidencia | Foto/máscara del caso, 410 por retención, error temporal de lectura distinto de ausencia, sin claves/URLs públicas |
| Elegibilidad | Simulado, fallo, parcial, baja confianza y configuración no aprobada no se vuelven aptos por decisión humana |
| Regresión | Registro, catálogo, retorno, QR, next seguro y logout siguen operativos |
| UI | Estados y decisiones reales, teclado, 390×844/1440×900 y referencia Figma |

Se necesitan RevisionAnalisis y servicio versionado de Isaac, y formularios/rutas/gateway de Lino. No aparecían ramas B5 de ambos en la consulta del 02/11. No crear tests con imports inexistentes ni simular endpoints para declarar aprobación real.

## Evidencia y cierre

La copia `.revision-b5-validacion` parte de la base de César sin mezclar ramas; se copió únicamente el archivo de tests complementarios. Ejecución del 02/11/2026: `..\.venv\Scripts\python.exe -B manage.py test apps.analisis.test_elegibilidad apps.analisis.test_elegibilidad_complementaria --verbosity 1`: **9 pruebas aprobadas en 0.018 s**, seis de Eduardo y tres existentes de César. Checks sin problemas. No es una prueba de BD de revisiones ni de vistas reales.

Antes del cierre integrado: check, suite completa, migraciones, frontend si cambia, ensayo de confirmar/rechazar/denegación/conflicto sin secretos. El modelo real y su precisión requieren evaluación independiente; un doble solo acredita su contrato.
