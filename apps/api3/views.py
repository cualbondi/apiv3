from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import exceptions
from rest_framework import pagination
from rest_framework import viewsets, views
from rest_framework.response import Response

from apps.catastro.models import Ciudad
from apps.catastro.models import PuntoBusqueda
from apps.core.models import Linea
from apps.core.models import Recorrido
from . import serializers
from .mixins import LoggingMixin


class CiudadesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.CiudadSerializer
    queryset = Ciudad.objects.all()


class LineasViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializers.LineaSerializer
    queryset = Linea.objects.all()


class CBPagination(pagination.PageNumberPagination):
    page_size = 5

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'page': self.page.number,
            'page_size': self.page.paginator.per_page,
            'page_count': self.page.paginator.num_pages,
            'results': data
        })


class RecorridosViewSet(LoggingMixin, viewsets.GenericViewSet):
    """
        Parametros querystring

         - `l` lista de puntos (lon,lat floats) y radio (int: metros) en orden
            por los cuales se busca que pase una ruta. Ejemplos a continuación:

            - `l=55.3324,-55.4433,200`
            - `l=55.3324,-55.4433,200|55.1112,-55.3334,300`
            - [live example](/api//recorridos/?l=-57.957258224487305,-34.92056351681724,200|-57.94755935668945,-34.92556010123052,200)

         - `t` true/false: buscar con transbordo (true). `false` por defecto.
         - `q` string: para búsqueda por nombre de recorrido (fuzzy search)
         - `c` string: ciudad-slug, requerido cuando se usa `q`
    """

    serializer_class = serializers.RecorridoSerializer
    queryset = Recorrido.objects.all()
    pagination_class = CBPagination

    def list(self, request):
        q = request.query_params.get('q', None)
        l = request.query_params.get('l', None)
        t = request.query_params.get('t', 'false')
        c = request.query_params.get('c', None)

        if (q is None) == (l is None):
            raise exceptions.ValidationError(
                {'detail': '\'q\' or \'l\' parameter expected (but not both)'}
            )

        if t == 'true':
            t = True
        elif t == 'false':
            t = False
        else:
            raise exceptions.ValidationError(
                {'detail': '\'t\' parameter malformed: Expected \'true\' or \'false\''}
            )

        if l is not None:
            try:
                lp = []  # lista de puntos
                for p in l.split('|'):
                    ps = p.split(',')
                    lp.append({'p': GEOSGeometry('POINT({} {})'.format(ps[0], ps[1]), srid=4326), 'r': int(ps[2])})
            except:
                raise exceptions.ValidationError(
                    {'detail': '\'l\' parameter malformed'}
                )
            if len(lp) > 2:
                raise exceptions.ValidationError(
                    {'detail': '\'l\' parameter accepts up to 2 points max.'}
                )

            if len(lp) == 1:
                qs = Recorrido.objects.filter(ruta__distance_lte=(lp[0]['p'], D(m=lp[0]['r'])))
                page = self.paginate_queryset(qs)
                self.update_logger_extras({
                    "point1": "{},{}".format(lp[0]['p'].y, lp[0]['p'].x),
                    # "lat,lon" https://www.elastic.co/guide/en/elasticsearch/reference/1.3/mapping-geo-point-type.html
                    "rad1": lp[0]['r'],
                    "point2": None,
                    "rad2": None,
                    "t": False,
                    "count": self.paginator.page.paginator.count,
                    "page": self.paginator.page.number
                })
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    return self.get_paginated_response(serializer.data)
                else:
                    return Response([])

            if not t:
                # sin transbordo
                routerResults = Recorrido.objects.get_recorridos(lp[0]['p'], lp[1]['p'], lp[0]['r'], lp[1]['r'])
            else:
                # con transbordo
                routerResults = Recorrido.objects.get_recorridos_combinados_sin_paradas(lp[0]['p'], lp[1]['p'],
                                                                                        lp[0]['r'], lp[1]['r'], 500)

            page = self.paginate_queryset(routerResults)
            self.update_logger_extras({
                "point1": "{},{}".format(lp[0]['p'].y, lp[0]['p'].x),
                # "lat,lon" https://www.elastic.co/guide/en/elasticsearch/reference/1.3/mapping-geo-point-type.html
                "rad1": lp[0]['r'],
                "point2": "{},{}".format(lp[1]['p'].y, lp[1]['p'].x),
                "rad2": lp[1]['r'],
                "t": t,
                "count": self.paginator.page.paginator.count,
                "page": self.paginator.page.number
            })
            if page is not None:
                ser = serializers.RouterResultSerializer(page, many=True)
                return self.get_paginated_response(ser.data)
            else:
                return Response([])

        if q is not None:
            if c is None:
                raise exceptions.ValidationError(
                    {'detail': '\'c\' parameter is required when using `q` parameter'}
                )
            page = self.paginate_queryset(list(
                Recorrido.objects.fuzzy_like_trgm_query(q, c)
            ))
            self.update_logger_extras({
                "q": q,
                "c": c,
                "count": self.paginator.page.paginator.count,
                "page": self.paginator.page.number
            })
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            else:
                return Response([])


class GeocoderViewSet(LoggingMixin, viewsets.GenericViewSet):
    """
        Parámetros querystring

         - `q` obligatorio: string a geobuscar
         - `mk` opcional (arcgis): arcgis `magic key` si viene del suggest
         - `c` opcional: slug de la ciudad donde buscar

        Busca el valor del parámetro `q`
        usando varias fuentes según el formato del string de búsqueda

         - **Geocoder** [Google] (ej: [12 1234](/api//geocoder/?q=12%201234&c=la-plata) / [12 n 1234](/api//geocoder/?q=12%20n%201234&c=la-plata) / [centenario 1234](/api//geocoder/?q=centenario%20n%201234&c=la-plata))
         - **Intersección de calles** [OSM] (ej: [12 y 62](/api//geocoder/?q=12%20y%2062&c=la-plata) / perón y alvarez)
         - **POI (Point Of Interest)** [OSM y Cualbondi] (ej: plaza rocha / hospital)
         - **Zona (Barrio / Ciudad)** [Cualbondi] (ej: berisso / colegiales) (devuelve geocentro)

        El geocoder usa varias fuentes y técnicas, entre ellas fuzzy search.
        Por esto, devuelve un valor de "precision" para cada registro.

        Utiliza el parámetro `c` (ciudad) para dar mas contexto al lugar
        donde se está buscando. Esto ayuda a evitar ambigüedad en la búsqueda
        ya que puede haber dos calles que se llamen igual en distintas ciudades
        pero no restringe la búsqueda a esa ciudad (sólo altera la precisión)
    """
    serializer_class = serializers.GeocoderSerializer
    queryset = ''

    def list(self, request):
        q = request.query_params.get('q', None)
        c = request.query_params.get('c', None)
        mk = request.query_params.get('mk', None)
        if not q:
            raise exceptions.ValidationError(
                {'detail': 'expected \'q\' parameter'}
            )
        else:
            try:
                res = PuntoBusqueda.objects.geocode(q, c)
                ser = self.get_serializer(res, many=True)
                return Response(ser.data)
            except ObjectDoesNotExist:
                return Response([])


class GeocoderSuggestViewSet(viewsets.GenericViewSet):
    """
        Parámetros querystring

         - `q` obligatorio: string a geobuscar
         - `c` opcional: slug de la ciudad donde buscar

        Busca el valor del parámetro `q`
        usando Arcgis Suggest
    """
    serializer_class = serializers.GeocoderSuggestSerializer
    queryset = ''

    def list(self, request):
        q = request.query_params.get('q', None)
        c = request.query_params.get('c', None)
        if q is None:
            raise exceptions.ValidationError(
                {'detail': 'expected \'q\' parameter'}
            )
        else:
            try:
                res = PuntoBusqueda.objects.buscar_arcgis_suggest(q, c)
                ser = self.get_serializer(res, many=True)
                return Response(ser.data)
            except ObjectDoesNotExist:
                return Response([])


class ReverseGeocoderView(viewsets.GenericViewSet):

    def list(self, request):
        q = request.query_params.get('q', None)
        c = request.query_params.get('c', None)
        if q is None:
            raise exceptions.ValidationError(
                {'detail': 'expected \'q\' parameter'}
            )
        res = PuntoBusqueda.objects.reverse_geocode(q, c)
        return Response(res)
