"""
Optimization app serializers.
"""

from rest_framework import serializers
from .models import OptimizationResult, AlgorithmConfig


class OptimizationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationResult
        fields = '__all__'


class AlgorithmConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlgorithmConfig
        fields = '__all__'


class IntersectionOptimizationSerializer(serializers.Serializer):
    """单点优化请求"""
    node_id = serializers.CharField()
    algorithm = serializers.CharField(default='webster')
    params = serializers.DictField(required=False, default=dict)
    traffic_data = serializers.DictField(required=False, default=dict)


class CorridorOptimizationSerializer(serializers.Serializer):
    """干线优化请求"""
    node_ids = serializers.ListField(child=serializers.CharField())
    direction = serializers.ChoiceField(
        choices=['inbound', 'outbound', 'both'],
        default='both'
    )
    algorithm = serializers.CharField(default='maxband')
    params = serializers.DictField(required=False, default=dict)


class NetworkOptimizationSerializer(serializers.Serializer):
    """区域优化请求"""
    network_id = serializers.IntegerField()
    node_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    algorithm = serializers.CharField(default='transyt')
    params = serializers.DictField(required=False, default=dict)
