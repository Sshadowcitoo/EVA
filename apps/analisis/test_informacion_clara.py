from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.recomendaciones.testing.fixtures import detalle_fixture
from .test_interfaz_revision import revision, CASO


class InformacionClaraTests(SimpleTestCase):
    def test_revision_conserva_la_proteccion_sin_exponer_codigos(self):
        html = revision(
            caso={**CASO, 'version_modelo': 'modelo-interno-reservado'},
            resultados=[{'componente': 'Arroz', 'estado': 'NO_CONCLUYENTE',
                         'motivo': 'NO_COMPARABLE', 'confianza_texto': '85.07%',
                         'porcentaje_texto': '77 %'}],
        )
        self.assertIn('Las fotos no son comparables', html)
        self.assertIn('Sin medida', html)
        self.assertIn('name="version_esperada" value="3"', html)
        for valor in ('NO_COMPARABLE', 'modelo-interno-reservado', '85.07%', '77 %',
                      CASO['servicio_id'], '<summary>Detalles técnicos'):
            self.assertNotIn(valor, html)
        self.assertEqual(html.count('<summary>Más información</summary>'), 1)

    def test_cero_confirmado_sigue_siendo_un_resultado_valido(self):
        html = render_to_string('analisis/_tabla_resultados.html', {
            'resultados': [{'componente': 'Arroz', 'estado': 'CONCLUYENTE',
                            'porcentaje_texto': '0 %'}],
        })
        self.assertIn('0 %', html)
        self.assertIn('Concluyente', html)

    def test_recomendacion_explica_la_muestra_sin_parametros_ni_referencias(self):
        caso = detalle_fixture('aceptada')
        html = render_to_string('recomendaciones/_evidencia.html', {
            'caso': caso, 'parametros': 'PARAMETROS_INTERNOS_RESERVADOS',
        })
        self.assertIn('Por qué aparece esta recomendación', html)
        self.assertIn('La decisión final corresponde', html)
        self.assertIn('Se utilizaron', html)
        for valor in ('PARAMETROS_INTERNOS_RESERVADOS', 'version_modelo',
                      'Referencias de evidencia', 'Explicación de la regla aplicada'):
            self.assertNotIn(valor, html)

    def test_aviso_de_datos_de_ejemplo_se_conserva_en_lenguaje_comun(self):
        caso = detalle_fixture('aceptada')
        caso['evaluacion']['solo_pruebas'] = True
        html = render_to_string('recomendaciones/_evidencia.html', {'caso': caso})
        self.assertIn('datos son de ejemplo y no corresponden a servicios reales', html)
