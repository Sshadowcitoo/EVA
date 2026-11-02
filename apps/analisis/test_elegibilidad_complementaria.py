"""Regla pura de César: no acredita persistencia de revisiones ni endpoints."""

from itertools import product

from django.test import SimpleTestCase

from apps.analisis.elegibilidad import evaluar_elegibilidad


class ElegibilidadComplementariaTests(SimpleTestCase):
    def datos(self, **cambios):
        datos = dict(origen="REAL", estado_intento="COMPLETADO",
                     estados_componentes=["CONCLUYENTE", "CONCLUYENTE"],
                     configuracion_aprobada=True, evidencia_disponible=True,
                     decision="CONFIRMADO", intento_id="intento-1",
                     intento_revisado_id="intento-1")
        datos.update(cambios)
        return evaluar_elegibilidad(**datos)

    def test_tabla_combinada_no_convierte_bloqueos_en_aptitud(self):
        for real, completado, aprobada, concluyentes, evidencia in product((False, True), repeat=5):
            with self.subTest(real=real, completado=completado, aprobada=aprobada,
                              concluyentes=concluyentes, evidencia=evidencia):
                resultado = self.datos(
                    origen="REAL" if real else "SIMULADO",
                    estado_intento="COMPLETADO" if completado else "FALLIDO",
                    configuracion_aprobada=aprobada,
                    estados_componentes=["CONCLUYENTE"] if concluyentes else ["NO_CONCLUYENTE"],
                    evidencia_disponible=evidencia,
                )
                tecnico = real and completado and aprobada and concluyentes
                self.assertEqual(resultado["puede_confirmar"], tecnico and evidencia)
                # La retención posterior no borra una revisión válida anterior.
                self.assertEqual(resultado["apto_historico"], tecnico)

    def test_aprobacion_y_evidencia_exigen_booleano_real(self):
        for valor in (1, "True", "false", None):
            with self.subTest(valor=valor):
                sin_aprobacion = self.datos(configuracion_aprobada=valor)
                self.assertFalse(sin_aprobacion["puede_confirmar"])
                self.assertFalse(sin_aprobacion["apto_historico"])
                sin_evidencia = self.datos(evidencia_disponible=valor)
                self.assertFalse(sin_evidencia["puede_confirmar"])

    def test_componente_parcial_no_se_oculta_entre_concluyentes(self):
        resultado = self.datos(estados_componentes=["CONCLUYENTE", "NO_CONCLUYENTE", "CONCLUYENTE"])
        self.assertFalse(resultado["puede_confirmar"])
        self.assertFalse(resultado["apto_historico"])
        self.assertIn("COMPONENTES_NO_CONCLUYENTES", resultado["motivos"])

    def test_nuevo_intento_no_hereda_revision_y_faltan_ids_no_coinciden(self):
        for ids in (("nuevo", "anterior"), (None, "anterior"), ("nuevo", None), (None, None)):
            with self.subTest(ids=ids):
                resultado = self.datos(intento_id=ids[0], intento_revisado_id=ids[1])
                self.assertFalse(resultado["apto_historico"])
                # Puede ser técnicamente revisable, pero aún no está aprobado.
                self.assertTrue(resultado["puede_confirmar"])

    def test_todos_los_motivos_se_conservan(self):
        resultado = self.datos(origen="SIMULADO", estado_intento="TIEMPO_AGOTADO",
                               configuracion_aprobada=False, evidencia_disponible=False,
                               estados_componentes=[])
        self.assertSetEqual(set(resultado["motivos"]), {
            "ORIGEN_NO_REAL", "INTENTO_NO_COMPLETADO", "SIN_CONFIGURACION_APROBADA",
            "COMPONENTES_NO_CONCLUYENTES", "EVIDENCIA_NO_DISPONIBLE",
        })

    def test_regla_no_modifica_lista_de_componentes_del_llamador(self):
        estados = ["CONCLUYENTE", "NO_CONCLUYENTE"]
        original = estados.copy()
        self.datos(estados_componentes=estados)
        self.assertEqual(estados, original)
