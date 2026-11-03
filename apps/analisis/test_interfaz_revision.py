from django.template.loader import render_to_string
from django.test import SimpleTestCase

SERVICIO = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
CASO = {
    "plato_nombre": "Seco de pollo", "porcion_nombre": "Porción mediana", "origen": "REAL",
    "estado": "COMPLETADO", "bandeja_numero": "EVA-001", "servicio_id": SERVICIO,
}
RESULTADOS = [
    {"componente": "Arroz", "porcentaje_texto": "24 %", "confianza_texto": "91 %", "estado": "CONCLUYENTE", "color_clave": 1},
    {"componente": "Ensalada", "estado": "NO_CONCLUYENTE", "motivo": "OCULTACION"},
]
FOTOS = {"foto_servido_url": "/f/servido.jpg", "foto_retorno_url": "/f/retorno.jpg"}
VIGENTE = {"decision": "RECHAZADO", "autor": "cocina1", "fecha": "02/11/2026", "motivo": "Máscara incorrecta"}


def revision(**contexto):
    base = {"caso": CASO, "resultados": RESULTADOS, "decision_url": "/analisis/revision/1/decidir/",
            "version_esperada": 3, "puede_confirmar": True, **FOTOS}
    base.update(contexto)
    return render_to_string("analisis/revision.html", base)


class RevisionCocinaTests(SimpleTestCase):
    def test_tres_acciones_distintas_con_los_textos_de_figma(self):
        html = revision()
        for texto, valor in (("Confirmar revisión", "CONFIRMADO"), ("Marcar no concluyente", "NO_CONCLUYENTE"),
                             ("Marcar incorrecto", "RECHAZADO")):
            self.assertIn(f'name="decision" value="{valor}"', html)
            self.assertIn(texto, html)
        self.assertIn('name="version_esperada" value="3"', html)

    def test_motivo_es_un_campo_con_sugerencias_ocultas_sin_javascript(self):
        html = revision()
        self.assertIn('name="motivo" maxlength="1000"', html)
        self.assertIn("data-motivo-sugerencias hidden", html)
        self.assertIn("Máscara incorrecta", html)
        self.assertIn("Fotografía dudosa", html)
        self.assertIn("Es obligatorio al marcar como incorrecto o no concluyente", html)

    def test_confirmar_habilitado_solo_si_el_servidor_lo_permite(self):
        self.assertNotIn('value="CONFIRMADO" disabled', revision(puede_confirmar=True))
        bloqueado = revision(puede_confirmar=False)
        self.assertIn('value="CONFIRMADO" disabled', bloqueado)
        self.assertIn("confirmar-ayuda", bloqueado)

    def test_razon_visible_cuando_confirmar_esta_bloqueado(self):
        simulado = revision(puede_confirmar=False, caso={**CASO, "origen": "SIMULADO"})
        self.assertIn("SIMULADO", simulado)
        self.assertIn("no se puede confirmar como evidencia", simulado)
        sin_fotos = revision(puede_confirmar=False, foto_servido_url="", foto_retorno_url="")
        self.assertIn("no se puede confirmar a ciegas", sin_fotos)
        generico = revision(puede_confirmar=False)
        self.assertIn("criterios técnicos aprobados", generico)

    def test_sin_evidencia_explica_que_no_hay_fotos(self):
        html = revision(foto_servido_url="", foto_retorno_url="")
        self.assertIn("La evidencia fotográfica no está disponible", html)
        self.assertNotIn("<img", html)

    def test_mascaras_se_superponen_en_su_foto(self):
        html = revision(mascaras=[{"url": "/m/a.png", "componente": "Arroz", "etapa": "RETORNO"}])
        self.assertEqual(html.count('class="analisis-mascara"'), 1)
        self.assertIn("Máscara de Arroz sobre el retorno", html)

    def test_leyenda_y_motivo_legible_en_la_tabla(self):
        html = revision()
        self.assertIn("leyenda-punto c1", html)
        self.assertIn("El componente está oculto", html)
        self.assertIn("No concluyente", html)

    def test_identificacion_distingue_bandeja_y_servicio(self):
        html = revision()
        self.assertIn("Bandeja", html)
        self.assertIn("EVA-001", html)
        self.assertIn(SERVICIO, html)

    def test_decision_vigente_se_lee_en_palabras_y_pide_rectificar(self):
        html = revision(revision_actual=VIGENTE)
        self.assertIn("Marcada como incorrecta", html)
        self.assertIn("cocina1", html)
        self.assertIn("Motivo: Máscara incorrecta", html)
        self.assertIn("Rectificar la decisión", html)
        self.assertIn("data-rectificar", html)
        self.assertIn("Es obligatorio para rectificar", html)
        primera = revision()
        self.assertIn("Tu decisión", primera)
        self.assertNotIn("data-rectificar", primera)
        self.assertIn("Por revisar", primera)

    def test_solo_lectura_cuando_hay_decision_y_no_hay_endpoint(self):
        html = revision(revision_actual={**VIGENTE, "decision": "CONFIRMADO"}, decision_url="")
        self.assertIn("Confirmada", html)
        self.assertIn("Revisión cerrada. Consulta en solo lectura.", html)
        self.assertNotIn('name="decision"', html)

    def test_sin_endpoint_y_sin_decision_no_hay_formulario_falso(self):
        html = revision(decision_url="")
        self.assertIn("al conectar el servicio de revisión", html)
        self.assertNotIn('name="decision"', html)
        self.assertNotIn("js/analisis.js", html)

    def test_analisis_en_curso_o_fallido_no_se_puede_revisar(self):
        for estado in ("PENDIENTE", "EN_PROCESO"):
            html = revision(caso={**CASO, "estado": estado})
            self.assertIn("El análisis todavía no termina", html)
            self.assertNotIn('name="decision"', html)
        for estado in ("FALLIDO", "TIEMPO_AGOTADO"):
            html = revision(caso={**CASO, "estado": estado})
            self.assertIn("no hay un resultado técnico que revisar", html)
            self.assertNotIn('name="decision"', html)

    def test_simulado_se_marca_arriba(self):
        html = revision(caso={**CASO, "origen": "SIMULADO"})
        self.assertIn("SIMULADO: solo prueba del flujo", html)

    def test_el_script_solo_se_carga_con_formulario(self):
        self.assertIn("js/analisis.js", revision())
