# historico

Módulo: MOD-04 Histórico e indicadores
Requisitos: RF-11 a RF-13, RF-19; RNF-02, RNF-05
Historias: HU-05
Pendiente: P-03
Estado: dominio implementado en `dominio-historico-bloque-6`; interfaz en entrega independiente.

Entrada: [contrato del bloque 6](../../docs/contrato_bloque_6.md).
Preparación y reparto: [inicio del bloque 6](../../docs/inicio_bloque_6.md).
Los DTO de `testing/fixtures.py` son solo para pruebas y no se cargan en producción.
`services.py` consulta registros reales y conserva el contrato v1. La percepción
requiere la migración 0001_percepcion_versionada. No entrega fixtures como respuesta real.
Ver [implementación del dominio](../../docs/dominio_bloque_6.md).
