"""
SCOOT 实时自适应区域信号控制算法
算法原理: Hunt et al., 1981
在线增量优化: 连续微调周期、绿信比和相位差
基于检测器数据实时反馈
"""

import time
import random
from typing import Dict, List

from ..base import (
    BaseOptimizer, OptimizationContext, OptimizationResult,
    SignalTiming, PerformanceMetrics, OptimizationLevel
)


class SCOOTOptimizer(BaseOptimizer):
    """SCOOT 自适应信号控制优化器"""

    def get_algorithm_name(self) -> str:
        return 'scoot'

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

        # SCOOT 参数
        cycle_step = self.context.params.get('cycle_step', 4)
        green_step = self.context.params.get('green_step', 2)
        offset_step = self.context.params.get('offset_step', 4)
        max_iterations = self.context.params.get('iterations', 150)

        convergence = []

        # 初始化配时方案
        current_timing = self._initialize_timing(nodes, network_data, cycle)
        current_perf = self._evaluate_performance(current_timing, network_data, nodes)
        current_cost = self._performance_cost(current_perf)

        best_timing = {k: self._copy_timing(v) for k, v in current_timing.items()}
        best_cost = current_cost
        best_perf = current_perf

        for iteration in range(max_iterations):
            # SCOOT 三阶段微调
            # 1. 周期优化: 全网统一调整
            current_timing, current_cost, current_perf = self._optimize_cycle(
                current_timing, current_cost, current_perf,
                network_data, nodes, cycle_step
            )

            # 2. 绿信比优化: 各路口独立调整
            current_timing, current_cost, current_perf = self._optimize_green_splits(
                current_timing, current_cost, current_perf,
                network_data, nodes, green_step
            )

            # 3. 相位差优化: 相邻路口协调调整
            current_timing, current_cost, current_perf = self._optimize_offsets(
                current_timing, current_cost, current_perf,
                network_data, nodes, offset_step
            )

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

    def _copy_timing(self, timing):
        return SignalTiming(
            cycle_length=timing.cycle_length,
            offset=timing.offset,
            phases=[dict(p) for p in timing.phases]
        )

    def _optimize_cycle(self, timing, current_cost, current_perf, network_data, nodes, step):
        """
        SCOOT 周期优化
        检测关键路口饱和度，决定全网周期增减
        """
        # 找到关键路口 (饱和度最高)
        max_saturation = 0
        critical_node = nodes[0] if nodes else None

        for node_id in nodes:
            t = timing[node_id]
            sat = self._estimate_node_saturation(t, network_data, node_id)
            if sat > max_saturation:
                max_saturation = sat
                critical_node = node_id

        if critical_node is None:
            return timing, current_cost, current_perf

        t_critical = timing[critical_node]
        current_cycle = t_critical.cycle_length

        # 饱和度 > 0.9: 增加周期; < 0.7: 减少周期
        new_cycle = current_cycle
        if max_saturation > 0.9:
            new_cycle = min(self.constraints.max_cycle_length, current_cycle + step)
        elif max_saturation < 0.7:
            new_cycle = max(self.constraints.min_cycle_length, current_cycle - step)

        if new_cycle == current_cycle:
            return timing, current_cost, current_perf

        # 全网统一调整周期
        new_timing = {}
        for node_id in nodes:
            t = timing[node_id]
            ratio = new_cycle / current_cycle if current_cycle > 0 else 1
            new_phases = []
            for p in t.phases:
                new_p = dict(p)
                new_p['green'] = round(p['green'] * ratio, 1)
                new_phases.append(new_p)
            new_timing[node_id] = SignalTiming(
                cycle_length=new_cycle, offset=t.offset * ratio, phases=new_phases
            )

        new_perf = self._evaluate_performance(new_timing, network_data, nodes)
        new_cost = self._performance_cost(new_perf)

        if new_cost < current_cost:
            return new_timing, new_cost, new_perf
        return timing, current_cost, current_perf

    def _optimize_green_splits(self, timing, current_cost, current_perf, network_data, nodes, step):
        """
        SCOOT 绿信比优化
        根据各相位排队长度调整绿灯分配
        """
        improved = False
        new_timing = {k: self._copy_timing(v) for k, v in timing.items()}

        for node_id in nodes:
            t = new_timing[node_id]
            total_loss = sum(p['yellow'] + p['all_red'] for p in t.phases)
            effective = t.cycle_length - total_loss

            # 估算各方向排队
            ns_queue = self._estimate_direction_queue(node_id, 'ns', network_data, timing)
            ew_queue = self._estimate_direction_queue(node_id, 'ew', network_data, timing)

            total_queue = ns_queue + ew_queue
            if total_queue == 0:
                continue

            # 按排队比例调整
            ns_ratio = ns_queue / total_queue
            current_ns_ratio = t.phases[0]['green'] / effective if effective > 0 else 0.5

            if abs(ns_ratio - current_ns_ratio) > 0.05:
                new_ns_green = effective * ns_ratio
                new_ns_green = max(self.constraints.min_green_time,
                                   min(effective - self.constraints.min_green_time, new_ns_green))

                t.phases[0]['green'] = round(new_ns_green, 1)
                t.phases[1]['green'] = round(effective - new_ns_green, 1)
                improved = True

        if not improved:
            return timing, current_cost, current_perf

        new_perf = self._evaluate_performance(new_timing, network_data, nodes)
        new_cost = self._performance_cost(new_perf)

        if new_cost < current_cost:
            return new_timing, new_cost, new_perf
        return timing, current_cost, current_perf

    def _optimize_offsets(self, timing, current_cost, current_perf, network_data, nodes, step):
        """
        SCOOT 相位差优化
        沿主要交通流方向逐步调整偏移
        """
        improved = False
        new_timing = {k: self._copy_timing(v) for k, v in timing.items()}

        edges = network_data.get('edges', [])
        for edge in edges:
            from_node = edge.get('from')
            to_node = edge.get('to')
            flow = edge.get('flow', 0)

            if from_node not in new_timing or to_node not in new_timing:
                continue

            if flow < 100:
                continue

            t_from = new_timing[from_node]
            t_to = new_timing[to_node]
            travel_time = edge.get('travel_time', 30)

            # 当前偏移差
            current_offset_diff = (t_to.offset - t_from.offset) % t_to.cycle_length
            ideal_offset = travel_time % t_to.cycle_length

            error = current_offset_diff - ideal_offset
            if error > t_to.cycle_length / 2:
                error -= t_to.cycle_length
            elif error < -t_to.cycle_length / 2:
                error += t_to.cycle_length

            if abs(error) > step:
                adjustment = -step if error > 0 else step
                t_to.offset = (t_to.offset + adjustment) % t_to.cycle_length
                improved = True

        if not improved:
            return timing, current_cost, current_perf

        new_perf = self._evaluate_performance(new_timing, network_data, nodes)
        new_cost = self._performance_cost(new_perf)

        if new_cost < current_cost:
            return new_timing, new_cost, new_perf
        return timing, current_cost, current_perf

    def _estimate_node_saturation(self, timing, network_data, node_id):
        """估算路口饱和度"""
        total_flow = 0
        edges = network_data.get('edges', [])
        for edge in edges:
            if edge.get('to') == node_id:
                total_flow += edge.get('flow', 0)

        cycle = timing.cycle_length
        sat_flow = 1800
        green_total = sum(p['green'] for p in timing.phases)
        capacity = sat_flow * (green_total / cycle) if cycle > 0 else 0

        return total_flow / capacity if capacity > 0 else 0

    def _estimate_direction_queue(self, node_id, direction, network_data, timing):
        """估算某方向排队长度"""
        queue = 0
        edges = network_data.get('edges', [])
        for edge in edges:
            if edge.get('to') == node_id:
                # 简化: 根据方向标签判断
                from_node = edge.get('from', '')
                flow = edge.get('flow', 0)
                queue += flow * 0.01  # 简化排队估算
        return queue

    def _evaluate_performance(self, timing, network_data, nodes):
        total_delay = 0
        total_stops = 0
        total_flow = 0
        total_throughput = 0

        edges = network_data.get('edges', [])
        for edge in edges:
            from_node = edge.get('from')
            to_node = edge.get('to')
            flow = edge.get('flow', 0)

            if from_node not in timing or to_node not in timing:
                continue

            t_from = timing[from_node]
            t_to = timing[to_node]
            cycle = t_to.cycle_length

            green_ew = t_to.phases[1]['green'] if len(t_to.phases) > 1 else t_to.phases[0]['green']
            g_c = green_ew / cycle if cycle > 0 else 0.5

            # 协调效果
            offset_diff = (t_to.offset - t_from.offset) % cycle
            travel_time = edge.get('travel_time', 30)
            arrival_error = abs(offset_diff - travel_time % cycle)
            if arrival_error > cycle / 2:
                arrival_error = cycle - arrival_error
            coordination = max(0, 1 - arrival_error / green_ew) if green_ew > 0 else 0

            # Webster 延误
            sat_flow = 1800
            x = flow / (sat_flow * g_c) if g_c > 0 else 1
            if 0 < x < 1:
                d1 = (0.5 * cycle * (1 - g_c) ** 2) / (1 - min(1, x) * g_c)
            else:
                d1 = 0.5 * cycle * (1 - g_c) if g_c < 1 else 0

            d_adjusted = d1 * (1 - coordination * 0.5)
            stops = flow * (1 - g_c) * (1 - coordination * 0.4) / cycle * 3600 if cycle > 0 else 0

            total_delay += d_adjusted * flow
            total_stops += stops
            total_flow += flow
            total_throughput += flow * g_c * 0.9

        avg_delay = total_delay / total_flow if total_flow > 0 else 0
        avg_stops = total_stops / total_flow if total_flow > 0 else 0

        return PerformanceMetrics(
            avg_delay=round(avg_delay, 2),
            avg_queue_length=round(avg_delay * 0.25, 2),
            max_queue_length=int(avg_delay * 0.4),
            throughput=int(total_throughput),
            avg_stops=round(avg_stops, 2),
            vcr=round(sum(
                e.get('flow', 0) / 1800 for e in edges
            ) / max(len(edges), 1), 2)
        )

    def _performance_cost(self, perf):
        return perf.avg_delay * 0.6 + perf.avg_stops * 20 + perf.vcr * 30


from ..base import OptimizerFactory, OptimizationLevel
OptimizerFactory.register('network', 'scoot', SCOOTOptimizer)
