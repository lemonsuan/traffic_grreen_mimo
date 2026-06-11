"""
Analysis app serializers.
"""

from rest_framework import serializers
from .models import AnalysisReport, PerformanceMetric


class AnalysisReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisReport
        fields = '__all__'


class PerformanceMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceMetric
        fields = '__all__'


class MetricsQuerySerializer(serializers.Serializer):
    """指标查询请求"""
    network_id = serializers.IntegerField()
    node_id = serializers.CharField(required=False, allow_blank=True)
    metric_type = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    end_time = serializers.DateTimeField(required=False, allow_null=True)


class ComparisonRequestSerializer(serializers.Serializer):
    """对比请求"""
    result_ids = serializers.ListField(child=serializers.IntegerField())
    metrics = serializers.ListField(
        child=serializers.CharField(),
        default=['delay', 'queue', 'throughput', 'stops']
    )
