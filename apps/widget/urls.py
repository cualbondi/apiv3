from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.not_found),
    url(r'^v1/busqueda.js$', views.v1_busqueda, { 'extension': 'js' }, name='v1_busqueda_js'),
    url(r'^v1/busqueda.html$', views.v1_busqueda, { 'extension': 'html' }, name='v1_busqueda_html'),
    url(r'^v1/lineas.js$', views.v1_lineas, { 'extension': 'js' }, name='v1_lineas_js'),
    url(r'^v1/lineas.html$', views.v1_lineas, { 'extension': 'html' }, name='v1_lineas_html'),
    url(r'^test.html$', views.test),
]
