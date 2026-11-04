"""Contrasta evidencia CDP sanitizada contra expectativas de la ronda QA."""
import argparse
import json
from pathlib import Path


def verificar(ruta):
    informe = json.loads(Path(ruta).read_text(encoding="utf-8"))
    casos = informe["casos"]
    assert len(casos) == 65, "Ronda incompleta"
    anonimos = [c for c in casos if c["id"] == "E03/E25"]
    assert len(anonimos) == 6
    assert all(c["destino"] == "/cuentas/login/" for c in anonimos)
    permitidos = {
        "Registro": {"/captura/bandeja/"},
        "Cocina": {"/analisis/", "/historico/", "/recomendaciones/", "/recomendaciones/demostracion/"},
        "Administracion": {"/catalogo/platos/", "/historico/", "/recomendaciones/", "/recomendaciones/demostracion/"},
    }
    destinos = {"Registro": "/captura/nueva/", "Cocina": "/analisis/revision/", "Administracion": "/catalogo/platos/"}
    demos = {
        "mantener": (["10", "4,00 %", "0,00 %"], "Mantener"),
        "porcion": (["10", "30,00 %", "100,00 %"], "Revisar porción"),
        "prueba": (["10", "12,00 %", "20,00 %"], "Realizar prueba controlada"),
        "insuficiente": (["2", "35,00 %", "100,00 %"], "Evidencia insuficiente"),
    }
    for rol in permitidos:
        propios = [c for c in casos if c.get("rol") == rol]
        assert next(c for c in propios if c["id"] == "E01-login")["destino"] == destinos[rol]
        rutas = [c for c in propios if c["id"] == "E04/E25"]
        assert len(rutas) == 6
        for c in rutas:
            assert c["status"] == (200 if c["url"] in permitidos[rol] else 403), (rol, c["url"])
        assert next(c for c in propios if c["id"] == "E05")["status"] == 403
        assert next(c for c in propios if c["id"] == "E06-logoutGET")["status"] == 405
        assert next(c for c in propios if c["id"] == "E01-logout")["destino"] == "/cuentas/login/"
        if rol != "Registro":
            ejemplos = [c for c in propios if c["id"] == "E18/E19"]
            assert {c["escenario"] for c in ejemplos} == set(demos)
            for c in ejemplos:
                valores, categoria = demos[c["escenario"]]
                assert c["datosEjemplo"] and c["noPrediccion"]
                assert [i["valor"] for i in c["indicadores"]] == valores
                assert c["recomendacion"].endswith(categoria)
    capturas = [c for c in casos if c["id"] == "J02-cruzada"]
    assert len(capturas) == 21 and all(not c["overflow"] and not c["passwords"] for c in capturas)
    assert not informe["login_publico"]["passwords"]
    return {"observaciones_verificadas": len(casos), "capturas_viewport": len(capturas) + 1,
            "resultado": "EXPECTATIVAS DE ESTA RONDA CUMPLIDAS",
            "limite": "No evalúa cámara física, BFCache, Figma, IA real ni cierre integral."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidencia", type=Path)
    args = parser.parse_args()
    print(json.dumps(verificar(args.evidencia), ensure_ascii=False, indent=2))
