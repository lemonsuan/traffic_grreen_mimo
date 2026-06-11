"""
Simulation app admin.
"""

from django.contrib import admin
from .models import Simulation, SimulationSnapshot, SimulationMetrics


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    list_display = ['name', 'network', 'status', 'current_time', 'total_vehicles']
    list_filter = ['status', 'network']
    search_fields = ['name']


@admin.register(SimulationSnapshot)
class SimulationSnapshotAdmin(admin.ModelAdmin):
    list_display = ['simulation', 'time']
    list_filter = ['simulation']


@admin.register(SimulationMetrics)
class SimulationMetricsAdmin(admin.ModelAdmin):
    list_display = ['simulation', 'avg_delay', 'avg_queue_length', 'throughput']
