"""Carga reversible de un lote simulado en la configuración local."""
from collections import defaultdict
from datetime import datetime, timedelta
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models.deletion import ProtectedError

from apps.analisis.models import AnalisisServicio, IntentoAnalisis, ResultadoComponente, RevisionAnalisis
from apps.captura import contexto, protocolo, storage
from apps.captura.models import AsignacionBandeja, Bandeja, EtiquetaBandeja, FotografiaServicio, Servicio, ServicioComponente
from apps.catalogo.models import Plato, TipoPorcion
from apps.catalogo.permissions import ADMINISTRACION, COCINA, REGISTRO, tiene_rol
from apps.historico.models import PercepcionServicio
from apps.recomendaciones import models as recomendaciones, services
from ops.presentacion.aislamiento import lote_activo
from ops.presentacion.planificar import PLATOS, PORCIONES, construir

ORDEN = (
    recomendaciones.EvaluacionPrueba, recomendaciones.PruebaControlada,
    recomendaciones.DecisionRecomendacion, recomendaciones.Recomendacion,
    recomendaciones.EvaluacionEvidencia, PercepcionServicio, RevisionAnalisis,
    ResultadoComponente, IntentoAnalisis, AnalisisServicio, FotografiaServicio,
    AsignacionBandeja, ServicioComponente, Servicio, EtiquetaBandeja, Bandeja,
)
PERIODO = dict(desde='2026-10-05', hasta='2026-10-18')


def imagen(etapa):
    """Lámina sintética común a cada etapa, marcada incluso fuera de la interfaz."""
    lienzo = Image.new('RGB', (640, 420), '#f5ebd2')
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.ellipse((200, 56, 440, 296), fill='#fffcf1', outline='#b7a47b', width=4)
    dibujo.text((320, 165), 'ILUSTRACION DE EJEMPLO', fill='#292315', anchor='mm')
    dibujo.text((320, 345), etapa, fill='#292315', anchor='mm')
    salida = BytesIO()
    lienzo.save(salida, format='PNG')
    return salida.getvalue()


class Command(BaseCommand):
    help = 'Previsualiza, carga o retira los datos ficticios de la base local de presentación.'

    def add_arguments(self, parser):
        modos = parser.add_mutually_exclusive_group()
        modos.add_argument('--aplicar', action='store_true')
        modos.add_argument('--retirar', action='store_true')
        parser.add_argument('--confirmar')
        for rol in ('registro', 'cocina', 'administracion'):
            parser.add_argument(f'--{rol}')

    def handle(self, **opciones):
        lote = lote_activo()
        if not lote:
            raise CommandError('Selecciona la configuración local de presentación.')
        plan = construir(lote)['servicios']
        self.stdout.write(f'Lote {lote} · Destino {connection.settings_dict["NAME"]}')
        self.stdout.write('288 servicios · 6 bandejas · 576 láminas · 240 análisis simulados · 48 sin análisis')
        if not (opciones['aplicar'] or opciones['retirar']):
            return
        if opciones['confirmar'] != lote:
            raise CommandError('Confirma el identificador exacto del lote.')
        self.archivos = {}
        self.propios = defaultdict(list)
        self.raiz = Path(settings.EVA_CAPTURE_PRIVATE_ROOT)
        if opciones['retirar']:
            self.retirar(lote)
            return
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute('CREATE TABLE IF NOT EXISTS eva_presentacion_recibo '
                               '(lote TEXT PRIMARY KEY, inventario TEXT NOT NULL, retirado INTEGER DEFAULT 0)')
                cursor.execute('SELECT retirado FROM eva_presentacion_recibo WHERE lote=%s', [lote])
                previo = cursor.fetchone()
                if previo:
                    if previo[0]:
                        raise CommandError('Completa la retirada pendiente antes de volver a cargar.')
                    self.stdout.write('El lote ya está cargado.')
                    return
                usuarios = self.usuarios(opciones)
                self.cargar(plan, lote, usuarios)
                cursor.execute('INSERT INTO eva_presentacion_recibo(lote,inventario) VALUES(%s,%s)',
                               [lote, json.dumps(dict(filas=self.propios, archivos=self.archivos))])
        except BaseException:
            self.borrar_archivos(self.archivos)
            raise
        self.stdout.write(self.style.SUCCESS('Carga local completada.'))

    def usuarios(self, opciones):
        salida = {}
        for clave, rol in [('registro', REGISTRO), ('cocina', COCINA), ('administracion', ADMINISTRACION)]:
            usuario = get_user_model().objects.filter(username=opciones[clave]).first()
            if usuario is None or not tiene_rol(usuario, rol):
                raise CommandError(f'Indica una cuenta local activa del rol {rol} con --{clave}.')
            salida[clave] = usuario
        return salida

    def registrar(self, instancia):
        self.propios[instancia._meta.label].append(str(instancia.pk))
        return instancia

    def crear(self, modelo, **campos):
        return self.registrar(modelo.objects.create(**campos))

    def captura(self, servicio, etapa, fecha, usuario, lote, contenido):
        clave = f'presentacion/{lote}/{servicio.pk}/{etapa.lower()}.png'
        guardado = storage.guardar(contenido, clave, tipo_contenido='image/png', backend='local')
        self.archivos[clave] = guardado.hash_sha256
        foto = self.crear(FotografiaServicio, servicio=servicio, etapa=etapa, backend='local',
                          clave_archivo=clave, tipo_contenido='image/png', tamano_bytes=len(contenido),
                          hash_sha256=guardado.hash_sha256, ancho=640, alto=420, autor=usuario,
                          protocolo_version=protocolo.VERSION, checklist=dict.fromkeys(protocolo.CRITERIOS, True))
        FotografiaServicio.objects.filter(pk=foto.pk).update(fecha=fecha)
        foto.fecha = fecha
        return foto

    def cargar(self, plan, lote, usuarios):
        registro, cocina = usuarios['registro'], usuarios['cocina']
        platos = {p.codigo: p for p in Plato.objects.filter(codigo__in=PLATOS, activo=True)}
        porciones = {p.codigo: p for p in TipoPorcion.objects.filter(codigo__in=PORCIONES, activo=True)}
        if set(platos) != set(PLATOS) or set(porciones) != set(PORCIONES):
            raise CommandError('Prepara el catálogo local con los tres platos y ambas porciones activas.')
        componentes = {}
        for codigo, plato in platos.items():
            nombres = {r.componente.codigo: r.componente.nombre for r in plato.relaciones.filter(activo=True, componente__activo=True).select_related("componente")}
            if set(nombres) != set(PLATOS[codigo]):
                raise CommandError(f'La composición activa de {codigo} difiere del manifiesto.')
            componentes[codigo] = nombres
        bandejas = {n: self.crear(Bandeja, numero=900000 + n) for n in range(1, 7)}
        for bandeja in bandejas.values():
            self.crear(EtiquetaBandeja, bandeja=bandeja, emitida_en=datetime.fromisoformat(plan[0]['servido']))
        laminas = {etapa: imagen(etapa) for etapa in ('SERVIDO', 'RETORNO')}
        for fila in plan:
            servido, retorno = (datetime.fromisoformat(fila[campo]) for campo in ('servido', 'retorno'))
            plato, porcion = platos[fila['plato']], porciones[fila['porcion']]
            servicio = self.crear(Servicio, id=fila['id'], plato=plato.codigo, plato_nombre=plato.nombre,
                                  tipo_porcion=porcion.codigo, porcion_nombre=porcion.nombre,
                                  plato_catalogo=plato, porcion_catalogo=porcion, creado_por=registro,
                                  estado_captura='PAR_COMPLETO', contexto_snapshot=contexto.preparar(fila))
            Servicio.objects.filter(pk=servicio.pk).update(fecha_creacion=servido - timedelta(minutes=1))
            self.crear(AsignacionBandeja, bandeja=bandejas[fila['bandeja']], servicio=servicio,
                       inicio=servido - timedelta(seconds=30), fin=retorno)
            composicion = {codigo: self.crear(ServicioComponente, servicio=servicio, componente_codigo=codigo,
                                             componente_nombre=nombre)
                           for codigo, nombre in componentes[plato.codigo].items()}
            inicial = self.captura(servicio, 'SERVIDO', servido, registro, lote, laminas['SERVIDO'])
            contexto.fijar_servido(servicio, inicial)
            final = self.captura(servicio, 'RETORNO', retorno, registro, lote, laminas['RETORNO'])
            if fila['mediciones_sinteticas']:
                self.analisis(lote, servicio, inicial, final, composicion, fila['mediciones_sinteticas'], cocina)
            if fila['percepcion']:
                self.crear(PercepcionServicio, servicio=servicio, categoria=fila['percepcion'],
                           autor=cocina, version=1, motivo='Respuesta ficticia de presentación.')
        self.recomendar(usuarios['administracion'], cocina)

    def analisis(self, lote, servicio, inicial, final, composicion, mediciones, cocina):
        analisis = self.crear(AnalisisServicio, servicio=servicio, foto_servido=inicial, foto_retorno=final,
                              version_modelo=f'presentacion-{lote}', version_configuracion='presentacion-mediciones-v1',
                              origen='SIMULADO', solicitante=cocina)
        fecha = final.fecha + timedelta(minutes=1)
        intento = self.crear(IntentoAnalisis, analisis=analisis, numero=1, estado='COMPLETADO',
                             comenzado_en=fecha, finalizado_en=fecha)
        AnalisisServicio.objects.filter(pk=analisis.pk).update(intento_vigente=intento, creado_en=fecha)
        IntentoAnalisis.objects.filter(pk=intento.pk).update(creado_en=fecha)
        for codigo, valores in mediciones.items():
            area, residual = valores['area_servido'], valores['area_retorno']
            self.crear(ResultadoComponente, intento=intento, servicio_componente=composicion[codigo],
                       area_inicial=area, area_residual=residual, porcentaje=100 * residual / area,
                       confianza=0.90, umbral_aplicado=0.80, criterio='presentacion-mediciones-v1',
                       configuracion_aprobada=True, estado='CONCLUYENTE')
        revision = self.crear(RevisionAnalisis, intento=intento, decision='CONFIRMADO', version=1,
                              autor=cocina, motivo='Revisión ficticia de presentación.')
        RevisionAnalisis.objects.filter(pk=revision.pk).update(fecha=fecha + timedelta(minutes=1))

    def recomendar(self, admin, cocina):
        version = settings.EVA_RECOMENDACIONES_CRITERIOS['version']
        for plato, componente, categoria in (
            ('encebollado', 'yuca', 'MANTENER'),
            ('seco_de_pollo', 'pollo', 'REVISAR_PORCION'),
            ('arroz_menestra_carne', 'menestra', 'PRUEBA_CONTROLADA'),
        ):
            caso = services.evaluar_evidencia(dict(PERIODO, plato=plato, componente=componente, porcion='estandar'),
                                             version, admin)
            evidencia = self.registrar(recomendaciones.EvaluacionEvidencia.objects.get(pk=caso['evaluacion']['id']))
            caso = services.generar_recomendacion(evidencia.pk, admin)
            recomendacion = self.registrar(recomendaciones.Recomendacion.objects.get(evaluacion=evidencia))
            if recomendacion.categoria != categoria:
                raise CommandError(f'La evidencia de ejemplo de {componente} produjo {recomendacion.categoria}.')
            services.decidir_recomendacion(recomendacion.pk, 'ACEPTADA',
                                           'Decisión ficticia para el recorrido de presentación.', admin, 0)
            self.registrar(recomendacion.decisiones.get())
            if categoria == 'PRUEBA_CONTROLADA':
                detalle = services.registrar_prueba(recomendacion.pk, 'Revisar el tamaño de la porción de menestra.',
                                                    cocina.pk, dict(referencia_desde='2026-10-05',
                                                    referencia_hasta='2026-10-18', intervencion_desde='2026-10-19',
                                                    intervencion_hasta='2026-11-01'), admin)
                prueba = self.registrar(recomendacion.pruebas.get(pk=detalle['prueba']['id']))
                services.evaluar_prueba(prueba.pk, admin, prueba.version)
                self.registrar(prueba.evaluaciones.get())

    def borrar_archivos(self, inventario, comprobar=False):
        rutas = []
        for clave, huella in inventario.items():
            ruta = self.raiz / clave
            if ruta.is_symlink() or not ruta.resolve().is_relative_to(self.raiz.resolve()):
                raise CommandError('La ruta de una lámina cambió. Revisa el lote local.')
            if ruta.exists():
                if sha256(ruta.read_bytes()).hexdigest() != huella:
                    raise CommandError(f'El archivo {clave} cambió. Revisa el lote local.')
                rutas.append(ruta)
        if not comprobar:
            for ruta in rutas:
                ruta.unlink(missing_ok=True)

    def retirar(self, lote):
        with connection.cursor() as cursor:
            if 'eva_presentacion_recibo' not in connection.introspection.table_names():
                self.stdout.write('No hay una carga registrada.')
                return
            cursor.execute('SELECT inventario, retirado FROM eva_presentacion_recibo WHERE lote=%s', [lote])
            fila = cursor.fetchone()
            if not fila:
                self.stdout.write('No hay una carga registrada.')
                return
            recibo, retirado = json.loads(fila[0]), fila[1]
            self.borrar_archivos(recibo['archivos'], comprobar=True)
            if not retirado:
                filas = recibo['filas']
                try:
                    with transaction.atomic():
                        AnalisisServicio.objects.filter(pk__in=filas[AnalisisServicio._meta.label]).update(intento_vigente=None)
                        for modelo in ORDEN:
                            modelo.objects.filter(pk__in=filas.get(modelo._meta.label, [])).delete()
                        cursor.execute('UPDATE eva_presentacion_recibo SET retirado=1 WHERE lote=%s', [lote])
                except ProtectedError as error:
                    raise CommandError('El lote tiene registros relacionados ajenos a la carga. No se retiró.') from error
            self.borrar_archivos(recibo['archivos'])
            cursor.execute('DELETE FROM eva_presentacion_recibo WHERE lote=%s', [lote])
        self.stdout.write(self.style.SUCCESS('Lote local retirado.'))
