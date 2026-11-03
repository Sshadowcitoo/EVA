"""Validación reproducible del dataset, antes de entrenar o aumentar imágenes."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, UnidentifiedImageError

CLASES = ('yuca', 'pescado', 'arroz', 'pollo', 'maduro', 'menestra', 'carne', 'ensalada')
PARTICIONES = ('train', 'val', 'test')
MAX_PIXELES = 20_000_000
MAX_BYTES = 10 * 1024 * 1024
MAX_VERTICES = 2048


class DatasetInvalido(ValueError):
    pass


def _poligono_simple(xy):
    """Rechaza cruces y contactos entre bordes no adyacentes, sin rasterizar."""
    if len(xy) < 3 or len(xy) > MAX_VERTICES or len(set(xy)) != len(xy):
        return False
    eps = 1e-12

    def orientacion(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    def sobre(a, b, c):
        return (min(a[0],b[0])-eps <= c[0] <= max(a[0],b[0])+eps
                and min(a[1],b[1])-eps <= c[1] <= max(a[1],b[1])+eps)

    n = len(xy)
    for i in range(n):
        a, b = xy[i], xy[(i+1) % n]
        for j in range(i+1,n):
            if j == i+1 or (i == 0 and j == n-1):
                continue
            c, d = xy[j], xy[(j+1) % n]
            if (max(a[0],b[0])+eps < min(c[0],d[0]) or max(c[0],d[0])+eps < min(a[0],b[0])
                    or max(a[1],b[1])+eps < min(c[1],d[1]) or max(c[1],d[1])+eps < min(a[1],b[1])):
                continue
            o1, o2, o3, o4 = orientacion(a,b,c), orientacion(a,b,d), orientacion(c,d,a), orientacion(c,d,b)
            if ((o1 > eps and o2 < -eps or o1 < -eps and o2 > eps)
                    and (o3 > eps and o4 < -eps or o3 < -eps and o4 > eps)):
                return False
            if (abs(o1) <= eps and sobre(a,b,c) or abs(o2) <= eps and sobre(a,b,d)
                    or abs(o3) <= eps and sobre(c,d,a) or abs(o4) <= eps and sobre(c,d,b)):
                return False
    return True


def _ruta(raiz, relativo):
    if not isinstance(relativo, str) or not relativo or Path(relativo).is_absolute():
        raise DatasetInvalido('Las rutas del manifiesto deben ser relativas a su carpeta.')
    ruta = (raiz / relativo).resolve()
    if not ruta.is_relative_to(raiz) or not ruta.is_file():
        raise DatasetInvalido(f'Archivo ausente o fuera del dataset: {relativo}')
    return ruta


def leer_poligonos(ruta, cantidad_clases, vacio_confirmado=False):
    if ruta.stat().st_size > 1024 * 1024:
        raise DatasetInvalido('Archivo de anotaciones demasiado grande.')
    try:
        lineas = ruta.read_text(encoding='utf-8-sig').splitlines()
    except (OSError, UnicodeError) as exc:
        raise DatasetInvalido('Anotaciones ilegibles.') from exc
    poligonos = []
    for numero, linea in enumerate(lineas, 1):
        campos = linea.split()
        if not campos:
            continue
        try:
            if not campos[0].isascii() or not campos[0].isdigit():
                raise ValueError()
            clase = int(campos[0])
            puntos = [float(v) for v in campos[1:]]
            if (not 0 <= clase < cantidad_clases or len(puntos) < 6 or len(puntos) % 2
                    or any(not math.isfinite(v) or not 0 <= v <= 1 for v in puntos)):
                raise ValueError()
            xy = list(zip(puntos[::2], puntos[1::2]))
            if len(xy) > 1 and xy[0] == xy[-1]:
                xy.pop()  # Algunos exportadores repiten el vértice inicial al cerrar.
            if not _poligono_simple(xy):
                raise ValueError()
            area = abs(sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(xy, xy[1:] + xy[:1]))) / 2
            if area <= 0:
                raise ValueError()
        except (ValueError, OverflowError):
            raise DatasetInvalido(f'Polígono YOLO inválido en {ruta.name}, línea {numero}.') from None
        poligonos.append((clase, xy))
    if not poligonos and vacio_confirmado is not True:
        raise DatasetInvalido('Etiquetas vacías: confirma explícitamente que no hay alimentos anotables.')
    return poligonos


def validar(manifiesto):
    manifiesto = Path(manifiesto).resolve()
    if not manifiesto.is_file() or manifiesto.stat().st_size > 5 * 1024 * 1024:
        raise DatasetInvalido('Manifiesto ausente o demasiado grande.')
    try:
        datos = json.loads(manifiesto.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError, UnicodeError) as exc:
        raise DatasetInvalido('El manifiesto debe ser JSON válido.') from exc
    if not isinstance(datos, dict) or type(datos.get('schema_version')) is not int or datos['schema_version'] != 1:
        raise DatasetInvalido('schema_version debe ser 1.')
    clases = datos.get('clases')
    if (not isinstance(clases, list) or not clases or any(not isinstance(c, str) or c not in CLASES for c in clases)
            or len(set(clases)) != len(clases)):
        raise DatasetInvalido('Declara una lista sin duplicados de componentes del piloto.')
    imagenes = datos.get('imagenes')
    if not isinstance(imagenes, list) or not imagenes:
        raise DatasetInvalido('No hay imágenes declaradas.')
    raiz = manifiesto.parent
    grupos, hashes, archivos = {}, {}, set()
    resumen = {p: dict(imagenes=0, grupos=set(), clases=Counter(), reales=0, sinteticas=0) for p in PARTICIONES}
    entradas, advertencias = [], []
    grupos_reales = set()
    for entrada in imagenes:
        if not isinstance(entrada, dict):
            raise DatasetInvalido('Cada imagen debe ser un objeto JSON.')
        particion, grupo, origen = (entrada.get(k) for k in ('particion', 'grupo', 'origen'))
        if (particion not in PARTICIONES or not isinstance(grupo, str) or not grupo.strip()
                or len(grupo) > 100 or origen not in ('REAL', 'SINTETICO')):
            raise DatasetInvalido('Define partición, grupo de preparación y origen de cada imagen.')
        grupo = grupo.strip()
        if grupo in grupos and grupos[grupo] != particion:
            raise DatasetInvalido(f'Fuga de datos: la preparación {grupo} aparece en varias particiones.')
        grupos[grupo] = particion
        if origen == 'SINTETICO' and particion != 'train':
            raise DatasetInvalido('Las variantes sintéticas solo pertenecen a train.')
        if origen == 'REAL':
            grupos_reales.add(grupo)
        foto, etiquetas = _ruta(raiz, entrada.get('archivo')), _ruta(raiz, entrada.get('etiquetas'))
        if foto in archivos:
            raise DatasetInvalido('La misma foto aparece más de una vez en el manifiesto.')
        archivos.add(foto)
        if foto.stat().st_size > MAX_BYTES:
            raise DatasetInvalido('Imagen mayor que 10 MiB.')
        try:
            with Image.open(foto) as imagen:
                if (imagen.format not in ('JPEG', 'PNG') or imagen.width * imagen.height > MAX_PIXELES
                        or getattr(imagen, 'n_frames', 1) != 1 or imagen.getexif().get(274, 1) != 1):
                    raise DatasetInvalido('Usa JPEG/PNG sin animación, con orientación normalizada y hasta 20 MP.')
                imagen.load()
                # Huella de píxeles: también detecta copias con nombres o EXIF distintos.
                huella = hashlib.sha256(str(imagen.size).encode() + imagen.convert('RGB').tobytes()).hexdigest()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise DatasetInvalido(f'Imagen ilegible: {foto.name}') from exc
        if huella in hashes and hashes[huella] != particion:
            raise DatasetInvalido('Fuga de datos: píxeles idénticos aparecen en distintas particiones.')
        if huella in hashes:
            advertencias.append(f'Imagen duplicada dentro de {particion}: {foto.name}')
        hashes[huella] = particion
        poligonos = leer_poligonos(etiquetas, len(clases), entrada.get('vacio_confirmado', False))
        estado = resumen[particion]
        estado['imagenes'] += 1
        estado['grupos'].add(grupo)
        estado['clases'].update(clases[c] for c, _ in poligonos)
        estado['reales' if origen == 'REAL' else 'sinteticas'] += 1
        entradas.append(dict(archivo=foto, etiquetas=etiquetas, particion=particion, grupo=grupo, origen=origen))
    if set(grupos) - grupos_reales:
        raise DatasetInvalido('Cada grupo necesita al menos una captura REAL de origen.')
    for particion, estado in resumen.items():
        if not estado['imagenes']:
            raise DatasetInvalido(f'Falta una preparación independiente para {particion}.')
        faltantes = set(clases) - set(estado['clases'])
        if faltantes:
            advertencias.append(f'{particion}: clases sin anotaciones: {", ".join(sorted(faltantes))}')
        estado['grupos'] = len(estado['grupos'])
        estado['clases'] = dict(estado['clases'])
    return dict(clases=clases, resumen=resumen, advertencias=advertencias, entradas=entradas)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Valida imágenes/anotaciones y evita fugas entre particiones.')
    parser.add_argument('manifiesto', type=Path)
    args = parser.parse_args()
    try:
        resultado = validar(args.manifiesto)
    except DatasetInvalido as exc:
        parser.exit(2, f'Dataset inválido: {exc}\n')
    print(json.dumps({k:v for k,v in resultado.items() if k != 'entradas'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
