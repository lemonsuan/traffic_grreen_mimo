"""
Network app URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.NetworkViewSet)
router.register(r'nodes', views.NodeViewSet)
router.register(r'intersections', views.IntersectionViewSet)
router.register(r'roundabouts', views.RoundaboutViewSet)
router.register(r'edges', views.EdgeViewSet)
router.register(r'lanes', views.LaneViewSet)
router.register(r'lane-connections', views.LaneConnectionViewSet)
router.register(r'signals', views.SignalViewSet)
router.register(r'phases', views.PhaseViewSet)
router.register(r'phase-lanes', views.PhaseLaneViewSet)
router.register(r'demands', views.TrafficDemandViewSet)
router.register(r'od-matrices', views.ODMatrixViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
