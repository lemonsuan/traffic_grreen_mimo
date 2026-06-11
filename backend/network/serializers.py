"""
Network app serializers.
"""

from rest_framework import serializers
from .models import (
    Network, Node, Intersection, Roundabout, Edge, Lane,
    LaneConnection, Signal, Phase, PhaseLane, TrafficDemand, ODMatrix
)


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = '__all__'


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = '__all__'


class IntersectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intersection
        fields = '__all__'


class RoundaboutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roundabout
        fields = '__all__'


class EdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edge
        fields = '__all__'


class LaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lane
        fields = '__all__'


class LaneConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaneConnection
        fields = '__all__'


class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signal
        fields = '__all__'


class PhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phase
        fields = '__all__'


class PhaseLaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhaseLane
        fields = '__all__'


class TrafficDemandSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficDemand
        fields = '__all__'


class ODMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = ODMatrix
        fields = '__all__'


class NetworkDetailSerializer(serializers.ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)
    edges = EdgeSerializer(many=True, read_only=True)
    demands = TrafficDemandSerializer(many=True, read_only=True)

    class Meta:
        model = Network
        fields = '__all__'
