"""
Optimization app URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'results', views.OptimizationResultViewSet)
router.register(r'algorithms', views.AlgorithmConfigViewSet)
router.register(r'', views.OptimizationViewSet, basename='optimization')

urlpatterns = [
    path('', include(router.urls)),
]
