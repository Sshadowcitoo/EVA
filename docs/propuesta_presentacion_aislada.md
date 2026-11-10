# Inventario reproducible y propuesta de carga aislada

Base `c3404ff`. Este PR entrega un inventario determinista, previsualización y pruebas de consistencia. El manifiesto es un insumo de planificación, sin escritura en Django o AWS.

```sh
python ops/presentacion/planificar.py --lote exposicion-eva
python ops/presentacion/planificar.py --lote exposicion-eva --salida /ruta/local/exposicion-eva.json
python -m unittest ops.presentacion.test_planificar
```

El identificador del lote genera UUID reproducibles y separados por lote. Repetir el comando con el mismo archivo conserva sus bytes y un archivo distinto en el destino se rechaza. La previsualización muestra cantidades, destino y ausencia de persistencia en base.

## Inventario y recorrido esperado

| Elemento | Plan |
| --- | --- |
| Servicios, fotos y bandejas | 288 servicios en cuatro semanas, 288 pares planeados y 6 bandejas reutilizadas sin solapamiento. Las fotos todavía no se han producido. |
| Catálogo y contexto | Tres platos, siete componentes y porciones estándar/reducida. Sede principal, modalidad mesa, misma franja de servido 12:00–13:00. Lotes separados por fecha y plato. |
| Grupos | Seis combinaciones plato/porción. Cada combinación incluye ocho días en cuatro semanas. Cinco entradas sintéticas con mediciones y una sin análisis por fecha. Los componentes permanecen separados. |
| Comparación | Semanas 1–2 frente a 3–4 para un mismo grupo exacto. En cada mitad, cuatro días con cinco mediciones y cuatro lotes. 20 de 24 casos planificados con mediciones por grupo, 83,33 % bajo los supuestos del ensayo. |
| Historia para presentar | Encebollado con sobrantes visuales bajos y ceros sintéticos, seco de pollo alto y menestra con señal intermedia en el grupo de arroz. Cambios semanales sin cifras en plantillas. 240 ejemplos con mediciones y 48 sin análisis. |
| Revisión y decisiones por completar | En el escenario aislado, revisión de ejemplos con mediciones, percepciones opcionales, mantener para yuca, revisar porción para arroz del seco y prueba controlada para arroz del plato con menestra. Proponer justificaciones de ejemplo y evaluar la intervención en el segundo periodo. |

Las tres pruebas verifican identidad, no reclasificación, reutilización, lotes, bloques completos, cobertura y presencia de las tres categorías previstas con los valores de la propuesta experimental vigente. Los resultados se derivan del manifiesto, sin ejecutar los selectores de Django. El lote no integra la huella de contexto; sí aporta diversidad de preparaciones.

## Decisión pendiente antes de implementar la carga

El selector operativo de Histórico excluye `SIMULADO`, y Cocina bloquea la confirmación operativa de una simulación. Recomendaciones exige evidencia `REAL` y criterios aprobados. El histórico de prueba en memoria reutiliza el cálculo y etiqueta `solo_pruebas`, pero no contiene las relaciones ORM que necesita el recorrido completo. El inventario mantiene `SIMULADO` y no se habilita comparabilidad operativa.

**Propuesta para aprobación:** adaptador de lectura y acciones de ensayo en una configuración Django exclusivamente local, con la misma interfaz y un rótulo visible «Entorno de presentación». Un inventario de pertenencia validado limita el adaptador a los registros del lote. Sus revisiones y decisiones serían explícitamente de ejemplo. Los cálculos comunes recibirían esa población sintética como entrada de ensayo, con parámetros de prueba y DTO marcados `solo_pruebas`. No se añadirían páginas ni menús. Los selectores y reglas operativos conservarían su comportamiento.

Implementación condicionada a aprobación y a un entorno de ejecución:

1. Exigir settings locales exclusivos, SQLite dentro de un directorio de presentación con marcador, almacenamiento local en otro subdirectorio y arranque en loopback. Rechazar configuración remota, conexión al motor o base sin marcador. Bloquear el adaptador si falla cualquier condición.
2. Previsualizar el destino y conteos. Generar un inventario de IDs y archivos del lote y sus hashes. Sembrar en transacción con roles de prueba explícitos y comprobar relaciones. Rechazar colisiones con registros ajenos y reutilizar cuentas sin sobrescribirlas.
3. Para retirar un lote, listar IDs y dependencias, confirmar el lote de forma explícita y eliminar solo las filas y archivos registrados. Si existen dependencias ajenas, abortar. Verificar que los datos y cuentas ajenos permanecen iguales.
4. Ejercitar las pantallas normales en Django con datos de ejemplo rotulados, capturar evidencia real de las pantallas y comprobar que el mismo lote queda excluido al consultar mediante los selectores operativos.

La carga, la retirada, la generación de recomendaciones y las capturas reales de Django siguen pendientes. El entorno de trabajo no tiene Django y la excepción de presentación requiere aprobación previa. No hubo cambios de contratos, fórmulas, criterios, permisos, interfaz ni datos operativos.
