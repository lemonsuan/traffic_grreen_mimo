"""
Network app admin configuration.
"""

from django.contrib import admin
from .models import (
    Network, Node, Intersection, Roundabout, Edge, Lane,
    LaneConnection, Signal, Phase, PhaseLane, TrafficDemand, ODMatrix
)


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ['node_id', 'name', 'node_type', 'network']
    list_filter = ['node_type', 'network']
    search_fields = ['node_id', 'name']


@admin.register(Intersection)
class IntersectionAdmin(admin.ModelAdmin):
    list_display = ['node', 'intersection_type', 'control_type']
    list_filter = ['intersection_type', 'control_type']


@admin.register(Roundabout)
class RoundaboutAdmin(admin.ModelAdmin):
    list_display = ['node', 'radius', 'lanes_count']


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ['edge_id', 'name', 'from_node', 'to_node', 'length', 'speed_limit']
    list_filter = ['road_class', 'network']
    search_fields = ['edge_id', 'name']


@admin.register(Lane)
class LaneAdmin(admin.ModelAdmin):
    list_display = ['edge', 'lane_index', 'lane_type', 'width']
    list_filter = ['lane_type']


@admin.register(LaneConnection)
class LaneConnectionAdmin(admin.ModelAdmin):
    list_display = ['from_lane', 'to_lane', 'connection_type']


@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ['node', 'signal_id', 'cycle_length', 'offset', 'control_mode']
    list_filter = ['control_mode']


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    list_display = ['signal', 'phase_index', 'green_time', 'yellow_time', 'phase_type']
    list_filter = ['phase_type']


@admin.register(PhaseLane)
class PhaseLaneAdmin(admin.ModelAdmin):
    list_display = ['phase', 'lane', 'has_right_of_way']


@admin.register(TrafficDemand)
class TrafficDemandAdmin(admin.ModelAdmin):
    list_display = ['name', 'network', 'demand_type', 'time_start', 'time_end']
    list_filter = ['demand_type']


@admin.register(ODMatrix)
class ODMatrixAdmin(admin.ModelAdmin):
    list_display = ['demand', 'from_node', 'to_node', 'flow']
