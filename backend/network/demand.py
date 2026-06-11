"""
交通流量生成器
支持: 时段模式、随机扰动、OD矩阵、检测器数据模拟
用于为仿真和优化提供输入数据
"""

import math
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class DemandGenerator:
    """交通需求生成器"""

    # 典型日小时流量分布系数 (24小时)
    HOURLY_PROFILES = {
        'weekday': [
            0.05, 0.03, 0.02, 0.02, 0.03, 0.08,  # 0-5
            0.25, 0.65, 1.00, 0.80, 0.60, 0.55,   # 6-11
            0.60, 0.55, 0.50, 0.55, 0.70, 0.90,   # 12-17
            0.85, 0.60, 0.40, 0.25, 0.15, 0.08    # 18-23
        ],
        'weekend': [
            0.05, 0.03, 0.02, 0.02, 0.02, 0.03,
            0.08, 0.15, 0.30, 0.50, 0.70, 0.80,
            0.85, 0.80, 0.75, 0.70, 0.65, 0.60,
            0.55, 0.50, 0.40, 0.30, 0.20, 0.10
        ],
        'peak': [
            0.10, 0.05, 0.03, 0.03, 0.05, 0.15,
            0.40, 0.80, 1.00, 0.70, 0.50, 0.45,
            0.50, 0.45, 0.40, 0.45, 0.60, 0.85,
            0.90, 0.65, 0.45, 0.30, 0.20, 0.12
        ]
    }

    @staticmethod
    def generate_edge_flows(
        edges: List[Dict],
        base_flow: float = 800,
        profile: str = 'weekday',
        variation: float = 0.15,
        peak_direction: str = 'ew',
        peak_factor: float = 1.5
    ) -> List[Dict]:
        """
        为路段生成流量数据

        Args:
            edges: 路段列表
            base_flow: 基础流量 (辆/小时)
            profile: 时段模式 'weekday'/'weekend'/'peak'
            variation: 随机扰动比例
            peak_direction: 高峰主方向 'ew'/'ns'
            peak_factor: 主方向高峰倍率

        Returns:
            带流量的路段数据列表
        """
        hourly = DemandGenerator.HOURLY_PROFILES.get(profile, DemandGenerator.HOURLY_PROFILES['weekday'])
        result = []

        for edge in edges:
            road_class = edge.get('road_class', 'arterial')
            lanes = edge.get('lanes_count', 2)

            class_factor = {
                'expressway': 2.0,
                'arterial': 1.0,
                'collector': 0.6,
                'local': 0.3
            }.get(road_class, 1.0)

            lane_factor = min(lanes / 2, 1.5)

            from_node = edge.get('from_node', '')
            to_node = edge.get('to_node', '')
            is_main_dir = (peak_direction in ['ew', 'we'] and ('_0' in from_node or '_1' in to_node)) or \
                          (peak_direction in ['ns', 'sn'] and ('0_' in from_node or '1_' in to_node))
            dir_factor = peak_factor if is_main_dir else (1.0 / peak_factor)

            flow_data = {
                **edge,
                'base_flow': base_flow * class_factor * lane_factor * dir_factor,
                'hourly_profile': hourly,
                'flow': int(base_flow * class_factor * lane_factor * dir_factor * hourly[8] *
                            random.uniform(1 - variation, 1 + variation))
            }
            result.append(flow_data)

        return result

    @staticmethod
    def generate_od_matrix(
        node_ids: List[str],
        total_demand: float = 5000,
        gravity_factor: float = 2.0,
        distance_matrix: Optional[Dict] = None
    ) -> List[Dict]:
        """
        生成OD矩阵 (重力模型)

        Args:
            node_ids: 节点ID列表
            total_demand: 总需求量 (辆/小时)
            gravity_factor: 重力模型指数
            distance_matrix: 距离矩阵 {from_to: distance}

        Returns:
            OD对列表 [{from_node, to_node, flow}]
        """
        n = len(node_ids)
        od_pairs = []

        attractiveness = {nid: random.uniform(0.5, 2.0) for nid in node_ids}

        total_weight = 0
        weights = {}
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                fi, ti = node_ids[i], node_ids[j]
                dist_key = f"{fi}_{ti}"
                if distance_matrix and dist_key in distance_matrix:
                    dist = distance_matrix[dist_key]
                else:
                    dist = abs(i - j) * 500 + 200

                weight = (attractiveness[fi] * attractiveness[ti]) / (dist ** gravity_factor) * 1e6
                weights[(fi, ti)] = weight
                total_weight += weight

        if total_weight == 0:
            return od_pairs

        for (fi, ti), weight in weights.items():
            flow = total_demand * (weight / total_weight)
            if flow > 0.5:
                od_pairs.append({
                    'from_node': fi,
                    'to_node': ti,
                    'flow': round(flow, 1)
                })

        return od_pairs

    @staticmethod
    def generate_detector_data(
        edge_id: str,
        duration_hours: float = 1.0,
        interval_seconds: int = 300,
        base_flow: float = 800,
        profile: str = 'weekday',
        noise_level: float = 0.1
    ) -> List[Dict]:
        """
        模拟检测器数据输出

        Args:
            edge_id: 路段ID
            duration_hours: 持续时长 (小时)
            interval_seconds: 检测间隔 (秒)
            base_flow: 基础流量
            profile: 时段模式
            noise_level: 噪声水平

        Returns:
            检测器记录列表
        """
        hourly = DemandGenerator.HOURLY_PROFILES.get(profile, DemandGenerator.HOURLY_PROFILES['weekday'])
        intervals_per_hour = 3600 / interval_seconds
        total_intervals = int(duration_hours * intervals_per_hour)

        records = []
        current_time = datetime(2024, 1, 15, 7, 0, 0)

        for i in range(total_intervals):
            hour = current_time.hour + current_time.minute / 60
            hour_idx = int(hour) % 24
            hour_factor = hourly[hour_idx]

            next_idx = (hour_idx + 1) % 24
            frac = hour - int(hour)
            interpolated = hourly[hour_idx] * (1 - frac) + hourly[next_idx] * frac

            flow = base_flow * interpolated / (3600 / interval_seconds)
            flow = max(0, flow * random.gauss(1.0, noise_level))

            speed = random.gauss(45, 5)
            occupancy = min(100, max(0, flow * 2.5 + random.gauss(0, 3)))

            records.append({
                'edge_id': edge_id,
                'timestamp': current_time.isoformat(),
                'interval': interval_seconds,
                'flow': round(flow, 1),
                'speed': round(speed, 1),
                'occupancy': round(occupancy, 1),
                'queue_length': max(0, round(flow * 0.02 + random.gauss(0, 1), 1))
            })

            current_time += timedelta(seconds=interval_seconds)

        return records

    @staticmethod
    def generate_time_of_day_signal_plan(
        cycle_base: int = 120,
        time_periods: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        生成时段信号配时方案 (TOD)

        Args:
            cycle_base: 基础周期
            time_periods: 时段配置 [{start_hour, end_hour, flow_ratio}]

        Returns:
            各时段配时方案
        """
        if time_periods is None:
            time_periods = [
                {'start_hour': 0, 'end_hour': 6, 'flow_ratio': 0.2, 'name': '夜间'},
                {'start_hour': 6, 'end_hour': 9, 'flow_ratio': 0.8, 'name': '早高峰'},
                {'start_hour': 9, 'end_hour': 12, 'flow_ratio': 0.5, 'name': '上午平峰'},
                {'start_hour': 12, 'end_hour': 14, 'flow_ratio': 0.6, 'name': '午间'},
                {'start_hour': 14, 'end_hour': 17, 'flow_ratio': 0.5, 'name': '下午平峰'},
                {'start_hour': 17, 'end_hour': 19, 'flow_ratio': 0.9, 'name': '晚高峰'},
                {'start_hour': 19, 'end_hour': 22, 'flow_ratio': 0.4, 'name': '晚间'},
                {'start_hour': 22, 'end_hour': 24, 'flow_ratio': 0.15, 'name': '深夜'}
            ]

        plans = []
        for period in time_periods:
            ratio = period['flow_ratio']
            cycle = max(60, min(180, int(cycle_base * (0.6 + 0.8 * ratio))))

            main_green = int(cycle * (0.45 + 0.2 * ratio))
            cross_green = cycle - main_green - 8

            plans.append({
                'name': period['name'],
                'start_hour': period['start_hour'],
                'end_hour': period['end_hour'],
                'cycle_length': cycle,
                'phases': [
                    {'green': main_green, 'yellow': 3, 'all_red': 1},
                    {'green': cross_green, 'yellow': 3, 'all_red': 1}
                ]
            })

        return plans
