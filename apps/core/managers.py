from django.contrib.gis.geos import Point
from django.db import DatabaseError, connection
from django.db.models import Manager as GeoManager


class RecorridoManager(GeoManager):
    """
        Contains all the search functions for Recorridos
    """
    def get_recorridos_combinados(self, punto_a, punto_b, distancia_a, distancia_b, gap):
        distancia_a = int(distancia_a)
        distancia_b = int(distancia_b)
        gap = int(gap)
        if not isinstance(punto_a, Point):
            raise DatabaseError(
                "get_recorridos: PuntoA Expected GEOS Point instance as parameter, %s given" % type(punto_a))
        if not isinstance(punto_b, Point):
            raise DatabaseError(
                "get_recorridos: PuntoB Expected GEOS Point instance as parameter, %s given" % type(punto_b))
        if not isinstance(distancia_a, int):
            raise DatabaseError("get_recorridos: distancia_a Expected integer as parameter, %s given" % type(distancia_a))
        if not isinstance(distancia_b, int):
            raise DatabaseError("get_recorridos: distancia_b Expected integer as parameter, %s given" % type(distancia_b))
        if not isinstance(gap, int):
            raise DatabaseError("get_recorridos: gap Expected integer as parameter, %s given" % type(gap))

        if punto_a.srid != 4326 or punto_b.srid != 4326:
            punto_a = Point(punto_a.x, punto_a.y, srid=4326)
            punto_b = Point(punto_b.x, punto_b.y, srid=4326)

        distancia_a = 0.0000111 * float(distancia_a)
        distancia_b = 0.0000111 * float(distancia_b)
        gap = 0.0000111 * float(gap)

        connection.cursor().execute('SET STATEMENT_TIMEOUT=30000')

        params = {'punto_a': punto_a.ewkt, 'punto_b': punto_b.ewkt,
                  'rad1': distancia_a, 'rad2': distancia_b, 'gap': gap, 'p': 0.1}
        query = """
            SELECT *
            FROM
            (
                SELECT *,
                encode(ST_AsGeobuf(
                    ST_LineSubstring(
                        re1_ruta,
                        ST_LineLocatePoint(re1_ruta, ll11),
                        ST_LineLocatePoint(re1_ruta, ll12)
                        )::Geography
                    ), 'base64') as ruta_corta,
                encode(ST_AsGeobuf(
                    ST_LineSubstring(
                        re2_ruta,
                        ST_LineLocatePoint(re2_ruta, ll21),
                        ST_LineLocatePoint(re2_ruta, ll22)
                        )::Geography
                    ), 'base64') as ruta_corta2,
                ST_Length(
                    ST_LineSubstring(
                        re1_ruta,
                        ST_LineLocatePoint(re1_ruta, ll11),
                        ST_LineLocatePoint(re1_ruta, ll12)
                        )::Geography
                    ) as long_ruta,
                ST_Length(
                    ST_LineSubstring(
                        re2_ruta,
                        ST_LineLocatePoint(re2_ruta, ll21),
                        ST_LineLocatePoint(re2_ruta, ll22)
                        )::Geography
                    ) as long_ruta2,
                ST_DistanceSphere(ll11, re1_ruta) as long_pata,
                ST_DistanceSphere(ll22, re2_ruta) as long_pata2,
                ST_DistanceSphere(ll21, ll12) as long_pata_transbordo
            FROM (
                SELECT
                    re1.id as id,
                    re1.ruta as re1_ruta,
                    re2.ruta as re2_ruta,
                    li1.nombre || ' ' || re1.nombre as nombre,
                    li2.nombre || ' ' || re2.nombre as nombre2,
                    re2.id as id2,
                    coalesce(re1.color_polilinea, li1.color_polilinea, '#000') as color_polilinea,
                    coalesce(re2.color_polilinea, li2.color_polilinea, '#000') as color_polilinea2,
                    coalesce(li1.foto, 'default') as foto,
                    coalesce(li2.foto, 'default') as foto2,
                    re1.inicio as inicio,
                    re2.inicio as inicio2,
                    re1.fin as fin,
                    re2.fin as fin2,
                    re1.paradas_completas as re1_paradas_completas,
                    re2.paradas_completas as re2_paradas_completas,
                    coalesce(p11.latlng, ST_GeomFromText(%(punto_a)s)) as ll11,
                    coalesce(p12.latlng, ST_ClosestPoint(re1.ruta, coalesce(p21.latlng, re2.ruta))) as ll12,
                    coalesce(p21.latlng, ST_ClosestPoint(re2.ruta, coalesce(p12.latlng, re1.ruta))) as ll21,
                    coalesce(p22.latlng, ST_GeomFromText(%(punto_b)s)) as ll22,
                    p11.id as p11ll,
                    p12.id as p12ll,
                    p21.id as p21ll,
                    p22.id as p22ll
                FROM
                    core_recorrido as re1
                    join core_recorrido as re2 on (re1.id <> re2.id)
                    join core_linea li1 on li1.id = re1.linea_id
                    join core_linea li2 on li2.id = re2.linea_id
                    LEFT OUTER JOIN core_horario as h11 on (h11.recorrido_id = re1.id)
                    LEFT OUTER JOIN core_horario as h12 on (h12.recorrido_id = re1.id)
                    LEFT OUTER JOIN core_parada  as p11 on (p11.id = h11.parada_id)
                    LEFT OUTER JOIN core_parada  as p12 on (p12.id = h12.parada_id and p11.id <> p12.id)
                    LEFT OUTER JOIN core_horario as h21 on (h21.recorrido_id = re2.id)
                    LEFT OUTER JOIN core_horario as h22 on (h22.recorrido_id = re2.id)
                    LEFT OUTER JOIN core_parada  as p21 on (p21.id = h21.parada_id)
                    LEFT OUTER JOIN core_parada  as p22 on (p22.id = h22.parada_id and p21.id <> p22.id)
                ) as sq
            WHERE
                (
                    ST_DWithin(re1_ruta, ll11, %(rad1)s)
                    and
                    ST_DWithin(re2_ruta, ll22, %(rad2)s)
                    and
                        ST_DWithin(ll21, ll12, %(gap)s)
                    and
                        ST_LineLocatePoint(re1_ruta, ll11)
                        <
                        ST_LineLocatePoint(re1_ruta, ll12 )
                    and
                        ST_LineLocatePoint(re2_ruta, ll21 )
                        <
                        ST_LineLocatePoint(re2_ruta, ll22)
                    and
                        (not re1_paradas_completas) and (not re2_paradas_completas)
                )

            UNION
            SELECT *,
                encode(ST_AsGeobuf(
                    ST_LineSubstring(
                        re1_ruta,
                        ST_LineLocatePoint(re1_ruta, ll11),
                        ST_LineLocatePoint(re1_ruta, ll12)
                        )::Geography
                    ), 'base64') as ruta_corta,
                encode(ST_AsGeobuf(
                    ST_LineSubstring(
                        re2_ruta,
                        ST_LineLocatePoint(re2_ruta, ll21),
                        ST_LineLocatePoint(re2_ruta, ll22)
                        )::Geography
                    ), 'base64') as ruta_corta2,
                ST_Length(
                    ST_LineSubstring(
                        re1_ruta,
                        ST_LineLocatePoint(re1_ruta, ll11),
                        ST_LineLocatePoint(re1_ruta, ll12)
                        )::Geography
                    ) as long_ruta,
                ST_Length(
                    ST_LineSubstring(
                        re2_ruta,
                        ST_LineLocatePoint(re2_ruta, ll21),
                        ST_LineLocatePoint(re2_ruta, ll22)
                        )::Geography
                    ) as long_ruta2,
                ST_DistanceSphere(ll11, re1_ruta) as long_pata,
                ST_DistanceSphere(ll22, re2_ruta) as long_pata2,
                ST_DistanceSphere(ll21, ll12) as long_pata_transbordo
            FROM (
                SELECT
                    re1.id as id,
                    re1.ruta as re1_ruta,
                    re2.ruta as re2_ruta,
                    li1.nombre || ' ' || re1.nombre as nombre,
                    li2.nombre || ' ' || re2.nombre as nombre2,
                    re2.id as id2,
                    coalesce(re1.color_polilinea, li1.color_polilinea, '#000') as color_polilinea,
                    coalesce(re2.color_polilinea, li2.color_polilinea, '#000') as color_polilinea2,
                    coalesce(li1.foto, 'default') as foto,
                    coalesce(li2.foto, 'default') as foto2,
                    re1.inicio as inicio,
                    re2.inicio as inicio2,
                    re1.fin as fin,
                    re2.fin as fin2,
                    re1.paradas_completas as re1_paradas_completas,
                    re2.paradas_completas as re2_paradas_completas,
                    coalesce(p11.latlng, ST_GeomFromText(%(punto_a)s)) as ll11,
                    coalesce(p12.latlng, ST_ClosestPoint(re1.ruta, coalesce(p21.latlng, re2.ruta))) as ll12,
                    coalesce(p21.latlng, ST_ClosestPoint(re2.ruta, coalesce(p12.latlng, re1.ruta))) as ll21,
                    coalesce(p22.latlng, ST_GeomFromText(%(punto_b)s)) as ll22,
                    p11.id as p11ll,
                    p12.id as p12ll,
                    p21.id as p21ll,
                    p22.id as p22ll
                FROM
                    core_recorrido as re1
                    join core_recorrido as re2 on (re1.id <> re2.id)
                    join core_linea li1 on li1.id = re1.linea_id
                    join core_linea li2 on li2.id = re2.linea_id
                    LEFT OUTER JOIN core_horario as h11 on (h11.recorrido_id = re1.id)
                    LEFT OUTER JOIN core_horario as h12 on (h12.recorrido_id = re1.id)
                    LEFT OUTER JOIN core_parada  as p11 on (p11.id = h11.parada_id)
                    LEFT OUTER JOIN core_parada  as p12 on (p12.id = h12.parada_id and p11.id <> p12.id)
                    LEFT OUTER JOIN core_horario as h21 on (h21.recorrido_id = re2.id)
                    LEFT OUTER JOIN core_horario as h22 on (h22.recorrido_id = re2.id)
                    LEFT OUTER JOIN core_parada  as p21 on (p21.id = h21.parada_id)
                    LEFT OUTER JOIN core_parada  as p22 on (p22.id = h22.parada_id and p21.id <> p22.id)
                ) as sq
            WHERE
                (
                    ST_DWithin(ST_GeomFromText(%(punto_a)s), ll11, %(rad1)s)
                    and
                    ST_DWithin(re2_ruta, ll22, %(rad2)s)
                    and
                        ST_DWithin(ll21, ll12, %(gap)s)
                    and
                        ST_LineLocatePoint(re1_ruta, ll11)
                        <
                        ST_LineLocatePoint(re1_ruta, ll12 )
                    and
                        ST_LineLocatePoint(re2_ruta, ll21 )
                        <
                        ST_LineLocatePoint(re2_ruta, ll22)
                    and
                        re1_paradas_completas and (not re2_paradas_completas)
                    and
                        p11ll is not null and p12ll is not null
                )
            UNION
            SELECT *,
                encode(ST_AsGeobuf(
                    ST_LineSubstring(
                        re1_ruta,
                        ST_LineLocatePoint(re1_ruta, ll11),
                        ST_LineLocatePoint(re1_ruta, ll12)
                        )::Geography
                    ), 'base64') as ruta_corta,
                encode(ST_AsGeobuf(
                    ST_LineSubstring(
                        re2_ruta,
                        ST_LineLocatePoint(re2_ruta, ll21),
                        ST_LineLocatePoint(re2_ruta, ll22)
                        )::Geography
                    ), 'base64') as ruta_corta2,
                ST_Length(
                    ST_LineSubstring(
                        re1_ruta,
                        ST_LineLocatePoint(re1_ruta, ll11),
                        ST_LineLocatePoint(re1_ruta, ll12)
                        )::Geography
                    ) as long_ruta,
                ST_Length(
                    ST_LineSubstring(
                        re2_ruta,
                        ST_LineLocatePoint(re2_ruta, ll21),
                        ST_LineLocatePoint(re2_ruta, ll22)
                        )::Geography
                    ) as long_ruta2,
                ST_DistanceSphere(ll11, re1_ruta) as long_pata,
                ST_DistanceSphere(ll22, re2_ruta) as long_pata2,
                ST_DistanceSphere(ll21, ll12) as long_pata_transbordo
            FROM (
                SELECT
                    re1.id as id,
                    re1.ruta as re1_ruta,
                    re2.ruta as re2_ruta,
                    li1.nombre || ' ' || re1.nombre as nombre,
                    li2.nombre || ' ' || re2.nombre as nombre2,
                    re2.id as id2,
                    coalesce(re1.color_polilinea, li1.color_polilinea, '#000') as color_polilinea,
                    coalesce(re2.color_polilinea, li2.color_polilinea, '#000') as color_polilinea2,
                    coalesce(li1.foto, 'default') as foto,
                    coalesce(li2.foto, 'default') as foto2,
                    re1.inicio as inicio,
                    re2.inicio as inicio2,
                    re1.fin as fin,
                    re2.fin as fin2,
                    re1.paradas_completas as re1_paradas_completas,
                    re2.paradas_completas as re2_paradas_completas,
                    coalesce(p11.latlng, ST_GeomFromText(%(punto_a)s)) as ll11,
                    coalesce(p12.latlng, ST_ClosestPoint(re1.ruta, coalesce(p21.latlng, re2.ruta))) as ll12,
                    coalesce(p21.latlng, ST_ClosestPoint(re2.ruta, coalesce(p12.latlng, re1.ruta))) as ll21,
                    coalesce(p22.latlng, ST_GeomFromText(%(punto_b)s)) as ll22,
                    p11.id as p11ll,
                    p12.id as p12ll,
                    p21.id as p21ll,
                    p22.id as p22ll
                FROM
                    core_recorrido as re1
                    join core_recorrido as re2 on (re1.id <> re2.id)
                    join core_linea li1 on li1.id = re1.linea_id
                    join core_linea li2 on li2.id = re2.linea_id
                    LEFT OUTER JOIN core_horario as h11 on (h11.recorrido_id = re1.id)
                    LEFT OUTER JOIN core_horario as h12 on (h12.recorrido_id = re1.id)
                    LEFT OUTER JOIN core_parada  as p11 on (p11.id = h11.parada_id)
                    LEFT OUTER JOIN core_parada  as p12 on (p12.id = h12.parada_id and p11.id <> p12.id)
                    LEFT OUTER JOIN core_horario as h21 on (h21.recorrido_id = re2.id)
                    LEFT OUTER JOIN core_horario as h22 on (h22.recorrido_id = re2.id)
                    LEFT OUTER JOIN core_parada  as p21 on (p21.id = h21.parada_id)
                    LEFT OUTER JOIN core_parada  as p22 on (p22.id = h22.parada_id and p21.id <> p22.id)
                ) as sq
            WHERE
                (
                    ST_DWithin(re1_ruta, ll11, %(rad1)s)
                    and
                    ST_DWithin(ST_GeomFromText(%(punto_b)s), ll22, %(rad2)s)
                    and
                        ST_DWithin(ll21, ll12, %(gap)s)
                    and
                        ST_LineLocatePoint(re1_ruta, ll11)
                        <
                        ST_LineLocatePoint(re1_ruta, ll12 )
                    and
                        ST_LineLocatePoint(re2_ruta, ll21 )
                        <
                        ST_LineLocatePoint(re2_ruta, ll22)
                    and
                        (not re1_paradas_completas) and re2_paradas_completas
                    and
                        p21ll is not null and p22ll is not null
                )
            UNION
            SELECT *,
                encode(ST_AsGeobuf(
                    ST_LineSubstring(
                        re1_ruta,
                        ST_LineLocatePoint(re1_ruta, ll11),
                        ST_LineLocatePoint(re1_ruta, ll12)
                        )::Geography
                    ), 'base64') as ruta_corta,
                encode(ST_AsGeobuf(
                    ST_LineSubstring(
                        re2_ruta,
                        ST_LineLocatePoint(re2_ruta, ll21),
                        ST_LineLocatePoint(re2_ruta, ll22)
                        )::Geography
                    ), 'base64') as ruta_corta2,
                ST_Length(
                    ST_LineSubstring(
                        re1_ruta,
                        ST_LineLocatePoint(re1_ruta, ll11),
                        ST_LineLocatePoint(re1_ruta, ll12)
                        )::Geography
                    ) as long_ruta,
                ST_Length(
                    ST_LineSubstring(
                        re2_ruta,
                        ST_LineLocatePoint(re2_ruta, ll21),
                        ST_LineLocatePoint(re2_ruta, ll22)
                        )::Geography
                    ) as long_ruta2,
                ST_DistanceSphere(ll11, re1_ruta) as long_pata,
                ST_DistanceSphere(ll22, re2_ruta) as long_pata2,
                ST_DistanceSphere(ll21, ll12) as long_pata_transbordo
            FROM (
                SELECT
                    re1.id as id,
                    re1.ruta as re1_ruta,
                    re2.ruta as re2_ruta,
                    li1.nombre || ' ' || re1.nombre as nombre,
                    li2.nombre || ' ' || re2.nombre as nombre2,
                    re2.id as id2,
                    coalesce(re1.color_polilinea, li1.color_polilinea, '#000') as color_polilinea,
                    coalesce(re2.color_polilinea, li2.color_polilinea, '#000') as color_polilinea2,
                    coalesce(li1.foto, 'default') as foto,
                    coalesce(li2.foto, 'default') as foto2,
                    re1.inicio as inicio,
                    re2.inicio as inicio2,
                    re1.fin as fin,
                    re2.fin as fin2,
                    re1.paradas_completas as re1_paradas_completas,
                    re2.paradas_completas as re2_paradas_completas,
                    coalesce(p11.latlng, ST_GeomFromText(%(punto_a)s)) as ll11,
                    coalesce(p12.latlng, ST_ClosestPoint(re1.ruta, coalesce(p21.latlng, re2.ruta))) as ll12,
                    coalesce(p21.latlng, ST_ClosestPoint(re2.ruta, coalesce(p12.latlng, re1.ruta))) as ll21,
                    coalesce(p22.latlng, ST_GeomFromText(%(punto_b)s)) as ll22,
                    p11.id as p11ll,
                    p12.id as p12ll,
                    p21.id as p21ll,
                    p22.id as p22ll
                FROM
                    core_recorrido as re1
                    join core_recorrido as re2 on (re1.id <> re2.id)
                    join core_linea li1 on li1.id = re1.linea_id
                    join core_linea li2 on li2.id = re2.linea_id
                    LEFT OUTER JOIN core_horario as h11 on (h11.recorrido_id = re1.id)
                    LEFT OUTER JOIN core_horario as h12 on (h12.recorrido_id = re1.id)
                    LEFT OUTER JOIN core_parada  as p11 on (p11.id = h11.parada_id)
                    LEFT OUTER JOIN core_parada  as p12 on (p12.id = h12.parada_id and p11.id <> p12.id)
                    LEFT OUTER JOIN core_horario as h21 on (h21.recorrido_id = re2.id)
                    LEFT OUTER JOIN core_horario as h22 on (h22.recorrido_id = re2.id)
                    LEFT OUTER JOIN core_parada  as p21 on (p21.id = h21.parada_id)
                    LEFT OUTER JOIN core_parada  as p22 on (p22.id = h22.parada_id and p21.id <> p22.id)
                ) as sq
            WHERE
                (
                    ST_DWithin(ST_GeomFromText(%(punto_a)s), ll11, %(rad2)s)
                    and
                    ST_DWithin(ST_GeomFromText(%(punto_b)s), ll22, %(rad2)s)
                    and
                        ST_DWithin(ll21, ll12, %(gap)s)
                    and
                        ST_LineLocatePoint(re1_ruta, ll11)
                        <
                        ST_LineLocatePoint(re1_ruta, ll12 )
                    and
                        ST_LineLocatePoint(re2_ruta, ll21 )
                        <
                        ST_LineLocatePoint(re2_ruta, ll22)
                    and
                        re1_paradas_completas and re2_paradas_completas
                    and
                        p21ll is not null and p22ll is not null
                    and
                        p21ll is not null and p22ll is not null
                )
            ) as sq2
            ORDER BY (cast(long_pata+long_pata2+long_pata_transbordo as integer)*100 + ( cast(long_ruta as integer) + cast(long_ruta2 as integer) ) ) ASC
        ;"""
        query_set = self.raw(query, params)
        return list(query_set)

    def get_recorridos(self, punto_a, punto_b, distancia_a, distancia_b):
        distancia_a = int(distancia_a)
        distancia_b = int(distancia_b)
        if not isinstance(punto_a, Point):
            raise DatabaseError(
                "get_recorridos: PuntoA Expected GEOS Point instance as parameter, %s given" % type(punto_a))
        if not isinstance(punto_b, Point):
            raise DatabaseError(
                "get_recorridos: PuntoB Expected GEOS Point instance as parameter, %s given" % type(punto_b))
        if not isinstance(distancia_a, int):
            raise DatabaseError("get_recorridos: distancia_a Expected integer as parameter, %s given" % type(distancia_a))
        if not isinstance(distancia_b, int):
            raise DatabaseError("get_recorridos: distancia_b Expected integer as parameter, %s given" % type(distancia_b))
        if punto_a.srid != 4326 or punto_b.srid != 4326:
            punto_a = Point(punto_a.x, punto_a.y, srid=4326)
            punto_b = Point(punto_b.x, punto_b.y, srid=4326)

        with connection.cursor() as c:
            c.execute(
                "(SELECT 1, ST_Buffer(%(punto_a)s::geography, %(radA)s)::geometry UNION SELECT 2, ST_Buffer(%(punto_b)s::geography, %(radB)s)::geometry) order by 1;",
                {'punto_a': punto_a.ewkt, 'radA': distancia_a, 'punto_b': punto_b.ewkt, 'radB': distancia_b}
            )
            bufferA = c.fetchone()[1]
            bufferB = c.fetchone()[1]

        params = {'bufferA': bufferA, 'bufferB': bufferB, 'punto_a': punto_a.ewkt, 'punto_b': punto_b.ewkt}
        query = """
SELECT
  re.id,
  li.nombre || ' ' || re.nombre as nombre,
  linea_id,
  re.slug as slug,
  li.slug as lineaslug,
  inicio,
  fin,
  encode(ST_AsGeobuf(re, 'ruta'), 'base64') as ruta_corta,
  round(long_ruta::numeric, 2) as long_ruta,
  round(long_pata::numeric, 2) as long_pata,
  coalesce(re.color_polilinea, li.color_polilinea, '#000') as color_polilinea,
  coalesce(li.foto, 'default') as foto,
  p1,
  p2
FROM
  core_linea as li join
  (
    (
    SELECT
      id,
      nombre,
      slug,
      inicio,
      fin,
      linea_id,
      color_polilinea,

      ruta,

      min(ST_Distance(segAgeom::geography, %(punto_a)s::geography) + ST_Distance(segBgeom::geography, %(punto_b)s::geography)) as long_pata,
      null::integer as p1,
      null::integer as p2,

      ST_Union(segAgeom) as segsA,
      ST_Union(segBgeom) as segsB,
      min(diff)*ST_Length(ruta::geography) as long_ruta
    FROM
      (
        SELECT
          id,
          nombre,
          slug,
          inicio,
          fin,
          linea_id,
          color_polilinea,
          ruta,
          ST_LineLocatePoint(ruta, ST_ClosestPoint(segB.geom, %(punto_b)s)) - ST_LineLocatePoint(ruta, ST_ClosestPoint(segA.geom, %(punto_a)s)) as diff,
          segA.geom as segAgeom,
          segB.geom as segBgeom
        FROM
          core_recorrido,
          ST_Dump(ST_Intersection( %(bufferA)s, ruta )) as segA,
          ST_Dump(ST_Intersection( %(bufferB)s, ruta )) as segB
        WHERE
          ST_Intersects( %(bufferA)s, ruta) and
          ST_Intersects( %(bufferB)s, ruta) and
          not paradas_completas
      ) as sel
    WHERE
      sel.diff > 0
    GROUP BY
      id,
      nombre,
      slug,
      inicio,
      fin,
      linea_id,
      color_polilinea,
      ruta
    )
    UNION
    (
    SELECT
      id,
      nombre,
      slug,
      inicio,
      fin,
      linea_id,
      color_polilinea,
      ruta,
      long_pata,
      p1id as p1,
      p2id as p2,
      NULL as segsA,
      NULL as segsB,
      diff*ST_Length(ruta::geography) as long_ruta
    FROM
    (
        SELECT
          r.id,
          r.nombre,
          r.slug,
          r.inicio,
          r.fin,
          r.linea_id,
          r.color_polilinea,
          r.ruta,
          ST_Distance(p1.latlng, %(punto_a)s) + ST_Distance(p2.latlng, %(punto_b)s) as long_pata,
          p1.id as p1id,
          p2.id as p2id,
          p1.latlng as p1ll,
          p2.latlng as p2ll,
          min(ST_Distance(p1.latlng,%(punto_a)s)) OVER (PARTITION BY r.id) as min_d1,
          min(ST_Distance(p2.latlng,%(punto_b)s)) OVER (PARTITION BY r.id) as min_d2,
          ST_Distance(p1.latlng,%(punto_a)s) as d1,
          ST_Distance(p2.latlng,%(punto_b)s) as d2,
          ST_LineLocatePoint(r.ruta, p2.latlng) - ST_LineLocatePoint(r.ruta, p1.latlng) as diff
        FROM
          core_recorrido    as r
          JOIN core_horario as h1 on (h1.recorrido_id = r.id)
          JOIN core_horario as h2 on (h2.recorrido_id = r.id)
          JOIN core_parada  as p1 on (p1.id = h1.parada_id)
          JOIN core_parada  as p2 on (p2.id = h2.parada_id and p1.id <> p2.id)
        WHERE
          ST_Intersects( %(bufferA)s, p1.latlng) and
          ST_Intersects( %(bufferB)s, p2.latlng) and
          ST_LineLocatePoint(r.ruta, p1.latlng) <
          ST_LineLocatePoint(r.ruta, p2.latlng) and
          r.paradas_completas
      ) as rec
    WHERE
      min_d1 = d1 and min_d2 = d2
    )
  ) as re on li.id = re.linea_id
  GROUP BY
      re.id,
      li.nombre || ' ' || re.nombre,
      linea_id,
      re.slug,
      li.slug,
      inicio,
      fin,
      long_ruta,
      long_pata,
      coalesce(re.color_polilinea, li.color_polilinea, '#000'),
      coalesce(li.foto, 'default'),
      p1,
      p2
  ORDER BY
    long_pata*10 + long_ruta asc

            ;"""
        query_set = self.raw(query, params)
        return list(query_set)

    def similar_hausdorff(self, rec):
        params = {"r2ruta": rec.ruta.ewkb}
        query = """
            SELECT
                set_limit(0.01);
            SELECT
                r.id,
                r.nombre as nombre,
                r.inicio as inicio,
                r.fin as fin,
                r.slug as slug,
                l.slug as linea_slug,
                l.nombre as linea_nombre,
                cc.slug as ciudad_slug
            FROM
                core_recorrido as r
                join core_linea as l on (r.linea_id = l.id)
                join catastro_ciudad_lineas ccl on (l.id = ccl.linea_id)
                join catastro_ciudad cc on (ccl.ciudad_id = cc.id)
            WHERE
                ST_contains(ST_Buffer(%(r2ruta)s::geometry, 0.03), r.ruta)
                and
                ST_HausdorffDistance(r.ruta, %(r2ruta)s) < 0.03
            ;
        """
        query_set = self.raw(query, params)
        return query_set

    def fuzzy_trgm_query(self, q):
        params = {"q": q}
        query = """
            SELECT
                set_limit(0.01);
            SELECT
                r.id,
                l.nombre || ' ' || r.nombre as nombre,
                similarity(l.nombre || ' ' || r.nombre, %(q)s) as similarity,
                ST_Astext(r.ruta) as ruta_corta
            FROM
                core_recorrido as r
                join core_linea as l on (r.linea_id = l.id)
            WHERE
                (l.nombre || ' ' || r.nombre) %% %(q)s
            ORDER BY
                similarity DESC
            LIMIT
                10
            ;
        """
        query_set = self.raw(query, params)
        return query_set

    def fuzzy_fts_query(self, q):
        params = {"q": q}
        query = """
            SELECT
                r.id,
                l.nombre || ' ' || r.nombre as nombre,
                ts_rank_cd(to_tsvector('spanish', l.nombre || ' ' || r.nombre), query, 32) as similarity,
                ST_Astext(r.ruta) as ruta_corta
            FROM
                core_recorrido as r
                join core_linea as l on (r.linea_id = l.id)
                cross join plainto_tsquery('spanish', %(q)s) query
            WHERE
                query @@ to_tsvector('spanish', l.nombre || ' ' || r.nombre)
            ORDER BY
                similarity DESC
            LIMIT
                10
            ;
        """
        query_set = self.raw(query, params)
        return query_set

    def fuzzy_like_query(self, q, ciudad):
        params = {"q": q, "ci": ciudad}
        query = """
            SELECT
                r.id,
                l.nombre || ' ' || r.nombre as nombre,
                ST_Astext(r.ruta) as ruta_corta,
                l.foto as foto,
                ST_Length(r.ruta::Geography) as long_ruta
            FROM
                core_recorrido as r
                join core_linea as l on (r.linea_id = l.id)
                join catastro_ciudad_lineas as cl on (cl.linea_id = l.id )
                join catastro_ciudad as c on (c.id = cl.ciudad_id)
            WHERE
                (l.nombre || ' ' || r.nombre) ILIKE ('%%' || %(q)s || '%%')
                AND c.slug = %(ci)s
            LIMIT
                10
            ;
        """
        query_set = self.raw(query, params)
        return query_set

    def fuzzy_like_trgm_query(self, q, ciudad):
        params = {"q": q, "ci": ciudad}
        query = """
            SELECT
                r.id,
                l.nombre || ' ' || r.nombre as nombre,
                ST_Astext(r.ruta) as ruta_corta,
                l.foto as foto,
                ST_Length(r.ruta::Geography) as long_ruta,
                similarity(l.nombre || ' ' || r.nombre, %(q)s) as similarity
            FROM
                core_recorrido as r
                join core_linea as l on (r.linea_id = l.id)
                join catastro_ciudad_lineas as cl on (cl.linea_id = l.id )
                join catastro_ciudad as c on (c.id = cl.ciudad_id)
            WHERE
                (l.nombre || ' ' || r.nombre) ILIKE ('%%' || %(q)s || '%%')
                AND c.slug = %(ci)s
            ORDER BY
                similarity DESC,
                (l.nombre || ' ' || r.nombre) ASC
            ;
        """
        query_set = self.raw(query, params)
        return query_set

    def get_recorridos_combinados_con_paradas(self, punto_a, punto_b, distancia_a, distancia_b, gap):
        distancia_a = int(distancia_a)
        distancia_b = int(distancia_b)
        gap = int(gap)
        if not isinstance(punto_a, Point):
            raise DatabaseError(
                "get_recorridos: PuntoA Expected GEOS Point instance as parameter, %s given" % type(punto_a))
        if not isinstance(punto_b, Point):
            raise DatabaseError(
                "get_recorridos: PuntoB Expected GEOS Point instance as parameter, %s given" % type(punto_b))
        if not isinstance(distancia_a, int):
            raise DatabaseError("get_recorridos: distancia_a Expected integer as parameter, %s given" % type(distancia_a))
        if not isinstance(distancia_b, int):
            raise DatabaseError("get_recorridos: distancia_b Expected integer as parameter, %s given" % type(distancia_b))
        if not isinstance(gap, int):
            raise DatabaseError("get_recorridos: gap Expected integer as parameter, %s given" % type(gap))
        if punto_a.srid != 4326 or punto_b.srid != 4326:
            punto_a = Point(punto_a.x, punto_a.y, srid=4326)
            punto_b = Point(punto_b.x, punto_b.y, srid=4326)
        distancia_a = 0.0000111 * float(distancia_a)
        distancia_b = 0.0000111 * float(distancia_b)
        gap = 0.0000111 * float(gap)

        connection.cursor().execute('SET STATEMENT_TIMEOUT=30000')

        params = {'punto_a': punto_a.ewkt, 'punto_b': punto_b.ewkt, 'rad1': distancia_a, 'rad2': distancia_b, 'gap': gap}
        query = """
            SELECT
                id,
                nombre,
                nombre2,
                id2,
                color_polilinea,
                color_polilinea2,
                foto,
                foto2,
                inicio,
                inicio2,
                fin,
                fin2,
                encode(ST_AsGeobuf(ruta_corta), 'base64') as ruta_corta,
                encode(ST_AsGeobuf(ruta_corta2), 'base64') as ruta_corta2,
                long_ruta,
                long_ruta2,
                long_pata,
                long_pata2,
                long_pata_transbordo,
                (
                    SELECT
                        p.id
                    FROM
                        core_horario     as h
                        JOIN core_parada as p on (p.id = h.parada_id)
                    WHERE
                        ST_DistanceSphere(setsrid(p.latlng,4326), setsrid(ST_PointN(subquery.ruta_corta::Geometry, 1),4326)) < 100
                        AND h.recorrido_id = subquery.id
                    ORDER BY
                        ST_DistanceSphere(setsrid(p.latlng,4326), setsrid(ST_PointN(subquery.ruta_corta::Geometry, 1),4326)) ASC
                    LIMIT 1
                    ) as p11ll,
                (
                    SELECT
                        p.id
                    FROM
                        core_horario     as h
                        JOIN core_parada as p on (p.id = h.parada_id)
                    WHERE
                        ST_DistanceSphere(setsrid(p.latlng,4326), setsrid(ST_PointN(subquery.ruta_corta::Geometry, ST_NPoints(subquery.ruta_corta::Geometry)),4326)) < 100
                        AND h.recorrido_id = subquery.id
                    ORDER BY
                        ST_DistanceSphere(setsrid(p.latlng,4326), setsrid(ST_PointN(subquery.ruta_corta::Geometry, ST_NPoints(subquery.ruta_corta::Geometry)),4326)) ASC
                    LIMIT 1
                    ) as p12ll,
                (
                    SELECT
                        p.id
                    FROM
                        core_horario     as h
                        JOIN core_parada as p on (p.id = h.parada_id)
                    WHERE
                        ST_DistanceSphere(setsrid(p.latlng,4326), setsrid(ST_PointN(subquery.ruta_corta2::Geometry, 1),4326)) < 100
                        AND h.recorrido_id = subquery.id2
                    ORDER BY
                        ST_DistanceSphere(setsrid(p.latlng,4326), setsrid(ST_PointN(subquery.ruta_corta2::Geometry, 1),4326)) ASC
                    LIMIT 1
                    ) as p21ll,
                (
                    SELECT
                        p.id
                    FROM
                        core_horario     as h
                        JOIN core_parada as p on (p.id = h.parada_id)
                    WHERE
                        ST_DistanceSphere(setsrid(p.latlng,4326), setsrid(ST_PointN(subquery.ruta_corta2::Geometry, ST_NPoints(subquery.ruta_corta2::Geometry)),4326)) < 100
                        AND h.recorrido_id = subquery.id2
                    ORDER BY
                        ST_DistanceSphere(setsrid(p.latlng,4326), setsrid(ST_PointN(subquery.ruta_corta2::Geometry, ST_NPoints(subquery.ruta_corta2::Geometry)),4326)) ASC
                    LIMIT 1
                    ) as p22ll
            FROM (
                SELECT
                    re1.id as id,
                    li1.nombre || ' ' || re1.nombre as nombre,
                    li2.nombre || ' ' || re2.nombre as nombre2,
                    re2.id as id2,
                    coalesce(re1.color_polilinea, li1.color_polilinea, '#000') as color_polilinea,
                    coalesce(re2.color_polilinea, li2.color_polilinea, '#000') as color_polilinea2,
                    coalesce(li1.foto, 'default') as foto,
                    coalesce(li2.foto, 'default') as foto2,
                    re1.inicio as inicio,
                    re2.inicio as inicio2,
                    re1.fin as fin,
                    re2.fin as fin2,
                    ST_AsText(
                        ST_LineSubstring(
                            re1.ruta,
                            ST_LineLocatePoint(re1.ruta, %(punto_a)s),
                            ST_LineLocatePoint(re1.ruta, ST_ClosestPoint(re1.ruta, re2.ruta))
                            )::Geography
                        ) as ruta_corta,
                    ST_AsText(
                        ST_LineSubstring(
                            re2.ruta,
                            ST_LineLocatePoint(re2.ruta, ST_ClosestPoint(re1.ruta, re2.ruta)),
                            ST_LineLocatePoint(re2.ruta, %(punto_b)s)
                            )::Geography
                        ) as ruta_corta2,
                    ST_Length(
                        ST_LineSubstring(
                            re1.ruta,
                            ST_LineLocatePoint(re1.ruta, %(punto_a)s),
                            ST_LineLocatePoint(re1.ruta, ST_ClosestPoint(re1.ruta, re2.ruta))
                            )::Geography
                        ) as long_ruta,
                    ST_Length(
                        ST_LineSubstring(
                            re2.ruta,
                            ST_LineLocatePoint(re2.ruta, ST_ClosestPoint(re1.ruta, re2.ruta)),
                            ST_LineLocatePoint(re2.ruta, %(punto_b)s)
                            )::Geography
                        ) as long_ruta2,
                    ST_DistanceSphere(ST_GeomFromText(%(punto_a)s), re1.ruta) as long_pata,
                    ST_DistanceSphere(ST_GeomFromText(%(punto_b)s), re2.ruta) as long_pata2,
                    ST_DistanceSphere(re1.ruta, re2.ruta) as long_pata_transbordo

                FROM
                    core_recorrido as re1
                    join core_recorrido as re2 on (re1.id <> re2.id)
                    join core_linea li1 on li1.id = re1.linea_id
                    join core_linea li2 on li2.id = re2.linea_id
                WHERE
                    ST_DWithin(ST_GeomFromText(%(punto_a)s), re1.ruta, %(rad1)s)
                    and
                    ST_DWithin(ST_GeomFromText(%(punto_b)s), re2.ruta, %(rad2)s)
                    and
                        ST_DWithin(re1.ruta, re2.ruta, %(gap)s)
                    and
                        ST_LineLocatePoint(re1.ruta, %(punto_a)s)
                        <
                        ST_LineLocatePoint(re1.ruta, ST_ClosestPoint(re1.ruta, re2.ruta) )
                    and
                        ST_LineLocatePoint(re2.ruta, ST_ClosestPoint(re1.ruta, re2.ruta) )
                        <
                        ST_LineLocatePoint(re2.ruta, %(punto_b)s)
                ) as subquery
            ORDER BY (cast(long_pata+long_pata2+long_pata_transbordo as integer)*100 + ( cast(long_ruta as integer) + cast(long_ruta2 as integer) ) ) ASC
        ;"""
        query_set = self.raw(query, params)
        try:
            return list(query_set)
        except DatabaseError:
            return []

    def get_recorridos_sin_paradas(self, punto_a, punto_b, distancia_a, distancia_b):
        distancia_a = int(distancia_a)
        distancia_b = int(distancia_b)
        if not isinstance(punto_a, Point):
            raise DatabaseError(
                "get_recorridos: PuntoA Expected GEOS Point instance as parameter, %s given" % type(punto_a))
        if not isinstance(punto_b, Point):
            raise DatabaseError(
                "get_recorridos: PuntoB Expected GEOS Point instance as parameter, %s given" % type(punto_b))
        if not isinstance(distancia_a, int):
            raise DatabaseError("get_recorridos: distancia_a Expected integer as parameter, %s given" % type(distancia_a))
        if not isinstance(distancia_b, int):
            raise DatabaseError("get_recorridos: distancia_b Expected integer as parameter, %s given" % type(distancia_b))
        if punto_a.srid != 4326 or punto_b.srid != 4326:
            punto_a = Point(punto_a.x, punto_a.y, srid=4326)
            punto_b = Point(punto_b.x, punto_b.y, srid=4326)
        distancia_a = 0.0000111 * float(distancia_a)
        distancia_b = 0.0000111 * float(distancia_b)

        params = {'punto_a': punto_a.ewkt, 'punto_b': punto_b.ewkt, 'rad1': distancia_a, 'rad2': distancia_b}
        query = """
                SELECT
                    re.id,
                    li.nombre || ' ' || re.nombre as nombre,
                    ruta_corta,
                    round(long_ruta::numeric, 2) as long_ruta,
                    round(long_pata::numeric, 2) as long_pata,
                    coalesce(re.color_polilinea, li.color_polilinea, '#000') as color_polilinea,
                    coalesce(li.foto, 'default') as foto
                FROM
                    core_linea as li join
                    (
                        SELECT
                            id,
                            nombre,
                            ST_AsText(min_path(ruta_corta)) as ruta_corta,
                            min(long_ruta) as long_ruta,
                            min(long_pata) as long_pata,
                            linea_id,
                            color_polilinea
                        FROM
                        (
                            (
                                SELECT
                                    *,
                                    ST_Length(ruta_corta::Geography) as long_ruta,
                                    ST_DistanceSphere(ST_GeomFromText(%(punto_a)s),ruta_corta) +
                                    ST_DistanceSphere(ST_GeomFromText(%(punto_b)s),ruta_corta) as long_pata
                                FROM
                                (
                                    SELECT
                                        *,
                                        ST_LineSubstring(
                                            ST_LineSubstring(ruta, 0, 0.5),
                                            ST_LineLocatePoint(ST_LineSubstring(ruta, 0, 0.5),       %(punto_a)s),
                                            ST_LineLocatePoint(ST_LineSubstring(ruta, 0, 0.5),       %(punto_b)s)
                                        ) as ruta_corta
                                    FROM
                                        core_recorrido
                                    WHERE
                                        ST_DWithin(ST_GeomFromText(%(punto_a)s), ST_LineSubstring(ruta, 0, 0.5), %(rad1)s) and
                                        ST_DWithin(ST_GeomFromText(%(punto_b)s), ST_LineSubstring(ruta, 0, 0.5), %(rad2)s) and
                                        ST_LineLocatePoint(ST_LineSubstring(ruta, 0, 0.5), %(punto_a)s) <
                                            ST_LineLocatePoint(ST_LineSubstring(ruta, 0, 0.5), %(punto_b)s)
                                ) as primera_inner
                            )
                            UNION
                            (
                                SELECT
                                    *,
                                    ST_Length(ruta_corta::Geography) as long_ruta,
                                    ST_DistanceSphere(ST_GeomFromText(%(punto_a)s),ruta_corta) + ST_DistanceSphere(ST_GeomFromText(%(punto_b)s),ruta_corta) as long_pata
                                FROM
                                (
                                    SELECT
                                        *,
                                        ST_LineSubstring(
                                            ST_LineSubstring(ruta, 0.5, 1),
                                            ST_LineLocatePoint(ST_LineSubstring(ruta, 0.5, 1),       %(punto_a)s),
                                            ST_LineLocatePoint(ST_LineSubstring(ruta, 0.5, 1),       %(punto_b)s)
                                        ) as ruta_corta
                                    FROM
                                        core_recorrido
                                    WHERE
                                        ST_DWithin(ST_GeomFromText(%(punto_a)s), ST_LineSubstring(ruta, 0.5, 1), %(rad1)s) and
                                        ST_DWithin(ST_GeomFromText(%(punto_b)s), ST_LineSubstring(ruta, 0.5, 1), %(rad2)s) and
                                        ST_LineLocatePoint(ST_LineSubstring(ruta, 0.5, 1), %(punto_a)s) <
                                        ST_LineLocatePoint(ST_LineSubstring(ruta, 0.5, 1), %(punto_b)s)
                                ) as segunda_inner
                            )
                            UNION
                            (
                                SELECT
                                    *,
                                    ST_Length(ruta_corta::Geography) as long_ruta,
                                    ST_DistanceSphere(ST_GeomFromText(%(punto_a)s),ruta_corta) + ST_DistanceSphere(ST_GeomFromText(%(punto_b)s),ruta_corta) as long_pata
                                FROM
                                (
                                    SELECT
                                        *,
                                        ST_LineSubstring(
                                            ruta,
                                            ST_LineLocatePoint(ruta, %(punto_a)s),
                                            ST_LineLocatePoint(ruta, %(punto_b)s)
                                        ) as ruta_corta
                                    FROM
                                        core_recorrido
                                    WHERE
                                        ST_DWithin(ST_GeomFromText(%(punto_a)s), ruta, %(rad1)s) and
                                        ST_DWithin(ST_GeomFromText(%(punto_b)s), ruta, %(rad2)s) and
                                        ST_LineLocatePoint(ruta, %(punto_a)s) <
                                        ST_LineLocatePoint(ruta, %(punto_b)s)
                                ) as completa_inner
                            )
                        ) as interior
                        GROUP BY
                            id,
                            linea_id,
                            nombre,
                            color_polilinea
                    ) as re
                    on li.id = re.linea_id
                    ORDER BY
                        long_pata*10 + long_ruta asc
            ;"""

        query_set = self.raw(query, params)
        return list(query_set)

    def get_recorridos_combinados_sin_paradas(self, punto_a, punto_b, distancia_a, distancia_b, gap):
        distancia_a = int(distancia_a)
        distancia_b = int(distancia_b)
        gap = int(gap)
        if not isinstance(punto_a, Point):
            raise DatabaseError(
                "get_recorridos: PuntoA Expected GEOS Point instance as parameter, %s given" % type(punto_a))
        if not isinstance(punto_b, Point):
            raise DatabaseError(
                "get_recorridos: PuntoB Expected GEOS Point instance as parameter, %s given" % type(punto_b))
        if not isinstance(distancia_a, int):
            raise DatabaseError("get_recorridos: distancia_a Expected integer as parameter, %s given" % type(distancia_a))
        if not isinstance(distancia_b, int):
            raise DatabaseError("get_recorridos: distancia_b Expected integer as parameter, %s given" % type(distancia_b))
        if not isinstance(gap, int):
            raise DatabaseError("get_recorridos: gap Expected integer as parameter, %s given" % type(gap))
        if punto_a.srid != 4326 or punto_b.srid != 4326:
            punto_a = Point(punto_a.x, punto_a.y, srid=4326)
            punto_b = Point(punto_b.x, punto_b.y, srid=4326)
        distancia_a = 0.0000111 * float(distancia_a)
        distancia_b = 0.0000111 * float(distancia_b)
        gap = 0.0000111 * float(gap)

        connection.cursor().execute('SET STATEMENT_TIMEOUT=30000')

        params = {'punto_a': punto_a.ewkt, 'punto_b': punto_b.ewkt, 'rad1': distancia_a, 'rad2': distancia_b, 'gap': gap}
        query = """
            SELECT
                id,
                nombre,
                nombre2,
                id2,
                lineaslug,
                lineaslug2,
                slug,
                slug2,
                color_polilinea,
                color_polilinea2,
                foto,
                foto2,
                inicio,
                inicio2,
                fin,
                fin2,
                ST_AsText(ruta_corta) as ruta_corta,
                ST_AsText(ruta_corta2) as ruta_corta2,
                long_ruta,
                long_ruta2,
                long_pata,
                long_pata2,
                long_pata_transbordo,
                null as p11ll,
                null as p12ll,
                null as p21ll,
                null as p22ll
            FROM (
                SELECT
                    re1.id as id,
                    re2.id as id2,
                    li1.nombre || ' ' || re1.nombre as nombre,
                    li2.nombre || ' ' || re2.nombre as nombre2,
                    li1.slug as lineaslug,
                    li2.slug as lineaslug2,
                    re1.slug as slug,
                    re2.slug as slug2,
                    coalesce(re1.color_polilinea, li1.color_polilinea, '#000') as color_polilinea,
                    coalesce(re2.color_polilinea, li2.color_polilinea, '#000') as color_polilinea2,
                    coalesce(li1.foto, 'default') as foto,
                    coalesce(li2.foto, 'default') as foto2,
                    re1.inicio as inicio,
                    re2.inicio as inicio2,
                    re1.fin as fin,
                    re2.fin as fin2,
                    ST_AsText(
                        ST_LineSubstring(
                            re1.ruta,
                            ST_LineLocatePoint(re1.ruta, %(punto_a)s),
                            ST_LineLocatePoint(re1.ruta, ST_ClosestPoint(re1.ruta, re2.ruta))
                            )::Geography
                        ) as ruta_corta,
                    ST_AsText(
                        ST_LineSubstring(
                            re2.ruta,
                            ST_LineLocatePoint(re2.ruta, ST_ClosestPoint(re1.ruta, re2.ruta)),
                            ST_LineLocatePoint(re2.ruta, %(punto_b)s)
                            )::Geography
                        ) as ruta_corta2,
                    ST_Length(
                        ST_LineSubstring(
                            re1.ruta,
                            ST_LineLocatePoint(re1.ruta, %(punto_a)s),
                            ST_LineLocatePoint(re1.ruta, ST_ClosestPoint(re1.ruta, re2.ruta))
                            )::Geography
                        ) as long_ruta,
                    ST_Length(
                        ST_LineSubstring(
                            re2.ruta,
                            ST_LineLocatePoint(re2.ruta, ST_ClosestPoint(re1.ruta, re2.ruta)),
                            ST_LineLocatePoint(re2.ruta, %(punto_b)s)
                            )::Geography
                        ) as long_ruta2,
                    ST_DistanceSphere(ST_GeomFromText(%(punto_a)s), re1.ruta) as long_pata,
                    ST_DistanceSphere(ST_GeomFromText(%(punto_b)s), re2.ruta) as long_pata2,
                    ST_DistanceSphere(re1.ruta, re2.ruta) as long_pata_transbordo

                FROM
                    core_recorrido as re1
                    join core_recorrido as re2 on (re1.id <> re2.id)
                    join core_linea li1 on li1.id = re1.linea_id
                    join core_linea li2 on li2.id = re2.linea_id
                WHERE
                    ST_DWithin(ST_GeomFromText(%(punto_a)s), re1.ruta, %(rad1)s)
                    and
                    ST_DWithin(ST_GeomFromText(%(punto_b)s), re2.ruta, %(rad2)s)
                    and
                        ST_DWithin(re1.ruta, re2.ruta, %(gap)s)
                    and
                        ST_LineLocatePoint(re1.ruta, %(punto_a)s)
                        <
                        ST_LineLocatePoint(re1.ruta, ST_ClosestPoint(re1.ruta, re2.ruta) )
                    and
                        ST_LineLocatePoint(re2.ruta, ST_ClosestPoint(re1.ruta, re2.ruta) )
                        <
                        ST_LineLocatePoint(re2.ruta, %(punto_b)s)
                ) as subquery
            ORDER BY (cast(long_pata+long_pata2+long_pata_transbordo as integer)*100 + ( cast(long_ruta as integer) + cast(long_ruta2 as integer) ) ) ASC
        ;"""
        query_set = self.raw(query, params)
        try:
            return list(query_set)
        except DatabaseError:
            return []
