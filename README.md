# Cualbondi

[![wercker status](https://app.wercker.com/status/d93ca25465dc45adb58b99c01e0662ff/s/master "wercker status")](https://app.wercker.com/project/byKey/d93ca25465dc45adb58b99c01e0662ff)

[![Coverage Status](https://coveralls.io/repos/github/cualbondi/cualbondi.com.ar/badge.svg?branch=HEAD)](https://coveralls.io/github/cualbondi/cualbondi.com.ar?branch=HEAD)

[![Code Climate](https://codeclimate.com/github/cualbondi/cualbondi.com.ar/badges/gpa.svg)](https://codeclimate.com/github/cualbondi/cualbondi.com.ar)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e36cba74aeca4d3387a0b41c029419bd)](https://www.codacy.com/app/jperelli/cualbondi-com-ar?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=cualbondi/cualbondi.com.ar&amp;utm_campaign=Badge_Grade)

## Requirements

* latest version of Docker and Compose

## How to install

**Copy and edit our env file**

`mv .env.example .env && nano .env`

**Build the image**

`docker-compose build`

**Run the containers**

`docker-compose up -d` 

**NOTE**: It tooks a little bit of time (seconds). You have to wait for it, before run the migrations. 
You can see if it is ready with `docker-compose logs -f api` command.

**Run the migrations**

`docker-compose exec api python manage.py syncdb`

**Run the fixtures**

`docker-compose exec api util/load_fixtures.sh`

#### Ready!

Now you can go to http://localhost:8000/ in the browser and enjoy cualbondi.

To access django's admin interface go to http://localhost:8000/admin/ and login with user `admin` pass `admin`

## License

Cualbondi software is distributed under GNU AGPLv3. See LICENSE file on directory root.

## Developers

- Julian Perelli
- Martin Zugnoni
- Bruno Cascio
