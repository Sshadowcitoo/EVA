from decimal import Decimal

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .presenters import textos_caso
from .testing.fixtures import detalle_fixture


class OrientacionConcretaTests(SimpleTestCase):
    def orientacion(self, **datos):
        contexto = dict(categoria='REVISAR_PORCION', componente='Pollo', ampliada=True,
                        indicadores=dict(n=40, intensidad=Decimal('32.10')))
        contexto.update(datos)
        return render_to_string('recomendaciones/_orientacion.html', contexto)

    def test_indica_alimento_evidencia_accion_y_seguimiento(self):
        html = self.orientacion()
        for texto in ('cantidad servida de pollo', '40 servicios', '32,10 %',
                      'Siguiente paso:', 'Cómo comprobarlo', 'no indica cuántos gramos'):
            self.assertIn(texto, html)
        self.assertNotIn('reduce un 32', html)

    def test_cero_valido_no_se_confunde_con_ausencia(self):
        self.assertIn('0,00 %', self.orientacion(indicadores=dict(n=5, intensidad=0)))
        self.assertIn('No hay un promedio único', self.orientacion(indicadores=dict(n=0, intensidad=None)))
        self.assertNotIn('0,00 %', self.orientacion(indicadores=dict(n=0, intensidad=None)))

    def test_acciones_depanden_de_la_categoria(self):
        for categoria, accion in [('MANTENER', 'Mantén la porción actual'),
                                   ('REVISAR_PREPARACION', 'sabor, textura o presentación'),
                                   ('PRUEBA_CONTROLADA', 'Elige con Cocina un solo cambio')]:
            with self.subTest(categoria=categoria):
                self.assertIn(accion, self.orientacion(categoria=categoria))

    def test_lista_corta_sin_datos_ni_instrucciones_extensas(self):
        html = self.orientacion(ampliada=False)
        self.assertIn('pollo', html)
        self.assertNotIn('32,10 %', html)
        self.assertNotIn('Cómo comprobarlo', html)

    def test_nombre_escapado_y_nombre_visible_desde_filtro(self):
        self.assertIn('&lt;pollo&gt;', self.orientacion(componente='<pollo>'))
        caso = detalle_fixture('aceptada')
        caso['evaluacion']['filtros']['componente'] = 'pollo'
        self.assertEqual(textos_caso(caso)['componente_visible'], 'Pollo')

    def test_seguimiento_no_afirma_mejora_cuando_no_baja_el_sobrante(self):
        from .testing.fixtures import prueba_fixture
        for diferencia, mensaje in [(2, 'El ajuste no redujo el sobrante observado'),
                                    (0, 'El ajuste no redujo el sobrante observado'),
                                    (-2, 'Se observó menos sobrante durante el cambio')]:
            contexto = prueba_fixture('EVALUADA')
            contexto['prueba']['comparacion']['diferencias']['intensidad_pp'] = diferencia
            html = render_to_string('recomendaciones/prueba.html', contexto)
            self.assertIn(mensaje, html)
            self.assertIn('no permite asegurar que el ajuste haya sido la causa', html)

    def test_descripcion_del_cambio_se_muestra_completa_y_escapada(self):
        from .testing.fixtures import prueba_fixture
        contexto = prueba_fixture('EVALUADA')
        contexto['prueba']['cambio'] = 'Antes: más espesa.\nDurante: menos espesa.\nMisma cantidad. <script>mal</script>'
        html = render_to_string('recomendaciones/prueba.html', contexto)
        self.assertIn('Qué cambio se registró', html)
        self.assertIn('Antes: más espesa.<br>Durante: menos espesa.', html)
        self.assertIn('Misma cantidad. &lt;script&gt;', html)
        self.assertNotIn('<script>mal</script>', html)
        self.assertIn('el sistema no realiza el cambio en la cocina', html)

    def test_formulario_pide_antes_y_despues_sin_cambiar_el_campo(self):
        from .forms import PruebaForm
        formulario = PruebaForm()
        self.assertEqual(formulario.fields['cambio'].max_length, 1000)
        self.assertIn('cómo era antes y cómo quedará', formulario.fields['cambio'].help_text)
