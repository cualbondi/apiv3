select osm_id, ref, name, st_linemerge(st_union(way)) as way
into bus_routes
from planet_osm_line
where route='bus'
group by osm_id, ref, name
order by osm_id;

create index bus_routes_idx on bus_routes using gist(way);
alter table bus_routes add primary key (osm_id);
