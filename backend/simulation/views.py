"""
Simulation app views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Simulation, SimulationSnapshot, SimulationMetrics
from .serializers import (
    SimulationSerializer, SimulationSnapshotSerializer,
    SimulationMetricsSerializer, SimulationStartSerializer
)
from .engine import SimulationEngine


# 存储运行中的仿真引擎
simulation_engines = {}


class SimulationViewSet(viewsets.ModelViewSet):
    queryset = Simulation.objects.all()
    serializer_class = SimulationSerializer
    filterset_fields = ['network', 'status']

    @action(detail=False, methods=['post'])
    def start(self, request):
        """启动仿真"""
        serializer = SimulationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 创建仿真记录
        simulation = Simulation.objects.create(
            network_id=serializer.validated_data['network_id'],
            name=f"Simulation_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            status='running',
            duration=serializer.validated_data.get('duration', 3600),
            step_size=serializer.validated_data.get('step_size', 1.0),
            speed_multiplier=serializer.validated_data.get('speed_multiplier', 1.0),
            random_seed=serializer.validated_data.get('random_seed'),
            started_at=timezone.now()
        )
        
        # 获取路网数据
        from network.models import Network
        network = Network.objects.get(id=simulation.network_id)
        network_data = self._prepare_network_data(network)
        
        # 创建仿真引擎
        engine = SimulationEngine(network_data, {
            'duration': simulation.duration,
            'step_size': simulation.step_size
        })
        
        simulation_engines[simulation.id] = engine
        
        return Response({
            'simulation_id': simulation.id,
            'status': simulation.status,
            'message': '仿真已启动'
        })

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止仿真"""
        simulation = self.get_object()
        simulation.status = 'completed'
        simulation.completed_at = timezone.now()
        
        # 获取最终结果
        engine = simulation_engines.get(simulation.id)
        if engine:
            simulation.results = engine.get_results()
            del simulation_engines[simulation.id]
        
        simulation.save()
        
        return Response({
            'simulation_id': simulation.id,
            'status': simulation.status,
            'results': simulation.results
        })

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停仿真"""
        simulation = self.get_object()
        simulation.status = 'paused'
        simulation.save()
        
        return Response({
            'simulation_id': simulation.id,
            'status': simulation.status
        })

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复仿真"""
        simulation = self.get_object()
        simulation.status = 'running'
        simulation.save()
        
        return Response({
            'simulation_id': simulation.id,
            'status': simulation.status
        })

    @action(detail=True, methods=['get'])
    def state(self, request, pk=None):
        """获取仿真状态"""
        simulation = self.get_object()
        
        engine = simulation_engines.get(simulation.id)
        if engine and simulation.status == 'running':
            # 执行一步仿真
            state = engine.step()
            
            # 更新仿真记录
            simulation.current_time = state['time']
            simulation.total_vehicles = len(state['vehicles'])
            simulation.save()
            
            # 检查是否完成
            if state['time'] >= simulation.duration:
                simulation.status = 'completed'
                simulation.completed_at = timezone.now()
                simulation.results = engine.get_results()
                simulation.save()
            
            return Response({
                'simulation_id': simulation.id,
                'status': simulation.status,
                'state': state
            })
        
        return Response({
            'simulation_id': simulation.id,
            'status': simulation.status,
            'current_time': simulation.current_time,
            'total_vehicles': simulation.total_vehicles,
            'completed_vehicles': simulation.completed_vehicles,
            'results': simulation.results
        })

    @action(detail=True, methods=['post'])
    def step_batch(self, request, pk=None):
        """批量执行多步仿真 (用于前端快速推进)"""
        simulation = self.get_object()
        
        engine = simulation_engines.get(simulation.id)
        if not engine or simulation.status != 'running':
            return Response({'error': '仿真未在运行'}, status=400)
        
        steps = min(int(request.data.get('steps', 10)), 100)
        state = None
        for _ in range(steps):
            state = engine.step()
            if state['time'] >= simulation.duration:
                break
        
        if state:
            simulation.current_time = state['time']
            simulation.total_vehicles = len(state['vehicles'])
            
            if state['time'] >= simulation.duration:
                simulation.status = 'completed'
                simulation.completed_at = timezone.now()
                simulation.results = engine.get_results()
            
            simulation.save()
            
            return Response({
                'simulation_id': simulation.id,
                'status': simulation.status,
                'state': state
            })
        
        return Response({'error': '无状态'}, status=500)

    @action(detail=True, methods=['get'])
    def snapshots(self, request, pk=None):
        """获取仿真快照列表"""
        simulation = self.get_object()
        snapshots = simulation.snapshots.all().order_by('time')
        serializer = SimulationSnapshotSerializer(snapshots, many=True)
        
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """获取仿真指标"""
        simulation = self.get_object()
        
        try:
            metrics = simulation.metrics.latest('id')
            serializer = SimulationMetricsSerializer(metrics)
            return Response(serializer.data)
        except SimulationMetrics.DoesNotExist:
            return Response({
                'avg_delay': 0,
                'avg_queue_length': 0,
                'max_queue_length': 0,
                'throughput': 0,
                'avg_stops': 0
            })

    def _prepare_network_data(self, network):
        """准备路网数据"""
        import random
        
        nodes = []
        for node in network.nodes.all():
            nodes.append({
                'id': node.node_id,
                'name': node.name,
                'type': node.node_type,
                'lng': node.lng,
                'lat': node.lat,
                'x': node.x,
                'y': node.y
            })
        
        # 根据道路等级设定默认流量
        flow_by_class = {
            'motorway': 1800, 'trunk': 1500, 'primary': 1200,
            'secondary': 800, 'tertiary': 500, 'residential': 200
        }
        
        edges = []
        for edge in network.edges.all():
            base_flow = flow_by_class.get(edge.road_class, 600)
            flow = base_flow * random.uniform(0.7, 1.3)
            edges.append({
                'id': edge.edge_id,
                'name': edge.name,
                'from': edge.from_node.node_id,
                'to': edge.to_node.node_id,
                'length': edge.length,
                'speed_limit': edge.speed_limit,
                'lanes': edge.lanes_count,
                'capacity': edge.capacity or (1800 * edge.lanes_count),
                'road_class': edge.road_class,
                'flow': round(flow)
            })
        
        signals = []
        for node in network.nodes.filter(signal__isnull=False):
            signal = node.signal
            phases = []
            for phase in signal.phases.all().order_by('phase_index'):
                green_links = list(
                    phase.phase_lanes.values_list('lane__edge__edge_id', flat=True)
                )
                phases.append({
                    'index': phase.phase_index,
                    'green': phase.green_time,
                    'yellow': phase.yellow_time,
                    'all_red': phase.all_red_time,
                    'green_links': green_links
                })
            
            signals.append({
                'node_id': node.node_id,
                'cycle_length': signal.cycle_length,
                'offset': signal.offset,
                'phases': phases
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'signals': signals
        }
