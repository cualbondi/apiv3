FROM python:2

MAINTAINER Cualbondi

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      osm2pgsql \
      osmctools \
      libgeos-dev \
      gdal-bin && \
    rm -rf /var/lib/apt/lists/* && \
    pip install uwsgi



ENV APP_PATH=/app

WORKDIR $APP_PATH

COPY requirements.txt $APP_PATH/

RUN pip install -r requirements.txt

EXPOSE 8000

COPY . $APP_PATH/

CMD ["uwsgi", "--ini", "/app/uwsgi.ini"]
