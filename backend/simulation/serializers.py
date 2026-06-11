"""
Simulation app serializers.
"""

from rest_framework import serializers
from .models import Simulation, SimulationSnapshot, SimulationMetrics


class SimulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Simulation
        fields = '__all__'


class SimulationSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationSnapshot
        fields = '__all__'


class SimulationMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationMetrics
        fields = '__all__'


class SimulationStartSerializer(serializers.Serializer):
    """仿真启动请求"""
    network_id = serializers.IntegerField()
    duration = serializers.IntegerField(default=3600)
    step_size = serializers.FloatField(default=1.0)
    speed_multiplier = serializers.FloatField(default=1.0)
    random_seed = serializers.IntegerField(required=False, allow_null=True)
    demand_id = serializers.IntegerField(required=False, allow_null=True)
    signal_timings = serializers.DictField(required=False, allow_null=True)


class SimulationStateSerializer(serializers.Serializer):
    """仿真状态响应"""
    simulation_id = serializers.CharField()
    status = serializers.CharField()
    current_time = serializers.FloatField()
    total_vehicles = serializers.IntegerField()
    completed_vehicles = serializers.IntegerField()
    metrics = serializers.DictField()
