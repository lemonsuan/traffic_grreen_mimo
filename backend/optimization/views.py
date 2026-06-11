"""
Optimization app views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import OptimizationResult, AlgorithmConfig
from .serializers import (
    OptimizationResultSerializer, AlgorithmConfigSerializer,
    IntersectionOptimizationSerializer, CorridorOptimizationSerializer,
    NetworkOptimizationSerializer
)
from .base import (
    OptimizerFactory, OptimizationContext, OptimizationLevel,
    OptimizationConstraints
)

# 导入优化器以触发注册
from . import intersection, corridor, network


class OptimizationResultViewSet(viewsets.ModelViewSet):
    queryset = OptimizationResult.objects.all()
    serializer_class = OptimizationResultSerializer
    filterset_fields = ['network', 'level', 'algorithm', 'is_applied']

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """应用优化方案到信号灯配置"""
        result = self.get_object()
        signal_timings = result.signal_timings or {}

        if not signal_timings:
            return Response(
                {'error': '该优化结果无配时方案'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from network.models import Node, Signal, Phase
        applied_count = 0

        for node_id, timing in signal_timings.items():
            try:
                node = Node.objects.filter(
                    network_id=result.network_id,
                    node_id=node_id
                ).first()
                if not node:
                    continue

                signal, _ = Signal.objects.update_or_create(
                    node=node,
                    defaults={
                        'signal_id': f'SIG_{node_id}',
                        'cycle_length': timing.get('cycle_length', 120),
                        'offset': timing.get('offset', 0),
                    }
                )

                Phase.objects.filter(signal=signal).delete()
                for i, phase_data in enumerate(timing.get('phases', [])):
                    Phase.objects.create(
                        signal=signal,
                        phase_index=phase_data.get('index', i),
                        green_time=phase_data.get('green', 30),
                        yellow_time=phase_data.get('yellow', 3),
                        all_red_time=phase_data.get('all_red', 1),
                    )
                applied_count += 1
            except Exception as e:
                continue

        result.is_applied = True
        result.applied_at = timezone.now()
        result.save()

        return Response({
            'message': f'优化方案已应用到 {applied_count} 个路口',
            'result_id': result.id,
            'applied_count': applied_count
        })


class AlgorithmConfigViewSet(viewsets.ModelViewSet):
    queryset = AlgorithmConfig.objects.all()
    serializer_class = AlgorithmConfigSerializer
    filterset_fields = ['level', 'is_enabled']


class OptimizationViewSet(viewsets.ViewSet):
    """优化接口"""
    
    @action(detail=False, methods=['get'])
    def algorithms(self, request):
        """获取可用算法列表"""
        level = request.query_params.get('level', None)
        
        if level:
            algorithms = OptimizerFactory.get_available_algorithms(level)
        else:
            algorithms = {
                'intersection': OptimizerFactory.get_available_algorithms('intersection'),
                'corridor': OptimizerFactory.get_available_algorithms('corridor'),
                'network': OptimizerFactory.get_available_algorithms('network'),
            }
        
        return Response({'algorithms': algorithms})
    
    @action(detail=False, methods=['post'])
    def intersection(self, request):
        """单点优化"""
        serializer = IntersectionOptimizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # 获取节点数据
        from network.models import Node
        try:
            node = Node.objects.get(node_id=data['node_id'])
        except Node.DoesNotExist:
            return Response(
                {'error': f'节点 {data["node_id"]} 不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 创建优化上下文
        context = OptimizationContext(
            level=OptimizationLevel.INTERSECTION,
            network_id=node.network_id,
            node_ids=[data['node_id']],
            traffic_data=data.get('traffic_data', {}),
            constraints=OptimizationConstraints(),
            params=data.get('params', {})
        )
        
        # 获取优化器
        algorithm = data.get('algorithm', 'webster')
        
        try:
            optimizer = OptimizerFactory.create(context, algorithm)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 执行优化
        if not optimizer.validate_inputs():
            return Response(
                {'error': '输入数据验证失败'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = optimizer.optimize()
        
        # 保存结果
        db_result = OptimizationResult.objects.create(
            network_id=node.network_id,
            level='intersection',
            algorithm=algorithm,
            signal_timings={k: v.to_dict() for k, v in result.signal_timings.items()},
            performance=result.performance.to_dict(),
            computation_time=result.computation_time
        )
        
        return Response({
            'result_id': db_result.id,
            'algorithm': result.algorithm,
            'signal_timings': result.signal_timings,
            'performance': result.performance.to_dict(),
            'computation_time': result.computation_time
        })
    
    @action(detail=False, methods=['post'])
    def corridor(self, request):
        """干线优化"""
        serializer = CorridorOptimizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        node_ids = data['node_ids']
        
        # 获取路网数据
        from network.models import Node, Edge
        nodes = Node.objects.filter(node_id__in=node_ids)
        
        if nodes.count() < 2:
            return Response(
                {'error': '至少需要2个节点'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 准备干线数据
        corridor_data = self._prepare_corridor_data(nodes, node_ids)
        
        # 创建优化上下文
        context = OptimizationContext(
            level=OptimizationLevel.CORRIDOR,
            network_id=nodes.first().network_id,
            node_ids=node_ids,
            traffic_data={'corridor_data': corridor_data},
            constraints=OptimizationConstraints(),
            params=data.get('params', {})
        )
        
        # 获取优化器
        algorithm = data.get('algorithm', 'maxband')
        
        try:
            optimizer = OptimizerFactory.create(context, algorithm)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 执行优化
        if not optimizer.validate_inputs():
            return Response(
                {'error': '输入数据验证失败'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = optimizer.optimize()
        
        # 保存结果
        db_result = OptimizationResult.objects.create(
            network_id=nodes.first().network_id,
            level='corridor',
            algorithm=algorithm,
            signal_timings={k: v.to_dict() for k, v in result.signal_timings.items()},
            performance=result.performance.to_dict(),
            computation_time=result.computation_time
        )
        
        response_data = {
            'result_id': db_result.id,
            'algorithm': result.algorithm,
            'signal_timings': {
                k: v.to_dict() for k, v in result.signal_timings.items()
            },
            'performance': result.performance.to_dict(),
            'computation_time': result.computation_time,
        }

        if result.convergence:
            response_data['convergence'] = result.convergence

        return Response(response_data)
    
    @action(detail=False, methods=['post'])
    def network(self, request):
        """区域优化"""
        serializer = NetworkOptimizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        network_id = data['network_id']
        node_ids = data.get('node_ids', [])

        # 获取路网数据
        from network.models import Node, Edge
        nodes_qs = Node.objects.filter(network_id=network_id)
        if node_ids:
            nodes_qs = nodes_qs.filter(node_id__in=node_ids)

        node_ids = list(nodes_qs.values_list('node_id', flat=True))
        if len(node_ids) < 2:
            return Response(
                {'error': '至少需要2个节点'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 准备区域路网数据
        network_data = self._prepare_network_data(nodes_qs, node_ids)

        # 创建优化上下文
        context = OptimizationContext(
            level=OptimizationLevel.NETWORK,
            network_id=network_id,
            node_ids=node_ids,
            traffic_data={'network_data': network_data},
            constraints=OptimizationConstraints(),
            params=data.get('params', {})
        )

        algorithm = data.get('algorithm', 'transyt')

        try:
            optimizer = OptimizerFactory.create(context, algorithm)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not optimizer.validate_inputs():
            return Response(
                {'error': '输入数据验证失败'},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = optimizer.optimize()

        db_result = OptimizationResult.objects.create(
            network_id=network_id,
            level='network',
            algorithm=algorithm,
            signal_timings={k: v.to_dict() for k, v in result.signal_timings.items()},
            performance=result.performance.to_dict(),
            computation_time=result.computation_time
        )

        response_data = {
            'result_id': db_result.id,
            'algorithm': result.algorithm,
            'signal_timings': {
                k: v.to_dict() for k, v in result.signal_timings.items()
            },
            'performance': result.performance.to_dict(),
            'computation_time': result.computation_time,
            'convergence': result.convergence[:50] if result.convergence else [],
        }

        if result.pareto_front:
            response_data['pareto_front'] = result.pareto_front

        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def compare(self, request):
        """对比优化结果"""
        result_ids = request.query_params.getlist('result_ids', [])
        
        if not result_ids:
            return Response(
                {'error': '请提供至少一个结果ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = OptimizationResult.objects.filter(id__in=result_ids)
        serializer = OptimizationResultSerializer(results, many=True)
        
        return Response({'results': serializer.data})
    
    def _prepare_corridor_data(self, nodes, node_ids):
        """准备干线数据"""
        from network.models import Edge, Signal
        
        corridor_data = {
            'nodes': {},
            'edges': {}
        }
        
        # 节点数据
        for node in nodes:
            node_data = {
                'id': node.node_id,
                'name': node.name,
                'lng': node.lng,
                'lat': node.lat
            }
            
            # 获取信号灯配置
            try:
                signal = Signal.objects.get(node=node)
                node_data['cycle_length'] = signal.cycle_length
                node_data['offset'] = signal.offset
                
                # 获取相位配置
                phases = signal.phases.all().order_by('phase_index')
                if phases.exists():
                    node_data['green_ns'] = phases[0].green_time if phases.count() > 0 else 45
                    node_data['green_ew'] = phases[1].green_time if phases.count() > 1 else 35
            except Signal.DoesNotExist:
                node_data['cycle_length'] = 120
                node_data['green_ns'] = 45
                node_data['green_ew'] = 35
            
            corridor_data['nodes'][node.node_id] = node_data
        
        # 路段数据
        for i in range(len(node_ids) - 1):
            from_id = node_ids[i]
            to_id = node_ids[i + 1]
            
            try:
                edge = Edge.objects.get(
                    from_node__node_id=from_id,
                    to_node__node_id=to_id
                )
                edge_data = {
                    'length': edge.length,
                    'speed_limit': edge.speed_limit,
                    'lanes': edge.lanes_count
                }
            except Edge.DoesNotExist:
                edge_data = {
                    'length': 500,  # 默认500米
                    'speed_limit': 50,
                    'lanes': 2
                }
            
            edge_key = f"{from_id}_{to_id}"
            corridor_data['edges'][edge_key] = edge_data
        
        return corridor_data

    def _prepare_network_data(self, nodes_qs, node_ids):
        """准备区域路网数据"""
        from network.models import Edge, Signal

        network_data = {
            'nodes': {},
            'edges': []
        }

        for node in nodes_qs:
            node_data = {
                'id': node.node_id,
                'name': node.name,
                'lng': node.lng,
                'lat': node.lat
            }

            try:
                signal = Signal.objects.get(node=node)
                node_data['cycle_length'] = signal.cycle_length
                node_data['offset'] = signal.offset
                phases = signal.phases.all().order_by('phase_index')
                if phases.exists():
                    node_data['green_ns'] = phases[0].green_time if phases.count() > 0 else 45
                    node_data['green_ew'] = phases[1].green_time if phases.count() > 1 else 35
            except Signal.DoesNotExist:
                node_data['cycle_length'] = 120
                node_data['green_ns'] = 45
                node_data['green_ew'] = 35

            network_data['nodes'][node.node_id] = node_data

        edges = Edge.objects.filter(
            from_node__node_id__in=node_ids,
            to_node__node_id__in=node_ids
        )

        for edge in edges:
            speed_ms = edge.speed_limit / 3.6
            network_data['edges'].append({
                'from': edge.from_node.node_id,
                'to': edge.to_node.node_id,
                'length': edge.length,
                'speed_limit': edge.speed_limit,
                'lanes': edge.lanes_count,
                'flow': getattr(edge, 'volume', 0) or 0,
                'travel_time': edge.length / speed_ms if speed_ms > 0 else 30
            })

        return network_data

    @action(detail=False, methods=['post'])
    def auto_optimize(self, request):
        """一键自动优化"""
        from .pipeline import OptimizationPipeline

        network_id = request.data.get('network_id')
        if not network_id:
            return Response(
                {'error': '请提供 network_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from network.models import Network, Node, Edge, Signal
        try:
            network = Network.objects.get(id=network_id)
        except Network.DoesNotExist:
            return Response(
                {'error': f'路网 {network_id} 不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        network_data = self._prepare_network_data_full(network)

        pipeline = OptimizationPipeline(
            network_id=network_id,
            network_data=network_data
        )

        result = pipeline.auto_optimize()

        from analysis.report_generator import ReportGenerator
        report = ReportGenerator.generate_optimization_report(result, network.name)

        return Response({
            'result': result,
            'report': report
        })

    def _prepare_network_data_full(self, network):
        """准备完整路网数据 (用于管线优化)"""
        from network.models import Node, Edge, Signal

        network_data = {'nodes': {}, 'edges': []}

        for node in network.nodes.all():
            node_data = {
                'id': node.node_id,
                'name': node.name,
                'lng': node.lng,
                'lat': node.lat
            }
            try:
                signal = Signal.objects.get(node=node)
                node_data['cycle_length'] = signal.cycle_length
                node_data['offset'] = signal.offset
                phases = signal.phases.all().order_by('phase_index')
                if phases.exists():
                    node_data['green_ns'] = phases[0].green_time if phases.count() > 0 else 45
                    node_data['green_ew'] = phases[1].green_time if phases.count() > 1 else 35
            except Signal.DoesNotExist:
                node_data['cycle_length'] = 120
                node_data['green_ns'] = 45
                node_data['green_ew'] = 35

            network_data['nodes'][node.node_id] = node_data

        for edge in network.edges.all():
            speed_ms = edge.speed_limit / 3.6
            network_data['edges'].append({
                'from_node': edge.from_node.node_id,
                'to_node': edge.to_node.node_id,
                'from': edge.from_node.node_id,
                'to': edge.to_node.node_id,
                'length': edge.length,
                'speed_limit': edge.speed_limit,
                'lanes': edge.lanes_count,
                'flow': 500,
                'travel_time': edge.length / speed_ms if speed_ms > 0 else 30,
                'road_class': edge.road_class,
                'capacity': edge.capacity
            })

        return network_data
