"""
Analysis app URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.AnalysisReportViewSet)
router.register(r'performance-metrics', views.PerformanceMetricViewSet)
router.register(r'', views.AnalysisViewSet, basename='analysis')

urlpatterns = [
    path('', include(router.urls)),
]
