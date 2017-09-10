#!/bin/sh

set -ex

host="$1"
shift
cmd="$@"

# Helper for quickly postgres connection
postgres_connect="PGPASSWORD=${DB_PASSWORD} psql -h $host -U${DB_USER} -d $DB_NAME"

# Wait for postgres
until eval "$postgres_connect -c '\l'"; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 3
done

# Add Postgres functions & extensions
eval "$postgres_connect <<-HEREDOC1
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  CREATE EXTENSION IF NOT EXISTS postgis;
  
  CREATE OR REPLACE FUNCTION
      min_linestring ( "line1" Geometry, "line2" Geometry )
      RETURNS geometry
      AS \\\$$
      BEGIN
          IF ST_Length2D_Spheroid(line1, 'SPHEROID["GRS_1980",6378137,298.257222101]') < ST_Length2D_Spheroid(line2, 'SPHEROID["GRS_1980",6378137,298.257222101]') THEN
              RETURN line1;
          ELSE
              RETURN line2;
          END IF;
      END;
      \\\$$ LANGUAGE plpgsql;

  DROP AGGREGATE IF EXISTS min_path(Geometry);

  CREATE AGGREGATE min_path(Geometry)(SFUNC = min_linestring, STYPE = Geometry);

HEREDOC1"

exec $cmd