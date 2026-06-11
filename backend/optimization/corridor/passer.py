"""
PASSER-II 干线绿波优化算法
算法原理: Chang & Messer, 1984
基于各流向带宽加权和最大化
相比MAXBAND: 区分左转专用相位、考虑多流向带宽
"""

import time
import numpy as np
from typing import Dict, List, Optional
from scipy.optimize import linprog

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


class PASSEROptimizer(BaseOptimizer):
    """PASSER-II 绿波优化器"""

    def get_algorithm_name(self) -> str:
        return 'passer'

    def validate_inputs(self) -> bool:
        if len(self.context.node_ids) < 2:
            return False
        if 'corridor_data' not in self.context.traffic_data:
            return False
        return True

    def optimize(self) -> OptimizationResult:
        start_time = time.time()

        corridor_data = self.context.traffic_data.get('corridor_data', {})
        nodes = self.context.node_ids
        desired_speed = self.context.params.get('desired_speed', 40)
        desired_speed_ms = desired_speed / 3.6

        travel_times = self._calculate_travel_times(nodes, corridor_data, desired_speed_ms)
        result = self._solve_passer(nodes, travel_times, corridor_data)

        if result is None:
            return self._fallback_solution(nodes, corridor_data)

        offsets, bandwidths = result
        signal_timings = self._generate_signal_timings(nodes, offsets, corridor_data)
        performance = self._estimate_performance(signal_timings, corridor_data, bandwidths)

        computation_time = time.time() - start_time

        return OptimizationResult(
            level=OptimizationLevel.CORRIDOR,
            algorithm=self.get_algorithm_name(),
            signal_timings=signal_timings,
            performance=performance,
            computation_time=computation_time
        )

    def _calculate_travel_times(
        self, nodes: List[str], corridor_data: Dict, speed_ms: float
    ) -> List[float]:
        travel_times = []
        for i in range(len(nodes) - 1):
            edge_key = f"{nodes[i]}_{nodes[i+1]}"
            edge_data = corridor_data.get('edges', {}).get(edge_key, {})
            length = edge_data.get('length', 500)
            travel_times.append(length / speed_ms)
        return travel_times

    def _solve_passer(
        self, nodes: List[str], travel_times: List[float], corridor_data: Dict
    ) -> Optional[tuple]:
        """
        PASSER-II 线性规划求解
        变量: 各路口偏移 + 正向/反向直行带宽 + 左转带宽
        """
        n = len(nodes)
        if n < 2:
            return None

        cycle = self._get_common_cycle(corridor_data)

        # 相位结构: 每个路口假设 4 相位 (NS直行, NS左转, EW直行, EW左转)
        # 偏移量指的是 EW 直行相位起始相对于参考时刻的偏移
        # 变量: [offset_0..offset_{n-1}, b_fwd, b_bwd, b_left_fwd, b_left_bwd]
        num_vars = n + 4

        # 各流向权重 (直行权重高于左转)
        w_through = self.context.params.get('w_through', 1.0)
        w_left = self.context.params.get('w_left', 0.5)

        # 目标: 最大化加权带宽和 => 最小化负值
        c = [0] * n + [-w_through, -w_through, -w_left, -w_left]

        A_ub = []
        b_ub = []

        # 偏移约束: 0 <= offset_i <= cycle
        for i in range(n):
            row = [0] * num_vars
            row[i] = -1
            A_ub.append(row)
            b_ub.append(0)

            row = [0] * num_vars
            row[i] = 1
            A_ub.append(row)
            b_ub.append(cycle)

        # 正向直行带宽约束
        for i in range(n - 1):
            tt = travel_times[i]
            # offset_{i+1} - offset_i + b_fwd <= tt
            row = [0] * num_vars
            row[i] = -1
            row[i + 1] = 1
            row[n] = 1
            A_ub.append(row)
            b_ub.append(tt)

        # 反向直行带宽约束
        for i in range(n - 1):
            tt = travel_times[i]
            # offset_i - offset_{i+1} + b_bwd <= -tt + cycle
            row = [0] * num_vars
            row[i] = 1
            row[i + 1] = -1
            row[n + 1] = 1
            A_ub.append(row)
            b_ub.append(-tt + cycle)

        # 左转带宽约束 (基于相位分割)
        left_phase_ratio = self.context.params.get('left_phase_ratio', 0.2)
        for i in range(n - 1):
            tt = travel_times[i]
            # 左转相位偏移 = 直行偏移 + 直行绿灯
            green_ns = corridor_data.get('nodes', {}).get(
                nodes[i], {}
            ).get('green_ns', 45)
            left_offset = green_ns * (1 - left_phase_ratio)

            row = [0] * num_vars
            row[i] = -1
            row[i + 1] = 1
            row[n + 2] = 1
            A_ub.append(row)
            b_ub.append(tt + left_offset)

            row = [0] * num_vars
            row[i] = 1
            row[i + 1] = -1
            row[n + 3] = 1
            A_ub.append(row)
            b_ub.append(-tt + cycle + left_offset)

        # 带宽非负
        for j in range(n, num_vars):
            row = [0] * num_vars
            row[j] = -1
            A_ub.append(row)
            b_ub.append(0)

        # 带宽上限
        max_bw = cycle * 0.4
        for j in range(n, num_vars):
            row = [0] * num_vars
            row[j] = 1
            A_ub.append(row)
            b_ub.append(max_bw)

        try:
            result = linprog(
                c, A_ub=A_ub, b_ub=b_ub,
                bounds=[(0, cycle)] * n + [(0, max_bw)] * 4,
                method='highs'
            )
            if result.success:
                offsets = result.x[:n].tolist()
                bandwidths = {
                    'forward': result.x[n],
                    'backward': result.x[n + 1],
                    'left_forward': result.x[n + 2],
                    'left_backward': result.x[n + 3]
                }
                return offsets, bandwidths
        except Exception as e:
            print(f"PASSER-II 求解失败: {e}")

        return None

    def _get_common_cycle(self, corridor_data: Dict) -> float:
        cycles = []
        for node_data in corridor_data.get('nodes', {}).values():
            if 'cycle_length' in node_data:
                cycles.append(node_data['cycle_length'])
        return max(cycles) if cycles else self.constraints.max_cycle_length

    def _generate_signal_timings(
        self, nodes: List[str], offsets: List[float], corridor_data: Dict
    ) -> Dict[str, SignalTiming]:
        signal_timings = {}
        for i, node_id in enumerate(nodes):
            node_data = corridor_data.get('nodes', {}).get(node_id, {})
            cycle = node_data.get('cycle_length', 120)
            green_ns = node_data.get('green_ns', 45)
            green_ew = node_data.get('green_ew', 35)

            phases = [
                {'index': 0, 'name': 'NS_through', 'green': green_ns,
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time},
                {'index': 1, 'name': 'EW_through', 'green': green_ew,
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time}
            ]
            signal_timings[node_id] = SignalTiming(
                cycle_length=cycle, offset=offsets[i], phases=phases
            )
        return signal_timings

    def _estimate_performance(
        self, signal_timings: Dict[str, SignalTiming],
        corridor_data: Dict, bandwidths: Dict
    ) -> PerformanceMetrics:
        cycle = list(signal_timings.values())[0].cycle_length
        total_bw = sum(bandwidths.values())
        efficiency = total_bw / (4 * cycle)

        base_delay = 45
        avg_delay = base_delay * (1 - efficiency * 0.6)
        avg_stops = 2.5 * (1 - efficiency * 0.5)

        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_delay * 0.3, 2),
            max_queue_length=int(avg_delay * 0.5),
            throughput=int(2000 * (1 + efficiency * 0.3)),
            avg_stops=round(avg_stops, 2),
            vcr=round(0.7 + (1 - efficiency) * 0.2, 2)
        )

    def _fallback_solution(
        self, nodes: List[str], corridor_data: Dict
    ) -> OptimizationResult:
        signal_timings = {}
        for i, node_id in enumerate(nodes):
            node_data = corridor_data.get('nodes', {}).get(node_id, {})
            cycle = node_data.get('cycle_length', 120)
            signal_timings[node_id] = SignalTiming(
                cycle_length=cycle, offset=i * 15,
                phases=[
                    {'index': 0, 'green': 45, 'yellow': 3, 'all_red': 1},
                    {'index': 1, 'green': 35, 'yellow': 3, 'all_red': 1}
                ]
            )
        return OptimizationResult(
            level=OptimizationLevel.CORRIDOR,
            algorithm=self.get_algorithm_name(),
            signal_timings=signal_timings,
            performance=PerformanceMetrics(avg_delay=40, avg_stops=2.0),
            computation_time=0
        )


from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('corridor', 'passer', PASSEROptimizer)
