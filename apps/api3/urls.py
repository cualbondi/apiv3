from django.conf.urls import url, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(r'ciudades', views.CiudadesViewSet)
router.register(r'lineas', views.LineasViewSet)
router.register(r'recorridos', views.RecorridosViewSet)
router.register(r'geocoder', views.GeocoderViewSet, "geocoder")

urlpatterns = [
    url(r'^auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^recorridos-por-ciudad/(?P<ciudad_id>\d+)/$', views.RecorridosPorCiudad.as_view({'get': 'list'})),
    url(r'^match-recorridos/(?P<recorrido_id>\d+)/$', views.match_recorridos),
    url(r'^display-recorridos/', views.display_recorridos),
    url(r'^', include((router.urls, 'v3'), namespace='v3')),
]
