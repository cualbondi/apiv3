#!/bin/bash
apt update && apt install postgresql-client
curl https://download.geofabrik.de/south-america/argentina-latest.osm.pbf -o ./osm/argentina-latest.osm.pbf
psql --host=db --username=$POSTGRES_USER --dbname=$POSTGRES_DB -f /app/osm/extensions.sql
osm2pgsql --cache 100 -E 3857 --slim --cache-strategy sparse -d $POSTGRES_DB -H db -U $POSTGRES_USER -W -P 5432 --hstore --hstore-add-index ./osm/argentina-latest.osm.pbf
psql --host=db --username=$POSTGRES_USER --dbname=$POSTGRES_DB -f /app/osm/merge.sql

# optional: clear unused tables
# psql --host=db --username=$POSTGRES_USER --dbname=$POSTGRES_DB -f /app/osm/delete_extra_tables.sql
