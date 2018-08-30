import json
from operator import itemgetter
from urllib.parse import quote
from urllib.request import urlopen
import unicodedata

from django.contrib.gis.geos import GEOSGeometry
from django.db import connection, IntegrityError
from django.db.models import Manager as GeoManager, F
from django.apps import apps
from django.conf import settings

from .geopy_arcgis import ArcGIS, ArcGISSuggest
from geopy.geocoders import Nominatim

nominatim = Nominatim(user_agent='cualbondi', timeout=5)


def remove_multiple_strings(cur_string, replace_list):
    for cur_word in replace_list:
        cur_string = cur_string.replace(cur_word, '')
    return cur_string


class PuntoBusquedaManager:
    """ Este manager se encarga de convertir una query tipo texto
    en una lista de puntos geográficos que pueden ser usados como origen
    o destino de una búsqueda. Los datos tenidos en cuenta son:
    **Interseccion de calles
    **Comercios
    **Pois
    **CustomPois
    **Google Geocoder

    A futuro puede sumarse:
    **Paradas

    """

    def __init__(self, *args, **kwargs):
        arcgis_args = {}
        if settings.ARCGIS_USER:
            arcgis_args['username'] = settings.ARCGIS_USER
            arcgis_args['referer'] = 'cualbondi.com.ar'
        if settings.ARCGIS_PASS:
            arcgis_args['password'] = settings.ARCGIS_PASS
            arcgis_args['referer'] = 'cualbondi.com.ar'
        self.geolocator = ArcGIS(**arcgis_args)
        self.suggestor = ArcGISSuggest(**arcgis_args)
        super().__init__(*args, **kwargs)

    def dictfetchall(self, cursor):
        "Returns all rows from a cursor as a dict"
        desc = cursor.description
        return [
            dict(list(zip([col[0] for col in desc], row)))
            for row in cursor.fetchall()
        ]

    def _objfetchall(self, cursor):
        "Returns all rows from a cursor as an object, but it's not editable (no setters)"
        desc = cursor.description
        l = []

        class Struct:
            def __init__(self, **entries):
                self.__dict__.update(entries)

        for row in cursor.fetchall():
            d = dict(list(zip([col[0] for col in desc], row)))
            l.append(Struct(**d))
        return l

    def buscar_arcgis(self, query, ciudad_actual_slug=None, magickey=None):
        ciudad_model = apps.get_app_config('catastro').get_model("Ciudad")
        ciudad_actual = ciudad_model.objects.get(slug=ciudad_actual_slug)
        xmin, ymin, xmax, ymax = ciudad_actual.poligono.extent
        cx, cy, _, _ = ciudad_actual.centro.extent
        extra_params = {
            # searchExtent=lon1,lat1,lon2,lat2
            'searchExtent': "{},{},{},{}".format(xmin, ymin, xmax, ymax),
            'location': "{},{}".format(cx, cy),
            'city': quote(ciudad_actual.nombre.encode('utf8')),
            'countryCode': 'ARG',
            'sourceCountry': 'ARG',
        }
        if magickey is not None and magickey != 'undefined':
            extra_params['magicKey'] = magickey
        locations = self.geolocator.geocode(
            query,
            exactly_one=False,
            extra_params=extra_params
        )
        if not locations:
            return []

        # comprehension para parsear lo devuelto por el google geocoder
        ret = [
            {
                'nombre': r.address,
                'precision': 1,
                'geom': "POINT({} {})".format(r.longitude, r.latitude),
                'tipo': ""
            }
            for r in locations
        ]
        return ret

    def buscar_arcgis_suggest(self, query, ciudad_actual_slug=None):
        #add = query + ", Argentina"
        #add = quote(add.encode('utf8'))
        # location la-plata
        ciudad_model = apps.get_app_config('catastro').get_model("Ciudad")
        ciudad_actual = ciudad_model.objects.get(slug=ciudad_actual_slug)
        xmin, ymin, xmax, ymax = ciudad_actual.poligono.extent
        cx, cy, _, _ = ciudad_actual.centro.extent
        locations = self.suggestor.geocode(
            query,
            exactly_one=False,
            extra_params={
                # searchExtent=lon1,lat1,lon2,lat2
                'searchExtent': "{},{},{},{}".format(xmin, ymin, xmax, ymax),
                'location': "{},{}".format(cx, cy),
                'city': quote(ciudad_actual.nombre.encode('utf8')),
                'countryCode': 'ARG',
                'sourceCountry': 'ARG'
            }
        )
        if not locations:
            return []

        # comprehension para parsear lo devuelto por el google geocoder
        ret = [
            {
                'nombre': r["text"],
                'magickey': r["magickey"]
            }
            for r in locations
        ]
        return ret

    def reverse_geocode(self, query, ciudad_actual_slug=None):
        response = nominatim.reverse(query, exactly_one=True, language='es')
        if response is None:
            return None
        city = response.raw.get('address').get('city')
        display_name = response.raw.get('display_name')
        short_response = display_name[:display_name.find(city)] + city
        return short_response

    def deaccent(self, text):
        """
        Remove accentuation from the given string. Input text is either a unicode string or utf8 encoded bytestring.
        Return input string with accents removed, as unicode.
        """
        norm = unicodedata.normalize("NFD", text)
        result = ''.join(ch for ch in norm if unicodedata.category(ch) != 'Mn')
        return unicodedata.normalize("NFC", result)

    def normalize_query(self, query):
        query = self.deaccent(query)
        query = query.replace('.', ' ')
        query = query.replace(',', ' ')
        query = ' '.join(query.split())
        query = query.strip()
        query = query.lower()
        return query

    def geocode(self, query, ciudad_actual_slug=None):
        assert query != ''
        google = self.buscar_google(query, ciudad_actual_slug)
        if google is not None:
            return google
        return self.buscar_arcgis(query, ciudad_actual_slug)

    def buscar_google(self, query, ciudad_actual_slug=None):
        google_cache_model = apps.get_app_config('catastro').get_model("GoogleGeocoderCache")
        ciudad_model = apps.get_app_config('catastro').get_model("Ciudad")
        ciudad_actual = ciudad_model.objects.get(slug=ciudad_actual_slug)
        xmin, ymin, xmax, ymax = ciudad_actual.poligono.extent
        cx, cy, _, _ = ciudad_actual.centro.extent
        bbox = "{},{}|{},{}".format(ymin, xmin, ymax, xmax)
        normalized_query = self.normalize_query(query)
        try:
            match = google_cache_model.objects.get(query=normalized_query, ciudad=ciudad_actual_slug)
            match.hit = F('hit') + 1
            match.save()
            return json.loads(match.results)
        except google_cache_model.DoesNotExist:
            results = self.rawGeocoder(query, bbox)
            if len(results) == 0:
                return None

            # avoid possible race condition here where two geocoding calls could resolve concurrently
            try:
                google_cache_model.objects.create(
                    query=normalized_query,
                    results=json.dumps(results),
                    ciudad=ciudad_actual_slug
                )
            except IntegrityError:
                # result already exists on db at this point
                pass
            return results

    def buscar_cualbondi(self, query, ciudad_actual_slug=None):
        # podria reemplazar todo esto por un lucene/solr/elasticsearch
        # que tenga un campo texto y un punto asociado

        # Dados estos ejemplos:
        #  - 12 y 64, casco urbano, la plata, buenos aires, argentina
        #  - plaza italia, casco urbano, la plata, buenos aires, argentina
        # la idea es separar lo que hay entre comas, en una lista de tokens
        # 1. tomat token[0] y fijarse si es
        #   una interseccion (contiene ' y ')
        #   una direccion postal (contiene ' n ')
        #   una punto de interes o zona o ciudad o "raw geocoder"
        # 2. tomar la lista de resultados devueltos, que contienen una "precision"
        #   Para cada uno del resto de los tokens:
        #   elevar un 20% la precision si el token coincide con el slug de la ciudad (o zona) donde el punto cae
        #   caso contrario, disminuir en un 20% la precision de ese punto

        ciudad_model = apps.get_app_config('catastro').get_model("Ciudad")
        zona_model = apps.get_app_config('catastro').get_model("Zona")
        tokens = [_f for _f in map(str.strip, query.split(',')) if _f]
        if query:

            res = self.poi_exact(query)
            if not res:

                query = remove_multiple_strings(query.upper(), ['AV.', 'AVENIDA', 'CALLE', 'DIAGONAL', 'BOULEVARD'])

                tokens = [_f for _f in map(str.strip, query.split(',')) if _f]

                if len(tokens) > 0:
                    calles = tokens[0].upper()[:]
                else:
                    return []

                separators = ['Y', 'ESQ', 'ESQ.', 'ESQUINA', 'ESQUINA.', 'INTERSECCION', 'CON', 'CRUCE']
                for sep in separators:
                    calles = calles.replace(' ' + sep + ' ', '@')
                calles = calles.split('@')

                if len(calles) == 2:
                    res = self.interseccion(calles[0].strip(), calles[1].strip())
                else:

                    direccion = tokens[0].upper()[:]
                    separators = ['N', 'NUM', 'NUM.', 'NRO', 'NUMERO', 'NUMERO.', 'NO', 'NO.']
                    for sep in separators:
                        direccion = direccion.replace(' ' + sep + ' ', '@')
                    direccion = direccion.split('@')

                    if len(direccion) == 2:
                        res = self.direccionPostal(direccion[0].strip(), direccion[1].strip(), ciudad_actual_slug)
                    else:
                        # worst case (ordenar por precision?)
                        res = []
                        for tok in tokens:
                            # PROBLEMA! estos devuelven diccionarios que se acceden asi: punto['item']
                            # PROBLEMA! pero los otros devuelven objetos que se acceden asi punto.attr
                            res += self.poi(tok) + self.zona(tok)

            # ciudad actual, en la que esta el mapa, deberia ser pasada por parametro
            ciudad_actual = ciudad_model.objects.get(slug=ciudad_actual_slug)

            if res:
                res = [r for r in res if ciudad_actual.poligono.intersects(GEOSGeometry(r['geom']))]
            if not res:
                res = []
                for tok in tokens:
                    res += self.poi(tok) + self.zona(tok)
                if res:
                    res = [r for r in res if ciudad_actual.poligono.intersects(GEOSGeometry(r['geom']))]
            if not res:
                res = []
                for tok in tokens:
                    res += self.rawGeocoder(tok)
                if res:
                    res = [r for r in res if ciudad_actual.poligono.intersects(GEOSGeometry(r['geom']))]
            if not res:
                res = []
                for tok in tokens:
                    res += self.rawGeocoder(tok + "," + ciudad_actual.nombre)
                if res:
                    res = [r for r in res if ciudad_actual.poligono.intersects(GEOSGeometry(r['geom']))]

            #
            # aca chequear si los resultados intersectan con el poligono de la ciudad_actual y de la ciudad_entrada o de la zona
            # ciudad entrada estaría en token[1]. Sumar puntos si eso es una ciudad, o si es una zona, a la cual cada punto pertenece.
            areas = []

            # zona o ciudad ingresada (tokens>1)
            for token in tokens[1:]:
                try:
                    areas += [GEOSGeometry(i.poligono) for i in zona_model.objects.fuzzy_like_query(token)]
                except:
                    pass
                try:
                    areas += [GEOSGeometry(i.poligono) for i in ciudad_model.objects.fuzzy_like_query(token)]
                except:
                    pass

            if areas:
                # para cada resultado aplicar la subida o bajada de puntaje segun el area en la que se encuentra
                for r in res:
                    # para cada area en la que este resultado intersecta, sumar o restar
                    for area in areas:
                        if area.intersects(GEOSGeometry(r['geom'])):
                            # sumar un 20% a la precision, sino restar un 20%
                            r['precision'] *= 1.8
                        else:
                            r['precision'] *= 0.4
                    if ciudad_actual.poligono.intersects(GEOSGeometry(r['geom'])):
                        r['precision'] *= 1.8
            else:
                # El punto tiene que estar si o si en la ciudad actual
                res = [r for r in res if ciudad_actual.poligono.intersects(GEOSGeometry(r['geom']))]

            # ordenar
            res.sort(key=itemgetter("precision"), reverse=True)
            # si el mejor tiene diferencia de .5 o mas con el segundo y esta sobre el .5 de precision, listo, gano
            # generar alguna otra regla heuristica similar para filtrar
            return res
        else:
            return []

    def interseccion(self, calle1, calle2):
        params = {'calle1': calle1, 'calle2': calle2}
        query = """
                SELECT DISTINCT
                    SEL1.nom || ' y ' || SEL2.nom || coalesce(', ' || z.name, '') as nombre,
                    ST_AsText(ST_Intersection(SEL1.way, SEL2.way)) as geom,
                    ( SEL2.similarity + SEL1.similarity ) / 2 as precision,
                    'interseccion' as tipo
                FROM
                    (
                        SELECT
                            nom,
                            similarity(nom_normal, %(calle1)s) as similarity,
                            way
                        FROM
                            catastro_calle as c
                        WHERE
                            nom_normal %% %(calle1)s
                    ) AS SEL1
                    join
                    (
                        SELECT
                            nom,
                            similarity(nom_normal, %(calle2)s) as similarity,
                            way
                        FROM
                            catastro_calle as c
                        WHERE
                            nom_normal %% %(calle2)s
                    ) AS SEL2
                    on ( ST_Intersects(SEL1.way, SEL2.way)
                        and ST_GeometryType(ST_Intersection(SEL1.way, SEL2.way)::Geometry)='ST_Point')

                    left outer join
                        catastro_zona as z
                        on ST_Intersects(z.geo, ST_Intersection(SEL1.way, SEL2.way))

                ORDER BY
                    precision DESC
                LIMIT 5
        ;"""
        cursor = connection.cursor()
        query_set = cursor.execute(query, params)
        l = self.dictfetchall(cursor)
        return l

    def poi(self, nombre):
        params = {'nombre': nombre}
        query = """
            SELECT set_limit(0.12);
            SELECT
                nom as nombre,
                similarity(nom_normal, %(nombre)s) as precision,
                ST_AsText(latlng) as geom,
                'poi' as tipo
            FROM
                catastro_poi as p
            WHERE
                nom_normal %% %(nombre)s
            ORDER BY
                precision DESC
            LIMIT 5
        ;"""
        cursor = connection.cursor()
        query_set = cursor.execute(query, params)
        l = self.dictfetchall(cursor)
        return l

    def poi_exact(self, nombre):
        params = {'nombre': nombre}
        query = """
            SELECT
                nom as nombre,
                1 as precision,
                ST_AsText(latlng) as geom,
                'poi' as tipo
            FROM
                catastro_poi as p
            WHERE
                nom_normal ilike %(nombre)s
            LIMIT 5
        ;"""
        cursor = connection.cursor()
        query_set = cursor.execute(query, params)
        l = self.dictfetchall(cursor)
        return l

    def zona(self, nombre):
        params = {'nombre': nombre}
        query = """
            SELECT set_limit(0.12);
            SELECT
                name as nombre,
                similarity(name, %(nombre)s) as precision,
                ST_AsText(ST_Centroid(geo::geometry)) as geom,
                'zona' as tipo
            FROM
                catastro_zona
            WHERE
                name %% %(nombre)s
            ORDER BY
                precision DESC
            LIMIT 5
        ;"""
        cursor = connection.cursor()
        query_set = cursor.execute(query, params)
        l = self.dictfetchall(cursor)
        return l

    def rawGeocoder(self, query, bbox=None):
        # http://stackoverflow.com/questions/9884475/using-google-maps-geocoder-from-python-with-urllib2
        add = query
        add = quote(add.encode('utf8'))
        geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?key={settings.GEOCODING_GOOGLE_KEY}&language=es&region=ar&address={add}"
        if bbox is not None:
            geocode_url = f'{geocode_url}&bounds={bbox}'
        # TODO: Test this change
        req = urlopen(geocode_url)
        res = json.loads(req.read())
        if res['status'] != 'OK':
            return []
        # comprehension para parsear lo devuelto por el google geocoder
        ret = [
            {
                'nombre': i["formatted_address"],
                'precision': len(i["address_components"]) / 6,
                'geom': "POINT(" + str(i["geometry"]["location"]["lng"]) + " " + str(
                    i["geometry"]["location"]["lat"]) + ")",
                'tipo': "rawGeocoder"
            }
            for i in res["results"]
        ]
        return ret

    def direccionPostal(self, calle, numero, ciudad_slug):
        # http://stackoverflow.com/questions/9884475/using-google-maps-geocoder-from-python-with-urllib2
        add = calle + " " + numero + ", " + ciudad_slug + ", Argentina"
        add = quote(add.encode('utf8'))
        geocode_url = "http://maps.googleapis.com/maps/api/geocode/json?language=es&address=%s&sensor=false" % add
        req = urlopen(geocode_url)
        res = json.loads(req.read())
        # comprehension para parsear lo devuelto por el google geocoder
        ret = [
            {
                'nombre': i["formatted_address"],
                'precision': 1,
                'geom': "POINT(" + str(i["geometry"]["location"]["lng"]) + " " + str(
                    i["geometry"]["location"]["lat"]) + ")",
                'tipo': "direccionPostal"
            }
            for i in res["results"]
            if "street_address" in i["types"]
        ]
        return ret


class ZonaManager(GeoManager):
    def fuzzy_like_query(self, q):
        params = {"q": q}
        query = """
            SELECT set_limit(0.12);
            SELECT
                id,
                name as nombre,
                geo as poligono
            FROM
                catastro_zona
            WHERE
                name %% %(q)s
            ORDER BY
                similarity(name, %(q)s) DESC
            LIMIT
                1
            ;
        """
        query_set = self.raw(query, params)
        return list(query_set)


class CiudadManager(GeoManager):
    def fuzzy_like_query(self, q):
        params = {"q": q}
        query = """
            SELECT set_limit(0.12);
            SELECT
                id,
                nombre,
                poligono
            FROM
                catastro_ciudad
            WHERE
                nombre %% %(q)s
            ORDER BY
                similarity(nombre, %(q)s) DESC
            LIMIT
                1
            ;
        """
        query_set = self.raw(query, params)
        return list(query_set)
