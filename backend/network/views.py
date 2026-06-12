"""
Network app views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import (
    Network, Node, Intersection, Roundabout, Edge, Lane,
    LaneConnection, Signal, Phase, PhaseLane, TrafficDemand, ODMatrix
)
from .serializers import (
    NetworkSerializer, NetworkDetailSerializer, NodeSerializer,
    IntersectionSerializer, RoundaboutSerializer, EdgeSerializer,
    LaneSerializer, LaneConnectionSerializer, SignalSerializer,
    PhaseSerializer, PhaseLaneSerializer, TrafficDemandSerializer,
    ODMatrixSerializer
)


class NetworkViewSet(viewsets.ModelViewSet):
    queryset = Network.objects.all()
    serializer_class = NetworkSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return NetworkDetailSerializer
        return NetworkSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """自动生成路网"""
        from .generator import NetworkGenerator

        gen_type = request.data.get('type', 'grid')
        params = request.data.get('params', {})

        if gen_type == 'grid':
            data = NetworkGenerator.generate_grid(**params)
        elif gen_type == 'corridor':
            data = NetworkGenerator.generate_corridor(**params)
        elif gen_type == 'city':
            data = NetworkGenerator.generate_small_city(**params)
        else:
            return Response(
                {'error': f'不支持的路网类型: {gen_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        network = Network.objects.create(
            name=data['network']['name'],
            description=data['network']['description'],
            srid=data['network'].get('srid', 4326)
        )

        node_map = {}
        for nd in data['nodes']:
            node = Node.objects.create(
                network=network,
                node_id=nd['node_id'],
                name=nd.get('name', nd['node_id']),
                node_type=nd.get('node_type', 'intersection'),
                lng=nd.get('lng', 0),
                lat=nd.get('lat', 0),
                x=nd.get('x', 0),
                y=nd.get('y', 0)
            )
            node_map[nd['node_id']] = node

        edge_count = 0
        for ed in data.get('edges', []):
            from_node = node_map.get(ed['from_node'])
            to_node = node_map.get(ed['to_node'])
            if from_node and to_node:
                Edge.objects.create(
                    network=network,
                    edge_id=ed.get('edge_id', f"E_{ed['from_node']}_{ed['to_node']}"),
                    name=ed.get('name', ''),
                    from_node=from_node,
                    to_node=to_node,
                    length=ed.get('length', 500),
                    speed_limit=ed.get('speed_limit', 50),
                    lanes_count=ed.get('lanes_count', 2),
                    capacity=ed.get('capacity', 1800),
                    road_class=ed.get('road_class', 'arterial'),
                    is_oneway=ed.get('is_oneway', False)
                )
                edge_count += 1

        signal_count = 0
        for sd in data.get('signals', []):
            node = node_map.get(sd['node_id'])
            if node:
                signal = Signal.objects.create(
                    node=node,
                    signal_id=sd.get('signal_id', f"SIG_{sd['node_id']}"),
                    cycle_length=sd.get('cycle_length', 120),
                    offset=sd.get('offset', 0)
                )
                for i, ph in enumerate(sd.get('phases', [])):
                    Phase.objects.create(
                        signal=signal,
                        phase_index=i,
                        green_time=ph.get('green', 30),
                        yellow_time=ph.get('yellow', 3),
                        all_red_time=ph.get('all_red', 1)
                    )
                signal_count += 1

        return Response({
            'network_id': network.id,
            'name': network.name,
            'nodes_created': len(data['nodes']),
            'edges_created': edge_count,
            'signals_created': signal_count
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """克隆路网"""
        original = self.get_object()
        new_name = request.data.get('name', f"{original.name} (副本)")

        new_network = Network.objects.create(
            name=new_name,
            description=original.description,
            srid=original.srid
        )

        node_id_map = {}
        for node in original.nodes.all():
            new_node = Node.objects.create(
                network=new_network,
                node_id=node.node_id,
                name=node.name,
                node_type=node.node_type,
                lng=node.lng,
                lat=node.lat,
                x=node.x,
                y=node.y,
                z=node.z
            )
            node_id_map[node.id] = new_node

            if hasattr(node, 'intersection'):
                Intersection.objects.create(
                    node=new_node,
                    intersection_type=node.intersection.intersection_type,
                    channelization=node.intersection.channelization,
                    control_type=node.intersection.control_type
                )
            if hasattr(node, 'roundabout'):
                Roundabout.objects.create(
                    node=new_node,
                    radius=node.roundabout.radius,
                    lanes_count=node.roundabout.lanes_count
                )

        for edge in original.edges.all():
            new_from = node_id_map.get(edge.from_node_id)
            new_to = node_id_map.get(edge.to_node_id)
            if new_from and new_to:
                Edge.objects.create(
                    network=new_network,
                    edge_id=edge.edge_id,
                    name=edge.name,
                    from_node=new_from,
                    to_node=new_to,
                    length=edge.length,
                    speed_limit=edge.speed_limit,
                    lanes_count=edge.lanes_count,
                    capacity=edge.capacity,
                    road_class=edge.road_class,
                    is_oneway=edge.is_oneway
                )

        for node in original.nodes.filter(signal__isnull=False):
            signal = node.signal
            new_node = node_id_map.get(node.id)
            if new_node:
                new_signal = Signal.objects.create(
                    node=new_node,
                    signal_id=signal.signal_id,
                    cycle_length=signal.cycle_length,
                    offset=signal.offset,
                    control_mode=signal.control_mode,
                    is_coordinated=signal.is_coordinated
                )
                for phase in signal.phases.all():
                    Phase.objects.create(
                        signal=new_signal,
                        phase_index=phase.phase_index,
                        green_time=phase.green_time,
                        yellow_time=phase.yellow_time,
                        all_red_time=phase.all_red_time,
                        phase_type=phase.phase_type,
                        allowed_movements=phase.allowed_movements
                    )

        return Response({
            'message': '路网克隆成功',
            'new_network_id': new_network.id,
            'new_network_name': new_network.name
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def import_network(self, request, pk=None):
        """导入路网数据 (支持JSON格式)"""
        network = self.get_object()
        data = request.data

        nodes_data = data.get('nodes', [])
        edges_data = data.get('edges', [])
        signals_data = data.get('signals', [])

        node_map = {}
        for nd in nodes_data:
            node, _ = Node.objects.update_or_create(
                network=network,
                node_id=nd['node_id'],
                defaults={
                    'name': nd.get('name', nd['node_id']),
                    'node_type': nd.get('node_type', 'intersection'),
                    'lng': nd.get('lng', 0),
                    'lat': nd.get('lat', 0),
                    'x': nd.get('x', 0),
                    'y': nd.get('y', 0),
                }
            )
            node_map[nd['node_id']] = node

        for ed in edges_data:
            from_node = node_map.get(ed['from_node'])
            to_node = node_map.get(ed['to_node'])
            if from_node and to_node:
                Edge.objects.update_or_create(
                    network=network,
                    edge_id=ed.get('edge_id', f"{ed['from_node']}_{ed['to_node']}"),
                    defaults={
                        'from_node': from_node,
                        'to_node': to_node,
                        'length': ed.get('length', 500),
                        'speed_limit': ed.get('speed_limit', 50),
                        'lanes_count': ed.get('lanes_count', 2),
                        'capacity': ed.get('capacity', 1800),
                    }
                )

        for sd in signals_data:
            node = node_map.get(sd['node_id'])
            if node:
                signal, _ = Signal.objects.update_or_create(
                    node=node,
                    defaults={
                        'signal_id': sd.get('signal_id', f"SIG_{sd['node_id']}"),
                        'cycle_length': sd.get('cycle_length', 120),
                        'offset': sd.get('offset', 0),
                    }
                )
                Phase.objects.filter(signal=signal).delete()
                for i, ph in enumerate(sd.get('phases', [])):
                    Phase.objects.create(
                        signal=signal,
                        phase_index=i,
                        green_time=ph.get('green', 30),
                        yellow_time=ph.get('yellow', 3),
                        all_red_time=ph.get('all_red', 1),
                    )

        return Response({
            'message': '导入成功',
            'nodes_imported': len(nodes_data),
            'edges_imported': len(edges_data),
            'signals_imported': len(signals_data)
        })

    @action(detail=True, methods=['post'])
    def export_network(self, request, pk=None):
        """导出路网数据"""
        network = self.get_object()
        export_format = request.data.get('format', 'json')

        nodes_data = []
        for node in network.nodes.all():
            nd = {
                'node_id': node.node_id,
                'name': node.name,
                'node_type': node.node_type,
                'lng': node.lng,
                'lat': node.lat,
                'x': node.x,
                'y': node.y,
            }
            if hasattr(node, 'signal'):
                signal = node.signal
                nd['signal'] = {
                    'signal_id': signal.signal_id,
                    'cycle_length': signal.cycle_length,
                    'offset': signal.offset,
                    'phases': [
                        {
                            'green': p.green_time,
                            'yellow': p.yellow_time,
                            'all_red': p.all_red_time,
                        }
                        for p in signal.phases.all().order_by('phase_index')
                    ]
                }
            nodes_data.append(nd)

        edges_data = []
        for edge in network.edges.all():
            edges_data.append({
                'edge_id': edge.edge_id,
                'name': edge.name,
                'from_node': edge.from_node.node_id,
                'to_node': edge.to_node.node_id,
                'length': edge.length,
                'speed_limit': edge.speed_limit,
                'lanes_count': edge.lanes_count,
                'capacity': edge.capacity,
                'road_class': edge.road_class,
                'is_oneway': edge.is_oneway,
            })

        export_data = {
            'network': {
                'name': network.name,
                'description': network.description,
                'srid': network.srid,
            },
            'nodes': nodes_data,
            'edges': edges_data,
        }

        return Response(export_data)

    @action(detail=False, methods=['post'])
    def from_bbox(self, request):
        """从地图框选区域导入OSM路网 + 自动渠化"""
        from .osm_importer import import_to_db
        from .auto_channelize import channelize_network

        bbox = request.data.get('bbox')
        name = request.data.get('name', 'OSM导入路网')

        if not bbox or not all(k in bbox for k in ('south', 'west', 'north', 'east')):
            return Response({'error': '需要bbox参数: {south, west, north, east}'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            network, stats = import_to_db(bbox, name)
            # 自动渠化
            channelize_result = channelize_network(network)
            stats['channelize'] = channelize_result
            return Response(stats, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def auto_channelize(self, request, pk=None):
        """对已有路网自动渠化"""
        from .auto_channelize import channelize_network

        network = self.get_object()
        result = channelize_network(network)
        return Response(result)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """查询历史快照"""
        from .history import get_snapshots

        network = self.get_object()
        date = request.query_params.get('date')
        from_time = request.query_params.get('from')
        to_time = request.query_params.get('to')
        source = request.query_params.get('source')
        limit = int(request.query_params.get('limit', 3600))

        snapshots = get_snapshots(network, date, from_time, to_time, source, limit)
        data = list(snapshots.values('sim_time', 'timestamp', 'source', 'metrics'))
        return Response(data)

    @action(detail=True, methods=['get'])
    def history_at(self, request, pk=None):
        """查询指定时刻的快照"""
        from .history import get_snapshot_at

        network = self.get_object()
        time_str = request.query_params.get('time')
        if not time_str:
            return Response({'error': '需要time参数'}, status=status.HTTP_400_BAD_REQUEST)

        snapshot = get_snapshot_at(network, time_str)
        if not snapshot:
            return Response({'error': '未找到该时刻的数据'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'sim_time': snapshot.sim_time,
            'timestamp': snapshot.timestamp,
            'vehicles': snapshot.vehicles,
            'signals': snapshot.signals,
            'metrics': snapshot.metrics,
            'intersection_metrics': snapshot.intersection_metrics,
        })

    @action(detail=True, methods=['get'])
    def history_intersection(self, request, pk=None):
        """查询某个交叉口的历史指标"""
        from .history import get_intersection_history

        network = self.get_object()
        node_id = request.query_params.get('node_id')
        date = request.query_params.get('date')

        if not node_id or not date:
            return Response({'error': '需要node_id和date参数'}, status=status.HTTP_400_BAD_REQUEST)

        data = get_intersection_history(network, node_id, date)
        return Response(data)

    @action(detail=True, methods=['get'])
    def history_dates(self, request, pk=None):
        """获取有历史数据的日期列表"""
        from .history import get_available_dates

        network = self.get_object()
        dates = get_available_dates(network)
        return Response(dates)


class NodeViewSet(viewsets.ModelViewSet):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer
    filterset_fields = ['network', 'node_type']


class IntersectionViewSet(viewsets.ModelViewSet):
    queryset = Intersection.objects.all()
    serializer_class = IntersectionSerializer

    @action(detail=True, methods=['get'])
    def full_detail(self, request, pk=None):
        """获取交叉口完整数据: 车道+连接+信号+相位+映射"""
        intersection = self.get_object()
        node = intersection.node

        try:
            signal = Signal.objects.get(node=node)
            phases = []
            for phase in signal.phases.all().order_by('phase_index'):
                phase_lanes = []
                for pl in phase.phase_lanes.select_related('lane__edge').all():
                    phase_lanes.append({
                        'lane_id': pl.lane.id,
                        'lane_index': pl.lane.lane_index,
                        'lane_type': pl.lane.lane_type,
                        'edge_id': pl.lane.edge.edge_id,
                        'signal_display': pl.lane.signal_display,
                    })
                phases.append({
                    'id': phase.id,
                    'index': phase.phase_index,
                    'green': phase.green_time,
                    'yellow': phase.yellow_time,
                    'all_red': phase.all_red_time,
                    'phase_type': phase.phase_type,
                    'light_type': phase.light_type,
                    'protected_movements': phase.protected_movements,
                    'permissive_movements': phase.permissive_movements,
                    'phase_lanes': phase_lanes,
                })
            signal_data = {
                'id': signal.id,
                'cycle_length': signal.cycle_length,
                'offset': signal.offset,
                'control_mode': signal.control_mode,
                'phases': phases,
            }
        except Signal.DoesNotExist:
            signal_data = None

        # 进口道车道
        incoming = Edge.objects.filter(to_node=node, network=node.network)
        approaches = {}
        for edge in incoming:
            dx = node.x - edge.from_node.x
            dy = node.y - edge.from_node.y
            if abs(dy) >= abs(dx):
                direction = 'north' if dy > 0 else 'south'
            else:
                direction = 'east' if dx > 0 else 'west'

            lanes = []
            for lane in Lane.objects.filter(edge=edge).order_by('lane_index'):
                connections = []
                for conn in lane.outgoing_connections.all():
                    connections.append({
                        'to_edge': conn.to_lane.edge.edge_id,
                        'to_lane_index': conn.to_lane.lane_index,
                        'type': conn.connection_type,
                    })
                lanes.append({
                    'id': lane.id,
                    'index': lane.lane_index,
                    'type': lane.lane_type,
                    'width': lane.width,
                    'signal_display': lane.signal_display,
                    'is_exclusive': lane.is_exclusive,
                    'connections': connections,
                })

            approaches[direction] = {
                'edge_id': edge.edge_id,
                'road_class': edge.road_class,
                'lanes_count': edge.lanes_count,
                'length': edge.length,
                'speed_limit': edge.speed_limit,
                'lanes': lanes,
            }

        return Response({
            'node_id': node.node_id,
            'name': node.name,
            'lng': node.lng,
            'lat': node.lat,
            'x': node.x,
            'y': node.y,
            'intersection_type': intersection.intersection_type,
            'control_type': intersection.control_type,
            'signal': signal_data,
            'approaches': approaches,
        })

    @action(detail=True, methods=['post'])
    def update_channelization(self, request, pk=None):
        """更新渠化方案, 自动重建相位"""
        from .auto_channelize import rebuild_phases_on_lane_change

        intersection = self.get_object()
        result = rebuild_phases_on_lane_change(intersection)
        return Response(result)

    @action(detail=True, methods=['post'])
    def micro_sim(self, request, pk=None):
        """单交叉口微观仿真"""
        from .micro_sim import IntersectionMicroSim, build_intersection_data_from_db

        intersection = self.get_object()
        duration = int(request.data.get('duration', 300))

        data = build_intersection_data_from_db(intersection)

        # 允许前端覆盖流量参数
        flow_overrides = request.data.get('approaches', {})
        for direction, override in flow_overrides.items():
            if direction in data.get('approaches', {}):
                data['approaches'][direction]['flow'] = override.get('flow', data['approaches'][direction]['flow'])

        sim = IntersectionMicroSim(data, {'duration': duration, 'step_size': 1.0})

        snapshots = []
        for _ in range(duration):
            state = sim.step()
            if _ % 5 == 0:  # 每5秒存一个快照
                snapshots.append(state)

        return Response({
            'results': sim.get_results(),
            'snapshots': snapshots,
        })


class RoundaboutViewSet(viewsets.ModelViewSet):
    queryset = Roundabout.objects.all()
    serializer_class = RoundaboutSerializer


class EdgeViewSet(viewsets.ModelViewSet):
    queryset = Edge.objects.all()
    serializer_class = EdgeSerializer
    filterset_fields = ['network', 'from_node', 'to_node', 'road_class']


class LaneViewSet(viewsets.ModelViewSet):
    queryset = Lane.objects.all()
    serializer_class = LaneSerializer
    filterset_fields = ['edge', 'lane_type']


class LaneConnectionViewSet(viewsets.ModelViewSet):
    queryset = LaneConnection.objects.all()
    serializer_class = LaneConnectionSerializer


class SignalViewSet(viewsets.ModelViewSet):
    queryset = Signal.objects.all()
    serializer_class = SignalSerializer


class PhaseViewSet(viewsets.ModelViewSet):
    queryset = Phase.objects.all()
    serializer_class = PhaseSerializer


class PhaseLaneViewSet(viewsets.ModelViewSet):
    queryset = PhaseLane.objects.all()
    serializer_class = PhaseLaneSerializer


class TrafficDemandViewSet(viewsets.ModelViewSet):
    queryset = TrafficDemand.objects.all()
    serializer_class = TrafficDemandSerializer
    filterset_fields = ['network', 'demand_type']


class ODMatrixViewSet(viewsets.ModelViewSet):
    queryset = ODMatrix.objects.all()
    serializer_class = ODMatrixSerializer
