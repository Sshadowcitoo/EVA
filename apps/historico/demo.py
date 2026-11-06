"""Ejemplos de presentación en memoria: sin ORM, fotos ni predicciones reales."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from .contracts import ZONA_HORARIA
from .filtros import normalizar_filtros
from .indicadores import resumir_con_panel

ESCENARIOS = ("con_datos", "sin_aptos")
PLATOS = {
    "seco_de_pollo": ("Seco de pollo", ("arroz", "pollo")),
    "arroz_menestra_carne": ("Arroz con menestra y carne", ("arroz", "menestra", "carne", "ensalada")),
    "encebollado": ("Encebollado", ("yuca", "pescado")),
}


@dataclass(frozen=True)
class ServicioEjemplo:
    pk: str
    plato: str
    tipo_porcion: str

    def get_plato_display(self):
        return PLATOS[self.plato][0]

    def get_tipo_porcion_display(self):
        return "Estándar" if self.tipo_porcion == "estandar" else "Reducida (ejemplo)"


def construir(escenario="con_datos", grupo="", pagina=1):
    if escenario not in ESCENARIOS:
        raise ValueError("Escenario de demostración desconocido.")
    datos = []
    # El hueco de la semana del 19 es intencional. Los valores no vienen de IA.
    ejemplos = [(5, 0), (7, 10), (12, 30), (14, 50), (26, 20), (27, 40), (28, 60), (29, 70)]
    registros = [("seco_de_pollo", "estandar", dia, valor) for dia, valor in ejemplos]
    registros += [("arroz_menestra_carne", "estandar", 12, 20),
                  ("arroz_menestra_carne", "estandar", 26, 30),
                  ("seco_de_pollo", "reducida", 12, 15),
                  ("seco_de_pollo", "reducida", 26, 25),
                  ("encebollado", "estandar", 12, 10),
                  ("encebollado", "estandar", 26, 20)]
    for i, (plato, porcion, dia, valor) in enumerate(registros, 1):
        componentes = [SimpleNamespace(pk=codigo, componente_codigo=codigo,
                                      componente_nombre=codigo.capitalize()) for codigo in PLATOS[plato][1]]
        analisis = SimpleNamespace(origen="SIMULADO", version_modelo="demo-no-inferencia",
            version_configuracion="demo-visual-v1", foto_servido=SimpleNamespace(protocolo_version="demo-protocolo"))
        resultados = [SimpleNamespace(servicio_componente_id=c.pk,
            porcentaje=Decimal(valor if c.componente_codigo == "arroz" else max(0, valor - 5))) for c in componentes]
        datos.append(dict(servicio=ServicioEjemplo(f"demo-{i:03}", plato, porcion),
            analisis=analisis, fecha=datetime(2026, 10, dia, 12, tzinfo=ZoneInfo(ZONA_HORARIA)),
            componentes=componentes, resultados=resultados,
            motivo=None if escenario == "con_datos" else "NO_CONCLUYENTE",
            contexto_clave="demo-contexto-supuesto"))
    filtros = normalizar_filtros(dict(desde="2026-10-05", hasta="2026-11-01"))
    resumen, panel = resumir_con_panel(datos, [], filtros, pagina, grupo)
    if not grupo and panel["opciones"]:
        grupo = next(g["clave"] for g in panel["opciones"] if g["plato_codigo"] == "seco_de_pollo"
                     and g["componente_codigo"] == "arroz" and g["porcion_codigo"] == "estandar")
        resumen, panel = resumir_con_panel(datos, [], filtros, pagina, grupo)
    resumen["solo_pruebas"] = True
    resumen["advertencias"] = ["Ejemplos ficticios: no son predicciones ni evidencia validada. El contexto compatible se supone solo para esta demostración."]
    return resumen, panel
