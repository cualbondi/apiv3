import uuid

from django.contrib.gis.db import models
from django.db.models import Manager as GeoManager
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.urls import reverse

from apps.catastro.models import Ciudad
from .managers import RecorridoManager


class Linea(models.Model):
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True, null=False)
    descripcion = models.TextField(blank=True, null=True)
    foto = models.CharField(max_length=20, blank=True, null=True)
    img_panorama = models.ImageField(max_length=200, upload_to='linea', blank=True, null=True)
    img_cuadrada = models.ImageField(max_length=200, upload_to='linea', blank=True, null=True)
    color_polilinea = models.CharField(max_length=20, blank=True, null=True)
    info_empresa = models.TextField(blank=True, null=True)
    info_terminal = models.TextField(blank=True, null=True)
    localidad = models.CharField(max_length=50, blank=True, null=True)
    cp = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=200, blank=True, null=True)
    envolvente = models.PolygonField(blank=True, null=True)

    @property
    def ciudades(self):
        return Ciudad.objects.filter(lineas=self)

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.slug = slugify(self.nombre)
        super(Linea, self).save(*args, **kwargs)

    def get_absolute_url(self, ciudad_slug=None):
        # chequear si la linea está en esta ciudad, sino tirar excepcion
        if ciudad_slug is None:
            try:
                ciudad_slug = Ciudad.objects.filter(lineas=self)[0].slug
            except:
                print(self)
                return ""
        else:
            get_object_or_404(Ciudad, slug=ciudad_slug, lineas=self)
        return reverse('ver_linea',
                       kwargs={
                           'nombre_ciudad': ciudad_slug,
                           'nombre_linea': self.slug
                       })


class Recorrido(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    nombre = models.CharField(max_length=100)
    img_panorama = models.ImageField(max_length=200, upload_to='recorrido', blank=True, null=True)
    img_cuadrada = models.ImageField(max_length=200, upload_to='recorrido', blank=True, null=True)
    linea = models.ForeignKey(Linea, on_delete=models.CASCADE)
    ruta = models.LineStringField()
    sentido = models.CharField(max_length=100, blank=True, null=False)
    slug = models.SlugField(max_length=200, blank=True, null=False)
    inicio = models.CharField(max_length=100, blank=True, null=False)
    fin = models.CharField(max_length=100, blank=True, null=False)
    semirrapido = models.BooleanField(default=False)
    color_polilinea = models.CharField(max_length=20, blank=True, null=True)
    horarios = models.TextField(blank=True, null=True)
    pois = models.TextField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    osm_id = models.TextField(blank=True, null=True)
    osm_sync = models.BooleanField(default=False)

    # Si tiene las paradas completas es porque tiene todas las paradas de
    # este recorrido en la tabla paradas+horarios (horarios puede ser null),
    # y se puede utilizar en la busqueda usando solo las paradas.
    paradas_completas = models.BooleanField(default=False)

    objects = RecorridoManager()

    @property
    def ciudades(self):
        return Ciudad.objects.filter(lineas=self.linea)

    def __str__(self):
        # return str(self.ciudad_set.all()[0]) + " - " + str(self.linea) + " - " + self.nombre
        return str(self.linea) + " - " + self.nombre

    def save(self, *args, **kwargs):
        # Generar el SLUG a partir del origen y destino del recorrido
        self.slug = slugify(self.nombre + " desde " + self.inicio + " hasta " + self.fin)

        # Asegurarse de que no haya 'inicio' y/o 'fin' invalidos
        assert (
            self.inicio != self.fin
            and self.inicio != ''
            and self.fin != ''
        ), "Los campos 'inicio' y 'fin' no pueden ser vacios y/o iguales"

        # Ejecutar el SAVE original
        super(Recorrido, self).save(*args, **kwargs)

        # Ver que ciudades intersecta
        ciudades = Ciudad.objects.all()
        for ciudad in ciudades:
            if ciudad.poligono.intersects(self.ruta):
                ciudad.recorridos.add(self)
                ciudad.lineas.add(self.linea)

    class Meta:
        ordering = ['linea__nombre', 'nombre']

    def get_absolute_url(self, ciudad_slug=None, linea_slug=None, slug=None):
        # chequear si la linea/recorrido está en esta ciudad, sino tirar excepcion
        if ciudad_slug is None:
            try:
                ciudad_slug = self.ciudad_slug
            except:
                try:
                    ciudad_slug = Ciudad.objects.filter(lineas=self.linea)[0].slug
                except:
                    print(self)
                    return ""
                    # raise
        else:
            # Esto lo comento porque hace muuuy lento a todo el sistema.
            # Mas vale tomo como que el slug esta siempre bien. De ultima como mucho, me genera un link que da un 404.
            # get_object_or_404(Ciudad, slug=ciudad_slug, lineas=self.linea)
            pass
        if linea_slug is None:
            try:
                linea_slug = self.linea_slug
            except:
                linea_slug = self.linea.slug  # Esto genera una consulta mas
        if slug is None:
            slug = self.slug  # Esto puede generar otra a veces
        return reverse('ver_recorrido',
                       kwargs={
                           'nombre_ciudad': ciudad_slug,
                           'nombre_linea': linea_slug,
                           'nombre_recorrido': slug
                       })


class Posicion(models.Model):
    """Ubicacion geografica de un recorrido en cierto momento del tiempo"""

    class Meta:
        verbose_name = 'Posicion'
        verbose_name_plural = 'Posiciones'

    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    dispositivo_uuid = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=True)
    latlng = models.PointField()

    objects = GeoManager()

    def __str__(self):
        return '{recorrido} ({hora}) - {punto}'.format(
            recorrido=self.recorrido,
            punto=self.latlng,
            hora=self.timestamp.strftime("%d %h %Y %H:%M:%S")
        )


class Comercio(models.Model):
    nombre = models.CharField(max_length=100)
    latlng = models.PointField()
    ciudad = models.ForeignKey(Ciudad, on_delete=models.CASCADE)
    objects = GeoManager()


class Parada(models.Model):
    codigo = models.CharField(max_length=15, blank=True, null=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    latlng = models.PointField()
    objects = GeoManager()

    def __str__(self):
        return self.nombre or self.codigo or "{}, {}".format(self.latlng.x, self.latlng.y)

    def get_absolute_url(self):
        return reverse('ver_parada', kwargs={'id': self.id})


class Horario(models.Model):
    """ Un "Recorrido" pasa por una "Parada" a
        cierto "Horario". "Horario" es el modelo
        interpuesto entre "Recorrido" y "Parada"
    """
    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE)
    hora = models.CharField(max_length=5, blank=True, null=True)

    def __str__(self):
        return str(self.recorrido) + " - " + str(self.parada) + " - " + str(self.hora or ' ')


class Terminal(models.Model):
    linea = models.ForeignKey(Linea, on_delete=models.CASCADE)
    descripcion = models.TextField(blank=True, null=True)
    direccion = models.CharField(max_length=150)
    telefono = models.CharField(max_length=150)
    latlng = models.PointField()
    objects = GeoManager()


class Tarifa(models.Model):
    tipo = models.CharField(max_length=150)
    precio = models.DecimalField(max_digits=5, decimal_places=2)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.CASCADE)

    def __str__(self):
        return '{0} - {1} - ${2}'.format(self.ciudad, self.tipo, self.precio)


class FacebookPage(models.Model):
    id_fb = models.CharField(max_length=50)
    linea = models.ForeignKey(Linea, on_delete=models.CASCADE)
