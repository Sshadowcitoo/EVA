"""Diagnóstico local de entradas límite; solo usa base de pruebas temporal.

No corrige el producto ni envía peticiones a AWS. Los 500 se registran como
hallazgos; que el diagnóstico termine no significa que esos casos estén aprobados.
"""
import json
import logging
import os
import sys
from io import StringIO
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, override_settings
from django.test.utils import setup_databases, setup_test_environment, teardown_databases, teardown_test_environment
from apps.captura.models import Bandeja, Servicio
from apps.catalogo.models import Plato, TipoPorcion


def auditar():
    resultados = []
    cliente = Client(raise_request_exception=False)
    usuario = get_user_model().objects.create_user(username="QA-EDUARDO-LIMITES-LOCAL")
    usuario.groups.add(Group.objects.get_or_create(name="Registro")[0])
    cliente.force_login(usuario)
    call_command("cargar_catalogo_demo", stdout=StringIO())
    call_command("cargar_bandejas_demo", stdout=StringIO())

    def consultar(nombre, ruta, datos=None, metodo="get"):
        antes = Servicio.objects.count()
        respuesta = getattr(cliente, metodo)(ruta, datos or {})
        contexto = respuesta.context
        formulario = contexto.get("form") if contexto is not None else None
        cuerpo = respuesta.content.decode("utf-8", errors="replace")
        resultados.append({
            "caso": nombre, "ruta": ruta, "metodo": metodo.upper(),
            "status": respuesta.status_code,
            "cache_control": respuesta.headers.get("Cache-Control"),
            "error_visible_contexto": contexto.get("error") if contexto is not None else None,
            "formulario_bound": formulario.is_bound if formulario is not None else None,
            "formulario_errores": dict(formulario.errors) if formulario is not None else None,
            "excepcion": respuesta.exc_info[0].__name__ if respuesta.exc_info else None,
            "numero_conservado": 'value="abc"' in cuerpo if nombre == "letras" else None,
            "ayuda_bandeja_pendiente_en_servido": "Busca una bandeja pendiente" in cuerpo if ruta == "/captura/bandeja/" else None,
            "servicios_creados": Servicio.objects.count() - antes,
        })

    entradas = [
        ("inicial", {}), ("vacio", {"numero": ""}),
        ("espacios", {"numero": "   "}), ("letras", {"numero": "abc"}),
        ("inexistente", {"numero": "2322"}), ("cero", {"numero": "0"}),
        ("negativo", {"numero": "-1"}), ("decimal", {"numero": "1.5"}),
        ("digito_superindice", {"numero": "\u00b2"}),
        ("entero_64_digitos", {"numero": "9" * 64}),
        ("entero_5000_digitos", {"numero": "9" * 5000}),
        ("numero_y_etiqueta", {"numero": "1", "etiqueta": "QA-invalida"}),
        ("etiqueta_invalida", {"etiqueta": "QA-invalida"}),
        ("bandeja_libre", {"numero": "1"}),
    ]
    for ruta in ("/captura/bandeja/", "/captura/retorno/"):
        for nombre, datos in entradas:
            consultar(nombre, ruta, datos)
    consultar("post_vacio_bandeja_libre", "/captura/bandeja/?numero=1", metodo="post")
    servicio = Servicio.registrar(
        plato=Plato.objects.get(codigo="seco_de_pollo"),
        porcion=TipoPorcion.objects.get(codigo="estandar"), usuario=usuario,
        bandeja=Bandeja.objects.get(numero=1),
    )
    consultar("post_foto_sin_archivo_ni_checklist", f"/captura/{servicio.pk}/foto-servido/", metodo="post")
    consultar("post_basico_vacio", "/captura/nueva/", metodo="post")
    usuario.groups.set([Group.objects.get_or_create(name="Cocina")[0]])
    filtros = [
        ("pagina_letras", {"page": "abc"}),
        ("pagina_negativa", {"page": "-1"}),
        ("fecha_invalida", {"desde": "2026-02-31"}),
        ("fechas_invertidas", {"desde": "2026-11-04", "hasta": "2026-11-01"}),
        ("horas_invertidas", {"hora_desde": "18:00", "hora_hasta": "08:00"}),
        ("plato_desconocido", {"plato": "QA-invalido"}),
    ]
    for ruta in ("/historico/", "/recomendaciones/"):
        for nombre, datos in filtros:
            consultar(nombre, ruta, datos)
    consultar("comparacion_sin_fechas", "/historico/comparar/", {"plato": ""})
    consultar("demo_escenario_desconocido", "/recomendaciones/demostracion/", {"escenario": "QA-invalido"})
    usuario.groups.set([Group.objects.get_or_create(name="Administración")[0]])
    for ruta in ("/catalogo/platos/nuevo/", "/catalogo/componentes/nuevo/", "/catalogo/porciones/nuevo/"):
        consultar("alta_catalogo_vacia", ruta, metodo="post")
    consultar("evaluacion_sin_campos", "/recomendaciones/evaluar/", metodo="post")
    return resultados


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    setup_test_environment()
    anterior = setup_databases(verbosity=0, interactive=False)
    try:
        with override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"]):
            resultados = auditar()
        salida = ROOT / "docs/evidencias/qa_20261104/diagnostico_validaciones_local.json"
        salida.write_text(json.dumps({"base": "7615a24", "fecha_ecuador": datetime.now(ZoneInfo("America/Guayaquil")).isoformat(),
                                      "entorno": "SQLite temporal, DEBUG=False; sin AWS; Client sin enforcement CSRF para aislar validación de formularios",
                                      "observaciones": resultados}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"observaciones": len(resultados), "respuestas_500": sum(r["status"] == 500 for r in resultados),
                          "salida": str(salida)}, ensure_ascii=False))
    finally:
        teardown_databases(anterior, verbosity=0)
        teardown_test_environment()
