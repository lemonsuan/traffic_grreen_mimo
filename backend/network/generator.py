"""
路网自动生成器
支持: 网格路网、随机路网、自定义模板
用于快速创建测试用例和小型城市路网
"""

import math
import random
from typing import List, Dict, Tuple, Optional


class NetworkGenerator:
    """路网生成器基类"""

    @staticmethod
    def generate_grid(
        rows: int = 4,
        cols: int = 4,
        block_size: float = 300,
        speed_limit: float = 50,
        lanes: int = 2,
        base_lng: float = 116.4074,
        base_lat: float = 39.9042,
        offset_x: float = 0.003,
        offset_y: float = 0.002
    ) -> Dict:
        """
        生成网格状路网 (典型城市街区)

        Args:
            rows: 南北方向路口数
            cols: 东西方向路口数
            block_size: 相邻路口间距 (米)
            speed_limit: 默认限速 (km/h)
            lanes: 默认车道数
            base_lng: 基准经度
            base_lat: 基准纬度
            offset_x: 经度偏移 (≈1度≈111km, 0.003≈300m)
            offset_y: 纬度偏移

        Returns:
            路网数据字典 {nodes, edges, signals}
        """
        nodes = []
        edges = []
        signals = []

        for r in range(rows):
            for c in range(cols):
                node_id = f"N{r}_{c}"
                lng = base_lng + c * offset_x
                lat = base_lat + r * offset_y

                nodes.append({
                    'node_id': node_id,
                    'name': f'路口({r},{c})',
                    'node_type': 'intersection',
                    'lng': round(lng, 6),
                    'lat': round(lat, 6),
                    'x': c * block_size,
                    'y': r * block_size
                })

                cycle = 120
                green_ns = random.randint(35, 55)
                green_ew = cycle - green_ns - 8

                signals.append({
                    'node_id': node_id,
                    'signal_id': f'SIG_{node_id}',
                    'cycle_length': cycle,
                    'offset': 0,
                    'phases': [
                        {'green': green_ns, 'yellow': 3, 'all_red': 1},
                        {'green': green_ew, 'yellow': 3, 'all_red': 1}
                    ]
                })

        for r in range(rows):
            for c in range(cols):
                if c < cols - 1:
                    from_id = f"N{r}_{c}"
                    to_id = f"N{r}_{c+1}"
                    edges.append({
                        'edge_id': f"E_{from_id}_{to_id}",
                        'name': f'{from_id}→{to_id}',
                        'from_node': from_id,
                        'to_node': to_id,
                        'length': block_size,
                        'speed_limit': speed_limit,
                        'lanes_count': lanes,
                        'capacity': lanes * 900,
                        'road_class': 'arterial',
                        'is_oneway': False
                    })

                if r < rows - 1:
                    from_id = f"N{r}_{c}"
                    to_id = f"N{r+1}_{c}"
                    edges.append({
                        'edge_id': f"E_{from_id}_{to_id}",
                        'name': f'{from_id}→{to_id}',
                        'from_node': from_id,
                        'to_node': to_id,
                        'length': block_size,
                        'speed_limit': speed_limit,
                        'lanes_count': lanes,
                        'capacity': lanes * 900,
                        'road_class': 'arterial',
                        'is_oneway': False
                    })

        return {
            'network': {
                'name': f'{rows}×{cols}网格路网',
                'description': f'自动生成的{rows}行{cols}列网格路网，共{rows*cols}个路口',
                'srid': 4326
            },
            'nodes': nodes,
            'edges': edges,
            'signals': signals
        }

    @staticmethod
    def generate_corridor(
        num_intersections: int = 6,
        segment_length: float = 500,
        speed_limit: float = 50,
        lanes: int = 3,
        base_lng: float = 116.4074,
        base_lat: float = 39.9042,
        direction: str = 'ew',
        desired_speed: float = 40
    ) -> Dict:
        """
        生成干线走廊路网 (绿波优化测试)

        Args:
            num_intersections: 路口数量
            segment_length: 路段长度 (米)
            speed_limit: 限速 (km/h)
            lanes: 车道数
            direction: 方向 'ew'(东西) 或 'ns'(南北)
            desired_speed: 设计速度 (km/h)

        Returns:
            路网数据字典
        """
        nodes = []
        edges = []
        signals = []

        travel_time = segment_length / (desired_speed / 3.6)
        cycle = max(90, min(150, int(travel_time * num_intersections * 0.8)))

        for i in range(num_intersections):
            node_id = f"C{i}"
            if direction == 'ew':
                lng = base_lng + i * 0.005
                lat = base_lat
                x = i * segment_length
                y = 0
            else:
                lng = base_lng
                lat = base_lat + i * 0.003
                x = 0
                y = i * segment_length

            nodes.append({
                'node_id': node_id,
                'name': f'干线路口{i+1}',
                'node_type': 'intersection',
                'lng': round(lng, 6),
                'lat': round(lat, 6),
                'x': x,
                'y': y
            })

            base_offset = int(i * travel_time) % cycle
            green_main = int(cycle * 0.55)
            green_cross = cycle - green_main - 8

            signals.append({
                'node_id': node_id,
                'signal_id': f'SIG_{node_id}',
                'cycle_length': cycle,
                'offset': base_offset,
                'phases': [
                    {'green': green_main, 'yellow': 3, 'all_red': 1},
                    {'green': green_cross, 'yellow': 3, 'all_red': 1}
                ]
            })

        for i in range(num_intersections - 1):
            from_id = f"C{i}"
            to_id = f"C{i+1}"
            edges.append({
                'edge_id': f"E_{from_id}_{to_id}",
                'name': f'干线段{i+1}',
                'from_node': from_id,
                'to_node': to_id,
                'length': segment_length,
                'speed_limit': speed_limit,
                'lanes_count': lanes,
                'capacity': lanes * 900,
                'road_class': 'arterial',
                'is_oneway': False
            })

        return {
            'network': {
                'name': f'{num_intersections}路口干线走廊',
                'description': f'自动生成的干线绿波走廊，{num_intersections}个路口，间距{segment_length}m',
                'srid': 4326
            },
            'nodes': nodes,
            'edges': edges,
            'signals': signals
        }

    @staticmethod
    def generate_small_city(
        center_lng: float = 116.4074,
        center_lat: float = 39.9042
    ) -> Dict:
        """
        生成小型城市路网 (约20-30个路口)
        包含: 主干道、次干道、支路

        Returns:
            完整路网数据
        """
        nodes = []
        edges = []
        signals = []

        main_grid = NetworkGenerator._create_grid_segment(
            rows=3, cols=4,
            start_r=0, start_c=0,
            base_lng=center_lng - 0.006,
            base_lat=center_lat - 0.003,
            block_size=400,
            lanes=3,
            road_class='arterial',
            prefix='M'
        )
        nodes.extend(main_grid['nodes'])
        edges.extend(main_grid['edges'])
        signals.extend(main_grid['signals'])

        sub_grid = NetworkGenerator._create_grid_segment(
            rows=4, cols=3,
            start_r=0, start_c=0,
            base_lng=center_lng + 0.008,
            base_lat=center_lat - 0.004,
            block_size=250,
            lanes=2,
            road_class='collector',
            prefix='S'
        )
        nodes.extend(sub_grid['nodes'])
        edges.extend(sub_grid['edges'])
        signals.extend(sub_grid['signals'])

        bridge_edges = [
            {
                'edge_id': 'E_bridge_1',
                'name': '连接桥1',
                'from_node': 'M1_3',
                'to_node': 'S1_0',
                'length': 600,
                'speed_limit': 40,
                'lanes_count': 2,
                'capacity': 1800,
                'road_class': 'arterial',
                'is_oneway': False
            }
        ]
        edges.extend(bridge_edges)

        return {
            'network': {
                'name': '小型城市路网',
                'description': f'自动生成的小型城市路网，含主干道和次干道，共{len(nodes)}个路口',
                'srid': 4326
            },
            'nodes': nodes,
            'edges': edges,
            'signals': signals
        }

    @staticmethod
    def _create_grid_segment(
        rows, cols, start_r, start_c,
        base_lng, base_lat, block_size,
        lanes, road_class, prefix
    ) -> Dict:
        """创建网格子区域"""
        nodes = []
        edges = []
        signals = []

        lng_step = block_size / 111000
        lat_step = block_size / 111000

        for r in range(rows):
            for c in range(cols):
                node_id = f"{prefix}{r}_{c}"
                nodes.append({
                    'node_id': node_id,
                    'name': f'{prefix}区路口({r},{c})',
                    'node_type': 'intersection',
                    'lng': round(base_lng + c * lng_step, 6),
                    'lat': round(base_lat + r * lat_step, 6),
                    'x': c * block_size,
                    'y': r * block_size
                })

                cycle = 120 if road_class == 'arterial' else 90
                green_a = random.randint(30, 50)
                green_b = cycle - green_a - 8

                signals.append({
                    'node_id': node_id,
                    'signal_id': f'SIG_{node_id}',
                    'cycle_length': cycle,
                    'offset': 0,
                    'phases': [
                        {'green': green_a, 'yellow': 3, 'all_red': 1},
                        {'green': green_b, 'yellow': 3, 'all_red': 1}
                    ]
                })

        for r in range(rows):
            for c in range(cols):
                if c < cols - 1:
                    fid = f"{prefix}{r}_{c}"
                    tid = f"{prefix}{r}_{c+1}"
                    edges.append({
                        'edge_id': f"E_{fid}_{tid}",
                        'name': f'{fid}→{tid}',
                        'from_node': fid,
                        'to_node': tid,
                        'length': block_size,
                        'speed_limit': 50 if road_class == 'arterial' else 40,
                        'lanes_count': lanes,
                        'capacity': lanes * 900,
                        'road_class': road_class,
                        'is_oneway': False
                    })
                if r < rows - 1:
                    fid = f"{prefix}{r}_{c}"
                    tid = f"{prefix}{r+1}_{c}"
                    edges.append({
                        'edge_id': f"E_{fid}_{tid}",
                        'name': f'{fid}→{tid}',
                        'from_node': fid,
                        'to_node': tid,
                        'length': block_size,
                        'speed_limit': 50 if road_class == 'arterial' else 40,
                        'lanes_count': lanes,
                        'capacity': lanes * 900,
                        'road_class': road_class,
                        'is_oneway': False
                    })

        return {'nodes': nodes, 'edges': edges, 'signals': signals}
