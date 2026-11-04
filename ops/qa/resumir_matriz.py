"""Resume una matriz CSV sin modificar sus registros ni aprobar casos pendientes."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ESTADOS = {"APROBADO", "FALLIDO", "BLOQUEADO", "NO EJECUTADO", "NO APLICA"}
CAMPOS = {"id", "responsable", "fecha_hora", "commit_entorno", "rol",
          "navegador_dispositivo", "bandeja_servicio_lote", "datos", "pasos",
          "esperado", "observado", "estado", "evidencia", "incidencia_pr",
          "repeticion", "revisor"}


def resumir(ruta):
    with Path(ruta).open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if not CAMPOS.issubset(lector.fieldnames or []):
            raise ValueError("La matriz no contiene todos los campos de la guía")
        filas = list(lector)
    claves = set()
    por_persona = defaultdict(Counter)
    for fila in filas:
        clave = (fila["responsable"], fila["id"])
        if clave in claves or fila["estado"] not in ESTADOS:
            raise ValueError(f"Caso duplicado o estado inválido: {clave}")
        claves.add(clave)
        if fila["estado"] == "APROBADO" and not all(
            fila[k].strip() for k in ("evidencia", "observado", "fecha_hora", "commit_entorno")
        ):
            raise ValueError(f"Aprobación sin evidencia mínima: {clave}")
        por_persona[fila["responsable"]][fila["estado"]] += 1
    totales = Counter(f["estado"] for f in filas)
    return {"casos": len(filas), "por_responsable": dict(por_persona),
            "totales": dict(totales),
            "casos_pendientes": sum(totales[e] for e in ("FALLIDO", "BLOQUEADO", "NO EJECUTADO")),
            "nota": "Este conteo no certifica la demo: revisar incidencias, evidencia, dispositivos y revisión cruzada."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matriz", type=Path)
    args = parser.parse_args()
    print(json.dumps(resumir(args.matriz), ensure_ascii=False, indent=2))
