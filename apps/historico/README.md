# historico

Módulo: MOD-04 Histórico e indicadores
Requisitos: RF-11 a RF-13, RF-19; RNF-02, RNF-05
Historias: HU-05
Pendiente: P-03
Estado: contrato v1, normalización de filtros y estructura registrados; consultas y persistencia todavía pendientes.

Entrada: [contrato del bloque 6](../../docs/contrato_bloque_6.md).
Preparación y reparto: [inicio del bloque 6](../../docs/inicio_bloque_6.md).
Los DTO de `testing/fixtures.py` son solo para pruebas y no se cargan en producción.
`services.py` falla explícitamente con BackendHistoricoNoDisponible mientras falte
el dominio; no entrega datos sintéticos como respuesta real.
