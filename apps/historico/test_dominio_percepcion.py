from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connections, transaction
from django.test import TransactionTestCase

from apps.captura.models import Servicio
from apps.catalogo.models import Plato, TipoPorcion
from . import services
from .contracts import ConflictoPercepcion, Percepcion, ServicioNoDisponible
from .models import PercepcionServicio
from .test_dominio_historico import BaseHistorico


class PercepcionTests(BaseHistorico):
    def setUp(self):
        self.servicio = Servicio.registrar(plato=Plato.objects.get(codigo='seco_de_pollo'),
            porcion=TipoPorcion.objects.get(codigo='estandar'), usuario=self.registro)

    def guardar(self, categoria='ADECUADA', motivo='', usuario=None, version=0):
        return services.registrar_percepcion(self.servicio.pk, categoria, motivo, usuario or self.registro, version)

    def test_no_informado_no_es_adecuado_y_no_crea_filas_al_consultar(self):
        dato = services.obtener_percepcion(self.servicio.pk, self.registro)
        self.assertEqual(set(dato), set(Percepcion.__annotations__))
        self.assertEqual(dato['categoria'], 'NO_INFORMADO')
        self.assertEqual(dato['version'], 0)
        self.assertIsNone(dato['registrada_en'])
        self.assertFalse(PercepcionServicio.objects.exists())
        self.assertEqual(self.guardar('NO_INFORMADO'), dato)
        self.assertFalse(PercepcionServicio.objects.exists())

    def test_tres_categorias_correccion_y_auditoria_conservada(self):
        for version, categoria in enumerate(('INSUFICIENTE', 'ADECUADA', 'EXCESIVA', 'NO_INFORMADO')):
            dto = self.guardar(categoria, '' if categoria == 'NO_INFORMADO' else 'Respuesta declarada', version=version)
            self.assertEqual(dto['version'], version + 1)
        filas = list(self.servicio.percepciones.order_by('version'))
        self.assertEqual(len(filas), 4)
        self.assertEqual(sum(p.vigente for p in filas), 1)
        self.assertEqual(filas[-1].sustituye_id, filas[-2].pk)
        self.assertTrue(all(p.autor_id == self.registro.pk and p.fecha is not None for p in filas))

    def test_otro_operador_de_registro_no_necesita_ser_creador(self):
        otro = get_user_model().objects.create_user('otro_registro')
        otro.groups.add(Group.objects.get(name='Registro'))
        self.assertNotEqual(self.servicio.creado_por_id, otro.pk)
        dto = self.guardar(usuario=otro)
        self.assertEqual(dto['operador_visible'], otro.get_username())
        self.assertEqual(services.obtener_percepcion(self.servicio.pk, self.registro)['version'], 1)

    def test_reenvio_identico_no_duplica_y_version_obsoleta_no_sobrescribe(self):
        original = self.guardar(motivo='Declaración de fixture')
        self.assertEqual(self.guardar(motivo=' Declaración de fixture '), original)
        self.assertEqual(self.guardar(motivo='Declaración de fixture', version=1), original)
        with self.assertRaises(ConflictoPercepcion):
            self.guardar('EXCESIVA', version=0)
        self.assertEqual(PercepcionServicio.objects.count(), 1)
        self.assertEqual(services.obtener_percepcion(self.servicio.pk, self.registro), original)

    def test_roles_aislados_inactivos_y_staff_no_registran(self):
        administrador = get_user_model().objects.create_user('administrador_fixture', is_staff=True)
        administrador.groups.add(Group.objects.get(name='Administración'))
        sin_rol = get_user_model().objects.create_user('staff_sin_rol', is_staff=True)
        for usuario in (self.cocina, administrador, sin_rol, None):
            with self.subTest(usuario=usuario), self.assertRaises(PermissionDenied):
                services.obtener_percepcion(self.servicio.pk, usuario)
            with self.assertRaises(PermissionDenied):
                services.registrar_percepcion(self.servicio.pk, 'ADECUADA', '', usuario, 0)
        self.registro.is_active = False
        with self.assertRaises(PermissionDenied):
            self.guardar()
        self.assertFalse(PercepcionServicio.objects.exists())

    def test_servicio_anulado_inexistente_o_uuid_invalido_no_se_modifica(self):
        for pk in (uuid4(), 'no-es-uuid'):
            with self.assertRaises(ServicioNoDisponible):
                services.obtener_percepcion(pk, self.registro)
        Servicio.objects.filter(pk=self.servicio.pk).update(estado_captura='ANULADO')
        with self.assertRaises(ServicioNoDisponible):
            self.guardar()
        self.assertFalse(PercepcionServicio.objects.exists())

    def test_validaciones_no_dependen_del_formulario(self):
        cambios = [dict(categoria='OTRA'), dict(motivo='x' * 1001), dict(motivo=None),
                   dict(categoria='NO_INFORMADO', motivo='No es una respuesta'),
                   dict(version=-1), dict(version=True), dict(version='0'), dict(version=2**31)]
        for cambio in cambios:
            with self.subTest(cambio=cambio), self.assertRaises(ValidationError):
                self.guardar(**cambio)
        self.assertFalse(PercepcionServicio.objects.exists())

    def test_fallo_de_insercion_revierte_cambio_de_vigencia(self):
        self.guardar()
        with patch('apps.historico.percepcion.PercepcionServicio.objects.create', side_effect=IntegrityError('fixture')):
            with self.assertRaises(ConflictoPercepcion):
                self.guardar('EXCESIVA', version=1)
        self.assertEqual(PercepcionServicio.objects.filter(vigente=True).get().categoria, 'ADECUADA')
        self.assertEqual(PercepcionServicio.objects.count(), 1)

    def test_restricciones_de_base_de_datos(self):
        self.guardar()
        casos = [dict(version=1, vigente=False, categoria='ADECUADA', motivo=''),
                 dict(version=2, vigente=True, categoria='ADECUADA', motivo=''),
                 dict(version=0, vigente=False, categoria='ADECUADA', motivo=''),
                 dict(version=2, vigente=False, categoria='OTRA', motivo=''),
                 dict(version=2, vigente=False, categoria='NO_INFORMADO', motivo='Texto')]
        for datos in casos:
            with self.subTest(datos=datos), self.assertRaises(IntegrityError), transaction.atomic():
                PercepcionServicio.objects.create(servicio=self.servicio, autor=self.registro, **datos)

    def test_no_modifica_captura_resultados_ni_indicadores(self):
        servicio, _, intento = self.caso(25)
        anterior = self.consulta()
        porcentajes = list(intento.resultados.values_list('pk', 'porcentaje'))
        services.registrar_percepcion(servicio.pk, 'INSUFICIENTE', 'Declaración de prueba', self.registro, 0)
        self.assertEqual(list(intento.resultados.values_list('pk', 'porcentaje')), porcentajes)
        self.assertEqual(self.consulta(), anterior)
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, 'PAR_COMPLETO')


class ConcurrenciaPercepcionTests(TransactionTestCase):
    def test_dos_operadores_no_crean_dos_versiones_iniciales_vigentes(self):
        call_command('cargar_catalogo_demo', verbosity=0)
        grupo = Group.objects.create(name='Registro')
        usuarios = [get_user_model().objects.create_user('concurrente_' + str(i)) for i in range(2)]
        for usuario in usuarios:
            usuario.groups.add(grupo)
        servicio = Servicio.registrar(plato=Plato.objects.get(codigo='seco_de_pollo'),
            porcion=TipoPorcion.objects.get(codigo='estandar'), usuario=usuarios[0])
        barrera = Barrier(2)
        def registrar(indice):
            try:
                usuario = get_user_model().objects.get(pk=usuarios[indice].pk)
                barrera.wait(timeout=5)
                services.registrar_percepcion(servicio.pk, ('INSUFICIENTE', 'EXCESIVA')[indice], '', usuario, 0)
                return 'guardado'
            except ConflictoPercepcion:
                return 'conflicto'
            finally:
                connections['default'].close()
        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            resultados = list(ejecutor.map(registrar, range(2)))
        self.assertLessEqual(resultados.count('guardado'), 1)
        self.assertIn('conflicto', resultados)
        self.assertLessEqual(PercepcionServicio.objects.count(), 1)
        if not PercepcionServicio.objects.exists():
            services.registrar_percepcion(servicio.pk, 'ADECUADA', '', usuarios[0], 0)
        self.assertEqual(PercepcionServicio.objects.filter(vigente=True).count(), 1)
        self.assertEqual(PercepcionServicio.objects.get().version, 1)
