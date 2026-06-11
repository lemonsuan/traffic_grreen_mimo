"""
Optimization app admin.
"""

from django.contrib import admin
from .models import OptimizationResult, AlgorithmConfig


@admin.register(OptimizationResult)
class OptimizationResultAdmin(admin.ModelAdmin):
    list_display = ['network', 'level', 'algorithm', 'computation_time', 'is_applied', 'created_at']
    list_filter = ['level', 'algorithm', 'is_applied']
    search_fields = ['name']


@admin.register(AlgorithmConfig)
class AlgorithmConfigAdmin(admin.ModelAdmin):
    list_display = ['level', 'algorithm', 'name', 'is_enabled']
    list_filter = ['level', 'is_enabled']
