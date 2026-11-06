# Documentación del software EVA

Versión de demostración, 6 de noviembre de 2026.

## Objetivo y alcance

EVA registra servicios de comida, vincula fotografías de servido y retorno,
consulta un análisis visual, permite revisión humana y organiza histórico,
indicadores y decisiones. El piloto representa La Mesa Costeña, un establecimiento
ficticio. Incluye encebollado (yuca y pescado), seco de pollo (arroz y pollo) y
arroz con menestra y carne (arroz, menestra, carne y ensalada).

## Organización funcional

1. Acceso y catálogo: usuarios, roles, platos, componentes y porciones.
2. Servicios y bandejas: identificadores, asignaciones, etiquetas y trazabilidad.
3. Captura: servido, retorno, checklist, hora automática, vinculación móvil,
   almacenamiento privado, anulación, reemplazo de etiqueta y retención.
4. Análisis: intentos, comunicación con motor, resultados por componente y máscaras.
5. Cocina: revisión humana versionada, estados y motivos.
6. Histórico: filtros, comparación, indicadores y percepción opcional.
7. Recomendaciones: evaluación de suficiencia, decisiones justificadas, seguimiento
   de pruebas controladas y demostración separada con datos de ejemplo.

Los contratos y decisiones detalladas se conservan en los documentos de cada
bloque de este directorio. La interfaz respeta los flujos de Figma con diferencias
documentadas; no se afirma coincidencia visual exacta ni cobertura móvil exhaustiva.

## Datos y reglas de integridad

Servicio relaciona catálogo, operador, contexto e instantáneas. Su composición
histórica no se reescribe al editar el catálogo. Bandeja conserva sus etiquetas y
asignaciones; FotografiaServicio identifica etapa, archivo privado, protocolo y
hora. Análisis conserva intentos y resultados, y Cocina mantiene sus revisiones.

Un plato nuevo necesita componentes activos. Registrar un servicio sin composición
activa se rechaza antes de crear filas. Una bandeja no puede tener dos asignaciones
abiertas. El retorno completa el par y libera la asignación dentro de una
transacción. Anular o reemplazar una etiqueta requiere Administración y motivo.
La falta de evidencia se conserva como no concluyente o insuficiente, no como cero.

## Verificación y despliegue

Las pruebas automáticas cubren dominio, formularios, permisos, integración HTTP,
almacenamiento y comportamiento JavaScript. Los informes de los compañeros son
evidencia de los casos que describen, no una aprobación global del sistema.
Véase `qa_cierre_2026_11_06.md` para resultados actuales y pendientes.

GitHub main no se despliega por sí solo: la actualización del servidor es una
operación separada, con versión objetivo, respaldo, comprobaciones y reversión
si falla. Mantiene cuentas y configuración externa. No se publican credenciales.

## Documentos de entrega

- [Manual de usuario](manual_usuario.md).
- [Características técnicas](caracteristicas_tecnicas.md).
- [Cierre de QA y límites](qa_cierre_2026_11_06.md).

La presentación debe describir una demostración controlada con datos reales y
sintéticos. Queda pendiente una evaluación independiente para afirmar precisión
en un restaurante real.
