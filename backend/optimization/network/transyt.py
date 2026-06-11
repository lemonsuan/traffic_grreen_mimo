"""
TRANSYT 区域信号优化算法
算法原理: Robertson, 1969
基于车队离散模型的网络配时优化
核心: 循环流量分布图(CFP) + 爬山法优化
"""

import time
import random
import math
from typing import Dict, List

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


class TRANSYTOptimizer(BaseOptimizer):
    """TRANSYT 区域信号优化器"""

    def get_algorithm_name(self) -> str:
        return 'transyt'

    def validate_inputs(self) -> bool:
        if not self.context.node_ids:
            return False
        if 'network_data' not in self.context.traffic_data:
            return False
        return True

    def optimize(self) -> OptimizationResult:
        start_time = time.time()

        network_data = self.context.traffic_data.get('network_data', {})
        nodes = self.context.node_ids

        cycle = self._get_common_cycle(network_data)
        convergence = []

        # 初始化配时方案
        best_timing = self._initialize_timing(nodes, network_data, cycle)
        best_perf = self._evaluate_network(best_timing, network_data, nodes)
        best_cost = self._performance_cost(best_perf)

        # 爬山法优化 (带随机重启)
        max_iterations = self.context.params.get('iterations', 200)
        restart_count = self.context.params.get('restarts', 5)
        step_size = self.context.params.get('step_size', 5)

        for restart in range(restart_count):
            if restart > 0:
                current_timing = self._random_timing(nodes, network_data, cycle)
            else:
                current_timing = {k: self._copy_timing(v) for k, v in best_timing.items()}

            current_perf = self._evaluate_network(current_timing, network_data, nodes)
            current_cost = self._performance_cost(current_perf)

            for it in range(max_iterations // restart_count):
                # 生成邻域解
                neighbor = self._neighbor(current_timing, nodes, cycle, step_size)
                neighbor_perf = self._evaluate_network(neighbor, network_data, nodes)
                neighbor_cost = self._performance_cost(neighbor_perf)

                if neighbor_cost < current_cost:
                    current_timing = neighbor
                    current_cost = neighbor_cost
                    current_perf = neighbor_perf

                    if current_cost < best_cost:
                        best_timing = {k: self._copy_timing(v) for k, v in current_timing.items()}
                        best_cost = current_cost
                        best_perf = current_perf

                convergence.append(best_cost)

        computation_time = time.time() - start_time

        return OptimizationResult(
            level=OptimizationLevel.NETWORK,
            algorithm=self.get_algorithm_name(),
            signal_timings=best_timing,
            performance=best_perf,
            convergence=convergence,
            computation_time=computation_time
        )

    def _get_common_cycle(self, network_data):
        cycles = []
        for node_data in network_data.get('nodes', {}).values():
            if 'cycle_length' in node_data:
                cycles.append(node_data['cycle_length'])
        return max(cycles) if cycles else self.constraints.max_cycle_length

    def _initialize_timing(self, nodes, network_data, cycle):
        signal_timings = {}
        for node_id in nodes:
            node_data = network_data.get('nodes', {}).get(node_id, {})
            node_cycle = node_data.get('cycle_length', cycle)
            green_ns = node_data.get('green_ns', 40)
            green_ew = node_data.get('green_ew', 35)
            offset = node_data.get('offset', 0)

            phases = [
                {'index': 0, 'name': 'NS_through', 'green': green_ns,
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time},
                {'index': 1, 'name': 'EW_through', 'green': green_ew,
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time}
            ]
            signal_timings[node_id] = SignalTiming(
                cycle_length=node_cycle, offset=offset, phases=phases
            )
        return signal_timings

    def _random_timing(self, nodes, network_data, cycle):
        signal_timings = {}
        for node_id in nodes:
            node_data = network_data.get('nodes', {}).get(node_id, {})
            node_cycle = node_data.get('cycle_length', cycle)
            total_loss = 2 * (self.constraints.yellow_time + self.constraints.all_red_time)
            effective = node_cycle - total_loss

            green_ns = random.uniform(self.constraints.min_green_time, effective - self.constraints.min_green_time)
            green_ew = effective - green_ns

            phases = [
                {'index': 0, 'name': 'NS_through', 'green': round(green_ns, 1),
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time},
                {'index': 1, 'name': 'EW_through', 'green': round(green_ew, 1),
                 'yellow': self.constraints.yellow_time, 'all_red': self.constraints.all_red_time}
            ]
            signal_timings[node_id] = SignalTiming(
                cycle_length=node_cycle, offset=random.uniform(0, node_cycle), phases=phases
            )
        return signal_timings

    def _copy_timing(self, timing):
        return SignalTiming(
            cycle_length=timing.cycle_length,
            offset=timing.offset,
            phases=[dict(p) for p in timing.phases]
        )

    def _neighbor(self, timing, nodes, cycle, step):
        """生成邻域: 随机选一个路口，调整偏移或绿灯分配"""
        new_timing = {k: self._copy_timing(v) for k, v in timing.items()}
        node = random.choice(nodes)
        t = new_timing[node]

        op = random.choice(['offset', 'green', 'both'])

        if op == 'offset':
            t.offset = (t.offset + random.uniform(-step, step)) % t.cycle_length
        elif op == 'green':
            total_loss = sum(p['yellow'] + p['all_red'] for p in t.phases)
            effective = t.cycle_length - total_loss
            delta = random.uniform(-step, step)
            new_ns = max(self.constraints.min_green_time,
                         min(effective - self.constraints.min_green_time, t.phases[0]['green'] + delta))
            t.phases[0]['green'] = round(new_ns, 1)
            t.phases[1]['green'] = round(effective - new_ns, 1)
        else:
            t.offset = (t.offset + random.uniform(-step, step)) % t.cycle_length
            total_loss = sum(p['yellow'] + p['all_red'] for p in t.phases)
            effective = t.cycle_length - total_loss
            delta = random.uniform(-step, step)
            new_ns = max(self.constraints.min_green_time,
                         min(effective - self.constraints.min_green_time, t.phases[0]['green'] + delta))
            t.phases[0]['green'] = round(new_ns, 1)
            t.phases[1]['green'] = round(effective - new_ns, 1)

        return new_timing

    def _evaluate_network(self, signal_timings, network_data, nodes):
        """
        TRANSYT 性能评估
        基于循环流量分布图(CFP)估算延误和停车
        """
        total_delay = 0
        total_stops = 0
        total_flow = 0

        edges = network_data.get('edges', [])
        for edge in edges:
            from_node = edge.get('from')
            to_node = edge.get('to')
            flow = edge.get('flow', 0)

            if from_node not in signal_timings or to_node not in signal_timings:
                continue

            t_from = signal_timings[from_node]
            t_to = signal_timings[to_node]

            travel_time = edge.get('travel_time', 30)
            cycle = t_from.cycle_length

            # 车队离散模型 (Robertson)
            beta = 0.35
            alpha = 0.5
            platoon_ratio = self._platoon_dispersion(
                t_from, t_to, travel_time, cycle, beta, alpha
            )

            # 根据到达绿灯比例计算延误
            green_to = t_to.phases[1]['green'] if len(t_to.phases) > 1 else t_to.phases[0]['green']
            g_c = green_to / cycle

            # 协调效果
            offset_diff = (t_to.offset - t_from.offset) % cycle
            arrival_green = max(0, 1 - abs(offset_diff - travel_time % cycle) / green_to) if green_to > 0 else 0

            # Webster 延误
            sat_flow = 1800
            x = flow / (sat_flow * g_c) if g_c > 0 else 1
            if x < 1 and x > 0:
                d1 = (0.5 * cycle * (1 - g_c) ** 2) / (1 - min(1, x) * g_c)
            else:
                d1 = 0.5 * cycle * (1 - g_c) if g_c < 1 else 0

            # 协调延误修正
            d1_adjusted = d1 * (1 - arrival_green * 0.6)

            delay = d1_adjusted * flow
            stops = flow * (1 - g_c) * (1 - arrival_green * 0.5) / cycle * 3600

            total_delay += delay
            total_stops += stops
            total_flow += flow

        avg_delay = total_delay / total_flow if total_flow > 0 else 0
        avg_stops = total_stops / total_flow if total_flow > 0 else 0

        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_delay * 0.25, 2),
            max_queue_length=int(avg_delay * 0.4),
            throughput=int(total_flow * 0.85),
            avg_stops=round(avg_stops, 2),
            vcr=round(sum(
                e.get('flow', 0) / 1800 for e in edges
            ) / max(len(edges), 1), 2)
        )

    def _platoon_dispersion(self, t_from, t_to, travel_time, cycle, beta, alpha):
        """
        Robertson 车队离散模型
        返回到达绿灯比例
        """
        offset_diff = (t_to.offset - t_from.offset) % cycle
        ideal_arrival = travel_time % cycle
        dispersion_error = abs(offset_diff - ideal_arrival)

        if dispersion_error > cycle / 2:
            dispersion_error = cycle - dispersion_error

        ratio = max(0, 1 - dispersion_error / (cycle * beta))
        return ratio

    def _performance_cost(self, perf):
        return perf.avg_delay * 0.6 + perf.avg_stops * 20 + perf.vcr * 30


from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('network', 'transyt', TRANSYTOptimizer)
