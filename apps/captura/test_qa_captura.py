from io import StringIO
from uuid import uuid4

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse

from .models import AsignacionBandeja, Servicio
from .test_dominio_bandejas import BaseDominio


class QACapturaTests(BaseDominio):
    def setUp(self):
        super().setUp()
        call_command("configurar_roles", stdout=StringIO())
        self.usuario.groups.add(Group.objects.get(name="Registro"))
        self.client.force_login(self.usuario)
        self.servido = reverse("captura:resolver_bandeja")
        self.retorno = reverse("captura:buscar_retorno")

    def test_busquedas_vacias_solo_muestran_error_al_enviarse(self):
        for url in (self.servido, self.retorno):
            with self.subTest(url=url):
                self.assertNotContains(self.client.get(url), "solo uno")
                self.assertContains(self.client.get(url, {"numero": "", "etiqueta": ""}), "solo uno")
        self.assertFalse(Servicio.objects.exists())

    def test_numero_invalido_o_inexistente_conserva_el_valor(self):
        casos = {
            "²": "hasta 10 dígitos",
            "9" * 5000: "hasta 10 dígitos",
            "2147483648": "2147483647",
            "1.0": "hasta 10 dígitos",
            "00999": "No se encontró una bandeja activa",
        }
        for url in (self.servido, self.retorno):
            for numero, mensaje in casos.items():
                with self.subTest(url=url, numero=numero[:20]):
                    respuesta = self.client.get(url, {"numero": numero})
                    self.assertContains(respuesta, mensaje)
                    self.assertEqual(respuesta.context["busqueda"]["numero"].value(), numero)
        self.assertFalse(AsignacionBandeja.objects.exists())

    def test_etiqueta_desconocida_y_busqueda_doble_se_pueden_corregir(self):
        respuesta = self.client.get(self.servido, {"etiqueta": "<incorrecta>"})
        self.assertContains(respuesta, "No se encontró una etiqueta vigente")
        self.assertContains(respuesta, "value=\"&lt;incorrecta&gt;\"")
        self.assertContains(respuesta, "<details open>")
        respuesta = self.client.get(self.retorno, {"numero": "001", "etiqueta": "etiqueta"})
        self.assertContains(respuesta, "solo uno")
        self.assertContains(respuesta, 'value="001"')
        self.assertContains(respuesta, 'value="etiqueta"')

    def test_gestion_conserva_identificadores_inexistentes_y_rechaza_numeros_invalidos(self):
        url = reverse("captura:gestion")
        self.assertEqual(self.client.get(url, {"numero": "999"}).status_code, 403)
        self.usuario.groups.set([Group.objects.get(name="Administración")])
        for campo, valor, mensaje in (
            ("numero", "999", "No se encontró una bandeja"),
            ("servicio", str(uuid4()), "No se encontró un servicio"),
            ("numero", "²", "hasta 10 dígitos"),
            ("numero", "9" * 5000, "hasta 10 dígitos"),
            ("numero", "", "solo uno"),
        ):
            with self.subTest(campo=campo, valor=valor[:20]):
                respuesta = self.client.get(url, {campo: valor})
                self.assertContains(respuesta, mensaje)
                self.assertEqual(respuesta.context["form"][campo].value(), valor)

    def test_posts_vacios_muestran_errores_sin_avanzar_el_servicio(self):
        alta = self.client.post(self.servido + "?numero=001", {})
        self.assertEqual(set(alta.context["form"].errors), {"plato", "tipo_porcion"})
        self.assertContains(alta, "errorlist")
        self.assertFalse(Servicio.objects.exists())

        servicio = self.nuevo_servicio()
        url_servido = reverse("captura:foto_servido", args=[servicio.pk])
        url_retorno = reverse("captura:foto_retorno", args=[servicio.pk])
        for url, etapa in ((url_servido, "SERVIDO"), (url_retorno, "RETORNO")):
            if etapa == "RETORNO":
                self.capturar(servicio, "SERVIDO")
                respuesta = self.client.post(self.retorno + "?numero=1", {})
                self.assertEqual(set(respuesta.context["form"].errors), {"confirmar"})
                self.assertContains(respuesta, "errorlist")
            respuesta = self.client.post(url, {})
            self.assertEqual(set(respuesta.context["form"].errors),
                             {"foto", "plato_visible", "vista_superior", "luz_adecuada"})
            self.assertContains(respuesta, "errorlist")
            self.assertFalse(servicio.fotografias.filter(etapa=etapa).exists())

    def test_csrf_y_permiso_se_mantienen(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post(self.servido + "?numero=1", {}).status_code, 403)
        self.usuario.groups.clear()
        self.assertEqual(cliente.get(self.servido, {"numero": 1}).status_code, 403)

    def test_enlace_de_servicio_inexistente_tiene_mensaje_y_mantiene_404(self):
        for nombre in ("captura:confirmacion", "captura:foto_servido", "captura:foto_retorno"):
            url = reverse(nombre, args=[uuid4()])
            self.assertContains(self.client.get(url), "Servicio no encontrado", status_code=404)

    @override_settings(EVA_CAPTURE_MAX_BYTES=1572864)
    def test_ayudas_lote_y_decimal_en_servido_y_retorno(self):
        datos = dict(plato=self.plato.pk, tipo_porcion=self.porcion.pk,
                     sede="principal", modalidad="mesa", lote_preparacion="qa-lote-visible")
        alta = self.client.post(self.servido + "?numero=001", datos)
        servicio = Servicio.objects.get()
        servido = self.client.get(alta.url)
        self.assertContains(servido, "qa-lote-visible")
        self.assertContains(servido, "Toma la foto antes de entregar el plato")
        self.assertNotContains(servido, "Mantén el encuadre")
        self.assertContains(servido, "1,50 MiB")
        self.assertContains(servido, 'data-max-bytes="1572864"')
        self.capturar(servicio, "SERVIDO")
        estado = self.client.get(alta.url)
        self.assertContains(estado, f'href="{self.retorno}?numero=1"')
        self.assertContains(self.client.get(self.retorno, {"numero": "001"}), "qa-lote-visible")
        retorno = self.client.get(reverse("captura:foto_retorno", args=[servicio.pk]))
        self.assertContains(retorno, "Mantén el encuadre")
        self.assertContains(retorno, "qa-lote-visible")
