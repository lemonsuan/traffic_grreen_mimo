"""
URL configuration for traffic_grreen project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/networks/', include('network.urls')),
    path('api/v1/simulation/', include('simulation.urls')),
    path('api/v1/optimization/', include('optimization.urls')),
    path('api/v1/analysis/', include('analysis.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
