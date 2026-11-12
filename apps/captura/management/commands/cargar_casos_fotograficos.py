"""Casos privados con fotografías e inferencia ONNX en la presentación aislada."""
import hashlib
import json
from pathlib import Path
import re
from uuid import NAMESPACE_URL, uuid5

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.analisis import motor, services
from apps.analisis.models import ArtefactoAnalisis
from apps.captura import contexto, protocolo, storage
from apps.captura.models import AsignacionBandeja, Bandeja, EtiquetaBandeja, FotografiaServicio, Servicio, ServicioComponente
from apps.catalogo.models import Plato, TipoPorcion
from apps.catalogo.permissions import COCINA, REGISTRO, tiene_rol
from ops.presentacion.aislamiento import lote_activo


def leer_casos(manifiesto):
    raiz = manifiesto.resolve().parent
    datos = json.loads(manifiesto.read_text(encoding='utf-8'))
    casos = datos.get('casos', [])
    if datos.get('schema_version') != 1 or not 1 <= len(casos) <= 10:
        raise CommandError('El manifiesto debe contener entre uno y diez casos.')
    claves = set()
    for caso in casos:
        clave = caso.get('clave', '')
        if not re.fullmatch(r'[a-z0-9-]{1,32}', clave) or clave in claves:
            raise CommandError('Las claves deben ser únicas, cortas y sin espacios.')
        claves.add(clave)
        if not isinstance(caso.get('nota'), str) or not 1 <= len(caso['nota']) <= 500:
            raise CommandError('Cada caso debe explicar la procedencia de sus fotos.')
        for etapa in ('servido', 'retorno'):
            ruta = (raiz / caso[etapa]).resolve()
            if not ruta.is_relative_to(raiz) or not ruta.is_file():
                raise CommandError('Las fotografías deben estar dentro del paquete privado.')
            if hashlib.sha256(ruta.read_bytes()).hexdigest() != caso[etapa + '_sha256']:
                raise CommandError('La fotografía no coincide con el manifiesto.')
            caso[etapa] = ruta
    return casos


class Command(BaseCommand):
    help = 'Previsualiza o carga casos fotográficos sin modificar la base operativa.'

    def add_arguments(self, parser):
        parser.add_argument('--manifiesto', type=Path, required=True)
        parser.add_argument('--registro')
        parser.add_argument('--cocina')
        parser.add_argument('--pesos', type=Path)
        parser.add_argument('--aplicar', action='store_true')

    def handle(self, **opciones):
        lote = lote_activo()
        if not lote:
            raise CommandError('Los casos fotográficos requieren la presentación aislada.')
        casos = leer_casos(opciones['manifiesto'])
        self.stdout.write(f'{len(casos)} casos fotográficos · Base de presentación: {settings.DATABASES["default"]["NAME"]}')
        if not opciones['aplicar']:
            return
        from visual_service.inference import _imagen, analizar
        from visual_service.onnx_inference import PredictorONNX
        pesos = opciones['pesos']
        if not pesos or not pesos.is_file():
            raise CommandError('Indica los pesos ONNX vigentes y privados.')
        usuarios = {}
        for campo, rol in (('registro', REGISTRO), ('cocina', COCINA)):
            usuario = get_user_model().objects.filter(username=opciones[campo]).first()
            if usuario is None or not tiene_rol(usuario, rol):
                raise CommandError(f'Falta una cuenta activa de {rol}.')
            usuarios[campo] = usuario
        predictor = PredictorONNX(pesos)
        version = 'sha256-' + hashlib.sha256(pesos.read_bytes()).hexdigest()[:40]
        recibo = []
        for indice, caso in enumerate(casos, 1):
            identificador = uuid5(NAMESPACE_URL, f'eva-fotografico:{lote}:{caso["clave"]}')
            fotos = {e.upper(): caso[e].read_bytes() for e in ('servido', 'retorno')}
            geometrias = {e: _imagen(datos).size for e, datos in fotos.items()}
            claves_nuevas = []
            try:
                with transaction.atomic():
                    servicio = Servicio.objects.filter(pk=identificador).first()
                    if servicio is None:
                        plato = Plato.objects.get(codigo=caso['plato'], activo=True)
                        porcion = TipoPorcion.objects.get(codigo='estandar', activo=True)
                        servicio = Servicio.objects.create(id=identificador, plato=plato.codigo, plato_nombre=plato.nombre,
                            tipo_porcion=porcion.codigo, porcion_nombre=porcion.nombre, plato_catalogo=plato,
                            porcion_catalogo=porcion, creado_por=usuarios['registro'], estado_captura='PAR_COMPLETO',
                            contexto_snapshot={**contexto.preparar(dict(sede='principal', modalidad='mesa',
                            lote_preparacion=caso['clave'])), 'nota_presentacion': caso['nota']})
                        bandeja, nueva = Bandeja.objects.get_or_create(numero=900100 + indice)
                        if not nueva:
                            raise CommandError('El número de bandeja del caso ya está en uso.')
                        EtiquetaBandeja.objects.create(bandeja=bandeja)
                        asignacion = AsignacionBandeja.objects.create(bandeja=bandeja, servicio=servicio)
                        for relacion in plato.relaciones.filter(activo=True, componente__activo=True).select_related('componente'):
                            ServicioComponente.objects.create(servicio=servicio, componente_codigo=relacion.componente.codigo,
                                                              componente_nombre=relacion.componente.nombre)
                        for etapa, datos in fotos.items():
                            clave = f'casos-fotograficos/{servicio.pk}/{etapa.lower()}.png'
                            guardado = storage.guardar(datos, clave, tipo_contenido='image/png', backend='local')
                            claves_nuevas.append(clave)
                            ancho, alto = geometrias[etapa]
                            foto = FotografiaServicio.objects.create(servicio=servicio, etapa=etapa, backend='local',
                                clave_archivo=clave, tipo_contenido='image/png' if datos.startswith(b'\x89PNG') else 'image/jpeg',
                                tamano_bytes=len(datos), hash_sha256=guardado.hash_sha256, ancho=ancho, alto=alto,
                                autor=usuarios['registro'], protocolo_version=protocolo.VERSION,
                                checklist=dict.fromkeys(protocolo.CRITERIOS, True))
                            if etapa == 'SERVIDO':
                                contexto.fijar_servido(servicio, foto)
                        asignacion.fin = foto.fecha
                        asignacion.save(update_fields=['fin'])
                    else:
                        for etapa, datos in fotos.items():
                            foto = servicio.fotografias.get(etapa=etapa, vigente=True)
                            if foto.hash_sha256 != hashlib.sha256(datos).hexdigest():
                                raise CommandError('Un caso existente tiene fotografías diferentes; no se sobrescribe.')
            except BaseException:
                for clave in claves_nuevas:
                    storage.eliminar(clave, backend='local')
                raise
            analisis, intento, _ = services.solicitar_analisis(servicio=servicio, solicitante=usuarios['cocina'],
                version_modelo=version, version_configuracion=settings.EVA_ANALISIS_CRITERIOS['version'], origen='SIMULADO')
            if intento.estado == 'PENDIENTE':
                reclamado = services.reclamar_siguiente_intento()
                if reclamado is None or reclamado.pk != intento.pk:
                    raise CommandError('Hay otra tarea pendiente; detén el worker antes de preparar los casos.')
                componentes = list(servicio.composicion.all())
                metadata = dict(schema_version=1, request_id=str(intento.pk), servicio_id=str(servicio.pk),
                    version_modelo=version, version_configuracion=analisis.version_configuracion, origen='SIMULADO',
                    componentes=[dict(id=str(c.pk), codigo=c.componente_codigo) for c in componentes])
                respuesta = analizar(metadata, fotos['SERVIDO'], fotos['RETORNO'], predictor,
                                     version_modelo=version, identidad_verificada=False)
                resultados, archivos = motor.validar(respuesta, intento, componentes)
                artefactos = []
                for numero, archivo in enumerate(archivos):
                    clave = f'casos-fotograficos/{servicio.pk}/mascara-{intento.pk}-{numero}.png'
                    guardado = storage.guardar(archivo['datos'], clave, tipo_contenido='image/png', backend='local')
                    artefactos.append(dict(servicio_componente=archivo['servicio_componente'], etapa=archivo['etapa'],
                        clave_archivo=guardado.clave, backend='local', hash_sha256=guardado.hash_sha256,
                        ancho=archivo['ancho'], alto=archivo['alto']))
                services.completar_intento(intento=intento, request_id=str(intento.pk), version_modelo=version,
                    version_configuracion=analisis.version_configuracion, origen='SIMULADO', resultados=resultados, artefactos=artefactos)
            intento.refresh_from_db()
            recibo.append(dict(servicio=str(servicio.pk), bandeja=900100+indice, analisis=str(analisis.pk),
                estado=intento.estado, mascaras=ArtefactoAnalisis.objects.filter(resultado__intento=intento).count(),
                resultados=list(intento.resultados.values('estado','motivo','porcentaje'))))
        salida = Path(settings.EVA_CAPTURE_PRIVATE_ROOT).parent / 'casos-fotograficos-resultados.json'
        salida.write_text(json.dumps(dict(version_modelo=version, casos=recibo), default=str, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Casos preparados: {len(recibo)}. Fotografías y máscaras privadas.'))
