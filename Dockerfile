FROM cualbondi/django

MAINTAINER Cualbondi

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client

# Copy content into WORKDIR
COPY . .

CMD ["./entrypoint.sh", "db", "python", "manage.py", "runserver", "0.0.0.0:8000"]