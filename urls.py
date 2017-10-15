from django.conf.urls import patterns, include, url
from django.contrib.gis import admin
import settings

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

urlpatterns = patterns('',
    # Archivos estaticos
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),

    # APPS de CualBondi
    url(r'^api/v2/', include('apps.api2.urls')),
    url(r'^api/v1/', include('apps.api.urls')),
    url(r'^api/', include('apps.api.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^widget/', include('apps.widget.urls')),

    url(r'^/', include('apps.api2.urls')),
)
