"""Inferencia de segmentación por componente, sin inventar ausencia de alimento."""
import base64
from io import BytesIO
import math
import os
from pathlib import Path
from uuid import UUID

from PIL import Image, ImageChops
from .dataset import CLASES, MAX_BYTES, MAX_PIXELES


class EntradaInvalida(ValueError):
    pass


class PredictorYOLO:
    def __init__(self, pesos, *, device='cpu', imgsz=640):
        pesos = Path(pesos).resolve()
        if not pesos.is_file() or pesos.suffix.lower() != '.pt':
            raise EntradaInvalida('Se necesitan pesos .pt locales de segmentación entrenados para el catálogo.')
        runtime = Path(os.environ.get('EVA_VISUAL_RUNTIME', str(Path(__file__).resolve().parent / 'runtime')))
        runtime.mkdir(parents=True, exist_ok=True)
        os.environ['YOLO_CONFIG_DIR'] = str(runtime)
        from ultralytics import YOLO
        self.modelo = YOLO(str(pesos))
        if self.modelo.task != 'segment' or any(n not in CLASES for n in self.modelo.names.values()):
            raise EntradaInvalida('El modelo no segmenta las clases del piloto; no usar pesos COCO genéricos como modelo terminado.')
        self.device, self.imgsz = device, imgsz

    def __call__(self, imagen):
        resultado = self.modelo.predict(imagen, imgsz=self.imgsz, device=self.device,
            conf=0.8, retina_masks=True, max_det=64, verbose=False, save=False)[0]
        if resultado.masks is None:
            return []
        salidas = []
        for i, mascara in enumerate(resultado.masks.data):
            pixeles = (mascara.cpu().numpy() > 0.5).astype('uint8') * 255
            salidas.append(dict(codigo=self.modelo.names[int(resultado.boxes.cls[i].item())],
                confianza=float(resultado.boxes.conf[i].item()), mascara=Image.fromarray(pixeles)))
        return salidas


def _imagen(datos):
    if not isinstance(datos, bytes) or not datos or len(datos) > MAX_BYTES:
        raise EntradaInvalida('Foto vacía o mayor que 10 MiB.')
    try:
        with Image.open(BytesIO(datos)) as imagen:
            if (imagen.format not in ('JPEG', 'PNG') or imagen.width * imagen.height > MAX_PIXELES
                    or getattr(imagen, 'n_frames', 1) != 1 or imagen.getexif().get(274, 1) != 1):
                raise EntradaInvalida('Foto sin normalizar, animada o fuera de los formatos/límites admitidos.')
            imagen.load()
            return imagen.convert('RGB')
    except (OSError, Image.DecompressionBombError) as exc:
        raise EntradaInvalida('Fotografía ilegible.') from exc


def _metadata(metadata):
    if (not isinstance(metadata, dict) or type(metadata.get('schema_version')) is not int or metadata['schema_version'] != 1
            or metadata.get('origen') not in ('REAL', 'SIMULADO')):
        raise EntradaInvalida('Metadata incompatible con el protocolo v1.')
    for campo in ('request_id', 'servicio_id'):
        try:
            UUID(str(metadata.get(campo)))
        except (ValueError, AttributeError):
            raise EntradaInvalida('Identificador inválido.') from None
    for campo in ('version_modelo', 'version_configuracion'):
        if not isinstance(metadata.get(campo), str) or not 1 <= len(metadata[campo]) <= 50:
            raise EntradaInvalida('Falta una versión del modelo o configuración.')
    componentes = metadata.get('componentes')
    if not isinstance(componentes, list) or not 1 <= len(componentes) <= 32:
        raise EntradaInvalida('Composición vacía o demasiado grande.')
    ids, codigos = set(), set()
    for componente in componentes:
        if not isinstance(componente, dict) or componente.get('codigo') not in CLASES:
            raise EntradaInvalida('Componente ajeno al catálogo del piloto.')
        valor_id = componente.get('id')
        if type(valor_id) not in (str, int):
            raise EntradaInvalida('Identificador de componente inválido.')
        texto_id = str(valor_id)
        if texto_id.isascii() and texto_id.isdigit() and len(texto_id) <= 20:
            if not 0 < int(texto_id) < 2**63 or str(int(texto_id)) != texto_id:
                raise EntradaInvalida('Identificador de componente inválido.')
            identificador = texto_id
        else:
            try:
                identificador = str(UUID(texto_id))
            except (ValueError, AttributeError):
                raise EntradaInvalida('Identificador de componente inválido.') from None
        if identificador in ids or componente['codigo'] in codigos:
            raise EntradaInvalida('Composición con componentes duplicados.')
        ids.add(identificador)
        codigos.add(componente['codigo'])
    return componentes


def _segmentar(imagen, predictor, codigos):
    uniones, confianzas, ambiguos = {}, {}, set()
    ajenos = False
    for objeto in predictor(imagen):
        codigo, confianza, mascara = (objeto.get(k) for k in ('codigo', 'confianza', 'mascara'))
        if codigo not in codigos:
            ajenos = True
            continue
        if (type(confianza) not in (int, float) or not math.isfinite(confianza) or not 0 <= confianza <= 1
                or not isinstance(mascara, Image.Image) or mascara.size != imagen.size or mascara.mode != 'L'
                or sum(mascara.histogram()[1:255])):
            raise EntradaInvalida('La predicción no contiene máscaras binarias alineadas o confianza válida.')
        if not mascara.getbbox():
            continue
        uniones[codigo] = ImageChops.lighter(uniones[codigo], mascara) if codigo in uniones else mascara.copy()
        confianzas[codigo] = min(confianzas.get(codigo, 1), confianza)
    compartidos = None
    for i, codigo in enumerate(uniones):
        for otro in list(uniones)[i+1:]:
            interseccion = ImageChops.darker(uniones[codigo], uniones[otro])
            if interseccion.getbbox():
                ambiguos.update([codigo, otro])
                compartidos = ImageChops.lighter(compartidos, interseccion) if compartidos is not None else interseccion
    if compartidos is not None:
        # No asignar al ganador: quitar los píxeles ambiguos de todas las clases.
        # Las zonas restantes sirven para revisión, nunca como porcentaje válido.
        for codigo in uniones:
            uniones[codigo] = ImageChops.subtract(uniones[codigo], compartidos)
    return uniones, confianzas, ambiguos, ajenos


def analizar(metadata, servido, retorno, predictor, *, version_modelo, identidad_verificada=False):
    componentes = _metadata(metadata)
    if metadata['version_modelo'] != version_modelo:
        raise EntradaInvalida('La versión solicitada no coincide con los pesos configurados.')
    fotos = dict(SERVIDO=_imagen(servido), RETORNO=_imagen(retorno))
    codigos = {c['codigo'] for c in componentes}
    segmentaciones = {etapa: _segmentar(imagen, predictor, codigos) for etapa, imagen in fotos.items()}
    identidad = identidad_verificada is True and fotos['SERVIDO'].size == fotos['RETORNO'].size
    componentes_salida = []
    for comp in componentes:
        codigo = comp['codigo']
        mascaras, areas, confianza = [], {}, []
        ambiguo = any(codigo in s[2] for s in segmentaciones.values())
        for etapa, (uniones, confianzas, _, _) in segmentaciones.items():
            if codigo not in uniones or not uniones[codigo].getbbox():
                continue
            mascara = uniones[codigo]
            salida = BytesIO()
            mascara.save(salida, 'PNG')
            if salida.tell() > 8 * 1024 * 1024:
                raise EntradaInvalida('La máscara supera el límite del cliente.')
            mascaras.append(dict(etapa=etapa, png_base64=base64.b64encode(salida.getvalue()).decode('ascii'),
                                  ancho=mascara.width, alto=mascara.height))
            areas[etapa] = mascara.histogram()[255]
            confianza.append(confianzas[codigo])
        completo = len(mascaras) == 2
        componentes_salida.append(dict(id=comp['id'], area_inicial=areas.get('SERVIDO'),
            area_residual=areas.get('RETORNO'), confianza=min(confianza) if completo else None,
            comparable=bool(identidad and completo and not ambiguo and not any(s[3] for s in segmentaciones.values())),
            oculto=False, mascaras=mascaras))
    return dict(schema_version=1, request_id=metadata['request_id'], version_modelo=version_modelo,
        version_configuracion=metadata['version_configuracion'], origen=metadata['origen'],
        transformacion=dict(tipo='IDENTIDAD' if identidad else 'NO_VERIFICADA', escala_comun=identidad),
        componentes=componentes_salida)
