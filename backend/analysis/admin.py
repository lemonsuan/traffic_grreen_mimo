"""
Analysis app admin.
"""

from django.contrib import admin
from .models import AnalysisReport, PerformanceMetric


@admin.register(AnalysisReport)
class AnalysisReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'network', 'report_type', 'created_at']
    list_filter = ['report_type', 'network']
    search_fields = ['name']


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(admin.ModelAdmin):
    list_display = ['network', 'node_id', 'metric_type', 'value', 'timestamp']
    list_filter = ['metric_type', 'network']
