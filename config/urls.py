from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin

from rest_framework.documentation import include_docs_urls

from apps.api3.urls import urlpatterns as v3urls

urlpatterns = [
    # admin
    url(settings.ADMIN_URL, admin.site.urls),
    url(r'^docs/', include_docs_urls(title='Cualbondi API v3')),
    url(r"^", include(v3urls)),
    url(r'^api/', include(v3urls)),
    # TODO: remove this legacy endpoint once web has been updated
    url(r'^v2/', include(v3urls)),
    url(r'^api/v3/', include(v3urls)),
    # url(r'^widget/', include('apps.widget.urls')),

] + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)

if hasattr(settings, 'SILK') and settings.SILK:
    urlpatterns += [url(r'^silk/', include('silk.urls', namespace='silk'))]

if settings.DEBUG:
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [url(r"^__debug__/", include(debug_toolbar.urls))] + urlpatterns
