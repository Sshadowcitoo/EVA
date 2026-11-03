"""Regresión: una fila de foto eliminada no es evidencia disponible."""
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.analisis import services
from apps.analisis.models import IntentoAnalisis, ResultadoComponente
from apps.analisis.test_dominio_analisis import BaseAnalisis
from apps.captura.models import FotografiaServicio


class FotografiasEliminadasTests(BaseAnalisis):
    def eliminar_servido(self):
        FotografiaServicio.objects.filter(pk=self.servido.pk).update(
            eliminada_en=timezone.now()
        )

    def test_no_solicita_analisis_de_foto_eliminada(self):
        self.eliminar_servido()
        with self.assertRaises(ValidationError):
            self.solicitar()
        self.assertFalse(IntentoAnalisis.objects.exists())

    def test_no_reclama_intento_con_foto_eliminada(self):
        _, intento, _ = self.solicitar()
        self.eliminar_servido()
        self.assertIsNone(services.reclamar_siguiente_intento())
        intento.refresh_from_db()
        self.assertEqual(intento.estado, IntentoAnalisis.Estado.FALLIDO)

    def test_no_publica_resultados_si_la_foto_fue_eliminada(self):
        intento = self.en_proceso()
        self.eliminar_servido()
        with self.assertRaises(ValidationError):
            self.completar(intento)
        self.assertFalse(ResultadoComponente.objects.exists())
